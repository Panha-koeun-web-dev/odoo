from odoo import models, fields, api, _


class SchoolAttendance(models.Model):
    _name = 'school.attendance'
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

    _sql_constraints = [
        ('unique_attendance', 'unique(student_id, date)',
         'Attendance already recorded for this student on this date!'),
    ]