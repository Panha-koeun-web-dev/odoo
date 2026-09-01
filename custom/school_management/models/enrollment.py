from odoo import models, fields, api, _


class SchoolEnrollment(models.Model):
    _name = 'school.enrollment'
    _description = 'Student Enrollment'
    _order = 'enrollment_date desc, id desc'
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    student_code = fields.Char(string='Student ID', related='student_id.student_id')
    student_email = fields.Char(string='Student Email', related='student_id.email')
    student_phone = fields.Char(string='Student Phone', related='student_id.phone')
    class_id = fields.Many2one('school.class', string='Class', required=True, ondelete='cascade')
    academic_year = fields.Char(string='Academic Year', required=True, default='2025-2026')
    semester = fields.Selection([
        ('1', 'Semester 1'),
        ('2', 'Semester 2'),
        ('full', 'Full Year'),
    ], string='Semester', required=True, default='1')
    enrollment_date = fields.Date(string='Enrollment Date', required=True, default=fields.Date.today)
    subject_ids = fields.Many2many('school.subject', string='Subjects to Learn')

    notes = fields.Text(string='Notes')

    _unique_enrollment = models.Constraint(
        'unique(student_id, class_id, academic_year, semester)',
        'This student is already enrolled in this class and semester for the selected academic year!',
    )

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            self.subject_ids = self.class_id.subject_ids

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id and not self.class_id:
            self.class_id = self.student_id.class_id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.class_id:
                rec.student_id.class_id = rec.class_id
        return records
