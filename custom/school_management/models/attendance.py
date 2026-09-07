from odoo import models, fields, api, _


class SchoolAttendance(models.Model):
    _name = 'school.attendance'
    _inherit = ['school.state.notification']
    _description = 'Student Attendance'
    _order = 'date desc, student_id'
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True)
    class_id = fields.Many2one(related='student_id.class_id', string='Class', store=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ], string='Status', required=True, default='present')
    notes = fields.Text(string='Notes')

    student_code = fields.Char(related='student_id.student_id', string='Student ID', readonly=True)

    _unique_attendance = models.Constraint(
        'unique(student_id, date)',
        'Attendance already recorded for this student on this date!',
    )

    def _get_state_email_template(self):
        return 'school_management.email_template_attendance_status'

    def _get_state_change_recipients(self):
        return self.student_id.email or self.student_id.parent_email

    def action_set_present(self):
        self.write({'status': 'present'})

    def action_set_absent(self):
        self.write({'status': 'absent'})

    def action_set_late(self):
        self.write({'status': 'late'})

    def action_set_excused(self):
        self.write({'status': 'excused'})
