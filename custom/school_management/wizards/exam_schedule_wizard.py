from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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
