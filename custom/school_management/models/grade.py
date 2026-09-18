from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SchoolGrade(models.Model):
    _name = 'school.grade'
    _description = 'Student Grade and Exam Schedule'
    _order = 'exam_datetime desc, student_id, exam_id'
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True)
    exam_id = fields.Many2one('school.exam', string='Exam', required=True, ondelete='cascade')
    subject_id = fields.Many2one(related='exam_id.subject_id', string='Subject', store=True)
    class_id = fields.Many2one(related='exam_id.class_id', string='Class', store=True)

    # Date & Time Scheduling for this student
    exam_datetime = fields.Datetime(
        string='Exam Start Time',
        compute='_compute_exam_schedule',
        store=True,
        readonly=False,
        help="The specific date and time this student is scheduled to take the exam."
    )
    exam_end_datetime = fields.Datetime(
        string='Exam End Time',
        compute='_compute_exam_schedule',
        store=True,
        readonly=False,
        help="The specific end date and time for this student's exam."
    )
    is_custom_schedule = fields.Boolean(
        string='Custom Timeslot',
        default=False,
        help="Indicates if this student has a specific custom exam datetime different from the class exam datetime."
    )
    schedule_type = fields.Selection([
        ('standard', 'Standard'),
        ('custom', 'Custom'),
    ], string='Timeslot', compute='_compute_schedule_type', store=True)
    room = fields.Char(
        string='Room / Seat / Desk',
        compute='_compute_room',
        store=True,
        readonly=False,
        help="Specific exam room, seat number, or desk."
    )
    attendance_status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('present', 'Present / Attended'),
        ('absent', 'Absent'),
        ('excused', 'Excused / Rescheduled'),
    ], string='Attendance', default='scheduled')
    schedule_notes = fields.Char(
        string='Schedule Reason / Notes',
        help="e.g. Makeup exam, oral exam slot, medical extension"
    )

    # Marks & Results
    marks_obtained = fields.Float(string='Marks Obtained')
    total_marks = fields.Integer(related='exam_id.total_marks', string='Total Marks')
    percentage = fields.Float(string='Percentage', compute='_compute_percentage', store=True)
    grade_letter = fields.Selection([
        ('a+', 'A+'), ('a', 'A'), ('a-', 'A-'),
        ('b+', 'B+'), ('b', 'B'), ('b-', 'B-'),
        ('c+', 'C+'), ('c', 'C'), ('c-', 'C-'),
        ('d', 'D'), ('f', 'F'),
    ], string='Grade', compute='_compute_grade', store=True)
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', compute='_compute_result', store=True)
    remarks = fields.Text(string='Remarks')

    @api.constrains('student_id', 'exam_id')
    def _check_unique_student_exam(self):
        for rec in self:
            if rec.student_id and rec.exam_id:
                existing = self.search([
                    ('exam_id', '=', rec.exam_id.id),
                    ('student_id', '=', rec.student_id.id),
                    ('id', '!=', rec.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_("Student '%s' is already scheduled for exam '%s'!") % (
                        rec.student_id.name, rec.exam_id.name
                    ))

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.exam_id and not self.is_custom_schedule:
            if self.exam_id.start_datetime and not self.exam_datetime:
                self.exam_datetime = self.exam_id.start_datetime
            if self.exam_id.end_datetime and not self.exam_end_datetime:
                self.exam_end_datetime = self.exam_id.end_datetime
            if self.exam_id.room and not self.room:
                self.room = self.exam_id.room
            if not self.attendance_status:
                self.attendance_status = 'scheduled'

    @api.depends('is_custom_schedule')
    def _compute_schedule_type(self):
        for rec in self:
            rec.schedule_type = 'custom' if rec.is_custom_schedule else 'standard'

    @api.depends('exam_id.start_datetime', 'exam_id.end_datetime')
    def _compute_exam_schedule(self):
        for rec in self:
            if not rec.is_custom_schedule and rec.exam_id:
                rec.exam_datetime = rec.exam_id.start_datetime
                rec.exam_end_datetime = rec.exam_id.end_datetime

    @api.depends('exam_id.room')
    def _compute_room(self):
        for rec in self:
            if not rec.is_custom_schedule and rec.exam_id and not rec.room:
                rec.room = rec.exam_id.room

    def write(self, vals):
        if ('exam_datetime' in vals or 'exam_end_datetime' in vals) and 'is_custom_schedule' not in vals:
            vals['is_custom_schedule'] = True
        return super().write(vals)

    def action_reset_to_default_schedule(self):
        """Reset student's exam timing back to the exam general timing."""
        for rec in self:
            rec.write({
                'is_custom_schedule': False,
                'exam_datetime': rec.exam_id.start_datetime,
                'exam_end_datetime': rec.exam_id.end_datetime,
                'room': rec.exam_id.room,
                'schedule_notes': False,
            })

    def action_open_student_schedule_wizard(self):
        """Open schedule wizard for this single student record."""
        self.ensure_one()
        return {
            'name': _("Set Specific Exam Datetime for %s") % self.student_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.exam.student.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_exam_id': self.exam_id.id,
                'default_grade_ids': [self.id],
                'default_specific_start_datetime': self.exam_datetime or self.exam_id.start_datetime,
                'default_specific_end_datetime': self.exam_end_datetime or self.exam_id.end_datetime,
                'default_room': self.room or self.exam_id.room,
                'default_attendance_status': self.attendance_status,
                'default_schedule_notes': self.schedule_notes,
            }
        }

    @api.depends('marks_obtained', 'total_marks')
    def _compute_percentage(self):
        for rec in self:
            rec.percentage = (rec.marks_obtained / rec.total_marks * 100) if rec.total_marks else 0

    @api.depends('percentage')
    def _compute_grade(self):
        for rec in self:
            p = rec.percentage
            if p >= 90:
                rec.grade_letter = 'a+'
            elif p >= 80:
                rec.grade_letter = 'a'
            elif p >= 70:
                rec.grade_letter = 'b+'
            elif p >= 60:
                rec.grade_letter = 'b'
            elif p >= 50:
                rec.grade_letter = 'c+'
            elif p >= 40:
                rec.grade_letter = 'c'
            elif p >= 30:
                rec.grade_letter = 'd'
            else:
                rec.grade_letter = 'f'

    @api.depends('marks_obtained', 'exam_id.passing_marks')
    def _compute_result(self):
        for rec in self:
            if rec.exam_id and rec.marks_obtained >= rec.exam_id.passing_marks:
                rec.result = 'pass'
            else:
                rec.result = 'fail'

    def action_export_xlsx(self):
        ids = self.ids or self.env.context.get('active_ids') or []
        ids_str = ','.join(str(x) for x in ids) if ids else ''
        return {
            'type': 'ir.actions.act_url',
            'url': f'/school_management/export_report_xlsx?report_type=grade&ids={ids_str}',
            'target': 'self',
        }
