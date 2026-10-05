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
    teacher_id = fields.Many2one(
        'school.teacher',
        string='Supervisor / Invigilator',
        index=True,
        help="Teacher assigned to supervise and invigilate this examination."
    )
    timetable_id = fields.Many2one(
        'school.timetable',
        string='Timetable Session',
        ondelete='set null',
        copy=False,
        help="Master timetable session synchronized with this examination."
    )


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('class_id'):
                class_rec = self.env['school.class'].browse(vals['class_id'])
                if not vals.get('term_id') and class_rec.current_term_id:
                    vals['term_id'] = class_rec.current_term_id.id
                if not vals.get('room') and class_rec.room:
                    vals['room'] = class_rec.room
                if not vals.get('teacher_id'):
                    if vals.get('subject_id'):
                        asg = self.env['school.teaching.assignment'].search([
                            ('class_id', '=', class_rec.id),
                            ('subject_id', '=', vals['subject_id']),
                            ('active', '=', True),
                        ], limit=1)
                        if asg and asg.teacher_id:
                            vals['teacher_id'] = asg.teacher_id.id
                    if not vals.get('teacher_id') and class_rec.teacher_id:
                        vals['teacher_id'] = class_rec.teacher_id.id
        records = super().create(vals_list)
        records._sync_timetable_session()
        return records

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

    @api.onchange('class_id', 'subject_id')
    def _onchange_class_and_subject(self):
        if self.class_id:
            if not self.term_id and self.class_id.current_term_id:
                self.term_id = self.class_id.current_term_id
            if not self.room and self.class_id.room:
                self.room = self.class_id.room
            if not self.teacher_id:
                if self.subject_id:
                    asg = self.env['school.teaching.assignment'].search([
                        ('class_id', '=', self.class_id.id),
                        ('subject_id', '=', self.subject_id.id),
                        ('active', '=', True),
                    ], limit=1)
                    if asg and asg.teacher_id:
                        self.teacher_id = asg.teacher_id
                if not self.teacher_id and self.class_id.teacher_id:
                    self.teacher_id = self.class_id.teacher_id

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

        sync_fields = {'start_datetime', 'end_datetime', 'room', 'teacher_id', 'class_id', 'subject_id', 'term_id', 'name', 'state', 'active'}
        if sync_fields.intersection(vals.keys()):
            self._sync_timetable_session()
        return res

    def unlink(self):
        timetables = self.mapped('timetable_id')
        res = super().unlink()
        if timetables:
            timetables.sudo().unlink()
        return res
    @api.constrains('start_datetime', 'end_datetime', 'room', 'teacher_id', 'class_id', 'state', 'active')
    def _check_exam_schedule_conflicts(self):
        for exam in self:
            if not exam.active or exam.state == 'cancelled':
                continue
            if not exam.start_datetime or not exam.end_datetime:
                continue
            if exam.start_datetime >= exam.end_datetime:
                raise ValidationError(_("Exam Start Date & Time must be earlier than End Date & Time!"))

            # 1. Room collision with other active exams
            if exam.room:
                conflicting_room_exam = self.search([
                    ('id', '!=', exam.id),
                    ('active', '=', True),
                    ('state', '!=', 'cancelled'),
                    ('room', '=ilike', exam.room.strip()),
                    ('start_datetime', '<', exam.end_datetime),
                    ('end_datetime', '>', exam.start_datetime),
                ], limit=1)
                if conflicting_room_exam:
                    raise ValidationError(_(
                        "Exam Room Conflict Detected!\n"
                        "Room '%(room)s' is already booked for examination '%(other_exam)s' (Class: %(class_name)s) "
                        "from %(start)s to %(end)s."
                    ) % {
                        'room': exam.room,
                        'other_exam': conflicting_room_exam.name,
                        'class_name': conflicting_room_exam.class_id.name or _("N/A"),
                        'start': fields.Datetime.to_string(conflicting_room_exam.start_datetime),
                        'end': fields.Datetime.to_string(conflicting_room_exam.end_datetime),
                    })

            # 2. Teacher supervisor / invigilator collision with other exams
            if exam.teacher_id:
                conflicting_teacher_exam = self.search([
                    ('id', '!=', exam.id),
                    ('active', '=', True),
                    ('state', '!=', 'cancelled'),
                    ('teacher_id', '=', exam.teacher_id.id),
                    ('start_datetime', '<', exam.end_datetime),
                    ('end_datetime', '>', exam.start_datetime),
                ], limit=1)
                if conflicting_teacher_exam:
                    raise ValidationError(_(
                        "Teacher Invigilation Conflict Detected!\n"
                        "Teacher '%(teacher)s' is already scheduled to supervise examination '%(other_exam)s' (Class: %(class_name)s) "
                        "from %(start)s to %(end)s."
                    ) % {
                        'teacher': exam.teacher_id.name,
                        'other_exam': conflicting_teacher_exam.name,
                        'class_name': conflicting_teacher_exam.class_id.name or _("N/A"),
                        'start': fields.Datetime.to_string(conflicting_teacher_exam.start_datetime),
                        'end': fields.Datetime.to_string(conflicting_teacher_exam.end_datetime),
                    })

            # 3. Class collision with other exams
            if exam.class_id:
                conflicting_class_exam = self.search([
                    ('id', '!=', exam.id),
                    ('active', '=', True),
                    ('state', '!=', 'cancelled'),
                    ('class_id', '=', exam.class_id.id),
                    ('start_datetime', '<', exam.end_datetime),
                    ('end_datetime', '>', exam.start_datetime),
                ], limit=1)
                if conflicting_class_exam:
                    raise ValidationError(_(
                        "Class Exam Conflict Detected!\n"
                        "Class '%(class_name)s' already has another examination '%(other_exam)s' scheduled "
                        "from %(start)s to %(end)s."
                    ) % {
                        'class_name': exam.class_id.name,
                        'other_exam': conflicting_class_exam.name,
                        'start': fields.Datetime.to_string(conflicting_class_exam.start_datetime),
                        'end': fields.Datetime.to_string(conflicting_class_exam.end_datetime),
                    })

    def _sync_timetable_session(self):
        Timetable = self.env['school.timetable'].sudo()
        for exam in self:
            if not exam.start_datetime or not exam.end_datetime:
                continue
            if exam.state == 'cancelled' or not exam.active:
                if exam.timetable_id:
                    exam.timetable_id.unlink()
                continue

            timetable_vals = {
                'name': f"[EXAM] {exam.name}",
                'exam_id': exam.id,
                'is_exam': True,
                'subject_id': exam.subject_id.id if exam.subject_id else False,
                'subject_ids': [(6, 0, [exam.subject_id.id])] if exam.subject_id else False,
                'class_id': exam.class_id.id if exam.class_id else False,
                'teacher_id': exam.teacher_id.id if exam.teacher_id else False,
                'room': exam.room,
                'start_datetime': exam.start_datetime,
                'end_datetime': exam.end_datetime,
                'term_id': exam.term_id.id if exam.term_id else False,
                'is_holiday': False,
            }
            # Include students enrolled in exam
            student_ids = exam.grade_ids.mapped('student_id.id')
            if not student_ids and exam.class_id:
                student_ids = exam.class_id.student_ids.ids
            if student_ids:
                timetable_vals['student_ids'] = [(6, 0, student_ids)]

            if exam.timetable_id:
                exam.timetable_id.write(timetable_vals)
            else:
                session = Timetable.create(timetable_vals)
                super(SchoolExam, exam).write({'timetable_id': session.id})

    def action_view_in_timetable(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('school_management.action_timetable')
        if self.timetable_id:
            action['domain'] = [('id', '=', self.timetable_id.id)]
            action['views'] = [(False, 'calendar'), (False, 'list'), (False, 'form')]
            action['res_id'] = self.timetable_id.id
        elif self.class_id:
            action['domain'] = [('class_id', '=', self.class_id.id)]
        return action


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
            self._sync_timetable_session()
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

    def action_select_all_students(self):
        self.ensure_one()
        if self.exam_id:
            self.grade_ids = [(6, 0, self.exam_id.grade_ids.ids)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_clear_students(self):
        self.ensure_one()
        self.grade_ids = [(5, 0, 0)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

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
