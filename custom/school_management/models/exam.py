from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError


class SchoolExam(models.Model):
    _name = 'school.exam'
    _description = 'School Exam'
    _order = 'start_datetime desc, date desc'

    name = fields.Char(string='Exam Name', required=True)
    subject_id = fields.Many2one('school.subject', string='Subject', required=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    term_id = fields.Many2one(
        'school.term',
        string='Academic Term',
        index=True,
        help="Academic term in which this exam is conducted."
    )

    @api.onchange('class_id')
    def _onchange_class_id_set_term(self):
        if self.class_id and self.class_id.current_term_id and not self.term_id:
            self.term_id = self.class_id.current_term_id
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('term_id') and vals.get('class_id'):
                class_rec = self.env['school.class'].browse(vals['class_id'])
                if class_rec.current_term_id:
                    vals['term_id'] = class_rec.current_term_id.id
        return super().create(vals_list)

    exam_type = fields.Selection([
        ('midterm', 'Midterm'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
    ], string='Exam Type', required=True, default='midterm')

    # Date & Time Scheduling
    start_datetime = fields.Datetime(
        string='Exam Start Date & Time',
        required=True,
        default=fields.Datetime.now,
        help="General scheduled start date and time for this exam."
    )
    end_datetime = fields.Datetime(
        string='Exam End Date & Time',
        compute='_compute_end_datetime',
        store=True,
        readonly=False,
        help="Scheduled end date and time for this exam."
    )
    duration_hours = fields.Float(
        string='Duration (Hours)',
        default=2.0,
        help="Exam duration in hours (e.g. 1.5 = 1 hour 30 mins)."
    )
    date = fields.Date(
        string='Exam Date',
        compute='_compute_date',
        store=True,
        readonly=False,
        help="Date extracted from the start datetime for easy reporting and filtering."
    )
    room = fields.Char(string='Exam Room / Hall / Link')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')

    total_marks = fields.Integer(string='Total Marks', default=100)
    passing_marks = fields.Integer(string='Passing Marks', default=40)
    grade_ids = fields.One2many('school.grade', 'exam_id', string='Student Schedules & Grades')
    active = fields.Boolean(default=True)

    # Statistical / KPI counters
    total_students_count = fields.Integer(string='Total Students', compute='_compute_exam_stats')
    custom_schedule_count = fields.Integer(string='Custom Timeslots', compute='_compute_exam_stats')
    attended_count = fields.Integer(string='Attended', compute='_compute_exam_stats')
    absent_count = fields.Integer(string='Absent', compute='_compute_exam_stats')
    passed_count = fields.Integer(string='Passed', compute='_compute_exam_stats')

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id and self.class_id.current_term_id and not self.term_id:
            self.term_id = self.class_id.current_term_id

    @api.depends('start_datetime')
    def _compute_date(self):
        for rec in self:
            if rec.start_datetime:
                rec.date = rec.start_datetime.date()
            elif not rec.date:
                rec.date = fields.Date.today()

    @api.depends('start_datetime', 'duration_hours')
    def _compute_end_datetime(self):
        for rec in self:
            if rec.start_datetime and rec.duration_hours:
                rec.end_datetime = rec.start_datetime + timedelta(hours=rec.duration_hours)
            elif rec.start_datetime and not rec.end_datetime:
                rec.end_datetime = rec.start_datetime + timedelta(hours=2.0)

    @api.onchange('start_datetime', 'end_datetime')
    def _onchange_datetimes(self):
        if self.start_datetime and self.end_datetime:
            if self.end_datetime < self.start_datetime:
                raise ValidationError(_("Exam End Time cannot be earlier than Start Time!"))
            diff_seconds = (self.end_datetime - self.start_datetime).total_seconds()
            self.duration_hours = round(diff_seconds / 3600.0, 2)

    @api.depends('grade_ids', 'grade_ids.is_custom_schedule', 'grade_ids.attendance_status', 'grade_ids.result')
    def _compute_exam_stats(self):
        for rec in self:
            rec.total_students_count = len(rec.grade_ids)
            rec.custom_schedule_count = len(rec.grade_ids.filtered('is_custom_schedule'))
            rec.attended_count = len(rec.grade_ids.filtered(lambda g: g.attendance_status in ('present', 'attended')))
            rec.absent_count = len(rec.grade_ids.filtered(lambda g: g.attendance_status == 'absent'))
            rec.passed_count = len(rec.grade_ids.filtered(lambda g: g.result == 'pass'))

    def write(self, vals):
        res = super().write(vals)
        if 'start_datetime' in vals or 'end_datetime' in vals or 'room' in vals:
            for exam in self:
                # Update non-custom student schedules
                update_vals = {}
                if 'start_datetime' in vals:
                    update_vals['exam_datetime'] = exam.start_datetime
                if 'end_datetime' in vals:
                    update_vals['exam_end_datetime'] = exam.end_datetime
                if 'room' in vals and vals.get('room'):
                    update_vals['room'] = exam.room

                if update_vals:
                    exam.grade_ids.filtered(lambda g: not g.is_custom_schedule).write(update_vals)
        return res

    # Workflow Actions
    def action_set_scheduled(self):
        self.write({'state': 'scheduled'})

    def action_start_exam(self):
        self.write({'state': 'in_progress'})

    def action_done_exam(self):
        self.write({'state': 'completed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_cancel_exam(self):
        self.write({'state': 'cancelled'})

    def action_open_select_students_wizard(self):
        """Open wizard to select specific students to take this exam."""
        self.ensure_one()
        return {
            'name': _('Select Students for Exam: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.exam.select.student.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_exam_id': self.id,
                'default_specific_start_datetime': self.start_datetime,
                'default_specific_end_datetime': self.end_datetime,
                'default_room': self.room,
            }
        }

    def action_populate_students(self):
        """Populate all enrolled students from class into this exam with default timing and room."""
        self.ensure_one()
        if not self.class_id:
            raise UserError(_("Please select a class first!"))

        students = self.class_id.student_ids
        if not students:
            raise UserError(_("The selected class '%s' has no enrolled students.") % self.class_id.name)

        existing_student_ids = self.grade_ids.mapped('student_id.id')
        new_grades = []
        for student in students:
            if student.id not in existing_student_ids:
                new_grades.append((0, 0, {
                    'student_id': student.id,
                    'exam_datetime': self.start_datetime,
                    'exam_end_datetime': self.end_datetime,
                    'room': self.room,
                    'attendance_status': 'scheduled',
                    'is_custom_schedule': False,
                }))

        if new_grades:
            self.write({'grade_ids': new_grades})
            msg = _("Successfully populated %d student(s) from class '%s'.") % (len(new_grades), self.class_id.name)
        else:
            msg = _("All students from class '%s' are already scheduled for this exam.") % self.class_id.name

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Students Populated'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_schedule_wizard(self):
        """Open popup wizard to set specific student exam schedule."""
        self.ensure_one()
        return {
            'name': _('Set Specific Student Exam Datetime'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.exam.student.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_exam_id': self.id,
                'default_specific_start_datetime': self.start_datetime,
                'default_specific_end_datetime': self.end_datetime,
                'default_room': self.room,
                'default_grade_ids': self.grade_ids.ids,
            }
        }


class SchoolExamStudentScheduleWizard(models.TransientModel):
    _name = 'school.exam.student.schedule.wizard'
    _description = 'Set Specific Student Exam Datetime Wizard'

    exam_id = fields.Many2one('school.exam', string='Exam', required=True)
    grade_ids = fields.Many2many(
        'school.grade',
        'school_exam_schedule_wiz_grade_rel',
        'wizard_id',
        'grade_id',
        string='Selected Students',
        required=True
    )
    student_count = fields.Integer(string='Students Count', compute='_compute_student_count')

    specific_start_datetime = fields.Datetime(
        string='Specific Exam Start Time',
        required=True,
        default=fields.Datetime.now
    )
    specific_end_datetime = fields.Datetime(
        string='Specific Exam End Time'
    )
    room = fields.Char(string='Specific Room / Desk / Link')
    attendance_status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('present', 'Present / Attended'),
        ('absent', 'Absent'),
        ('excused', 'Excused / Rescheduled'),
    ], string='Attendance Status', default='scheduled')
    schedule_notes = fields.Char(string='Reason / Notes')

    @api.depends('grade_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.grade_ids)

    def action_apply_schedule(self):
        self.ensure_one()
        if not self.grade_ids:
            raise UserError(_("Please select at least one student."))

        if self.specific_end_datetime and self.specific_end_datetime < self.specific_start_datetime:
            raise ValidationError(_("Exam End Time cannot be earlier than Start Time!"))

        vals = {
            'is_custom_schedule': True,
            'exam_datetime': self.specific_start_datetime,
            'exam_end_datetime': self.specific_end_datetime or self.specific_start_datetime,
        }
        if self.room:
            vals['room'] = self.room
        if self.schedule_notes:
            vals['schedule_notes'] = self.schedule_notes
        if self.attendance_status:
            vals['attendance_status'] = self.attendance_status

        self.grade_ids.write(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Exam Schedule Updated'),
                'message': _("Successfully set specific exam datetime for %d student(s).") % len(self.grade_ids),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_to_exam_schedule(self):
        self.ensure_one()
        for grade in self.grade_ids:
            grade.action_reset_to_default_schedule()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Exam Schedule Reset'),
                'message': _("Reset timing to default exam schedule for %d student(s).") % len(self.grade_ids),
                'type': 'info',
                'sticky': False,
            }
        }
