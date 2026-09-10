from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError


class SchoolMajor(models.Model):
    _name = 'school.major'
    _description = 'Academic Major / Program'
    _order = 'name'

    name = fields.Char(string='Major Name', required=True)
    code = fields.Char(string='Major Code', required=True)
    description = fields.Text(string='Description')
    department = fields.Char(string='Department / Faculty')
    duration_years = fields.Integer(string='Duration (Years)', default=4)
    total_credits = fields.Integer(string='Total Credits')
    active = fields.Boolean(default=True)

    student_count = fields.Integer(string='Enrolled Students', compute='_compute_student_count')
    enrollment_ids = fields.One2many('school.major.enrollment', 'major_id', string='Enrollments')
    class_ids = fields.One2many('school.class', 'major_id', string='Classes')
    student_ids = fields.Many2many(
        'school.student',
        'school_major_student_rel',
        'major_id',
        'student_id',
        string='Students'
    )
    subject_ids = fields.Many2many(
        'school.subject',
        'school_major_subject_rel',
        'major_id',
        'subject_id',
        string='Curriculum Subjects'
    )

    _code_uniq = models.Constraint('UNIQUE (code)', 'Major code must be unique!')

    @api.depends('enrollment_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.enrollment_ids.filtered(lambda e: e.status == 'enrolled'))

    def action_view_students(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enrolled Students'),
            'res_model': 'school.major.enrollment',
            'view_mode': 'list,form',
            'domain': [('major_id', '=', self.id), ('status', '=', 'enrolled')],
            'context': {'default_major_id': self.id},
        }

    def action_open_major_students(self):
        return self.action_view_students()


class SchoolMajorEnrollment(models.Model):
    _name = 'school.major.enrollment'
    _description = 'Student Major Enrollment'
    _order = 'enrollment_date desc'
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    student_code = fields.Char(related='student_id.student_id', string='Student ID', readonly=True, store=True)
    major_id = fields.Many2one('school.major', string='Major', required=True, ondelete='cascade')
    academic_year = fields.Char(string='Academic Year', required=True, default='2025-2026')
    status = fields.Selection([
        ('enrolled', 'Enrolled'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ], string='Status', default='enrolled')
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today)
    notes = fields.Text(string='Notes')

    _unique_major_enrollment = models.Constraint(
        'UNIQUE(student_id, major_id, academic_year)',
        'This student is already enrolled in this major for the selected academic year!'
    )

    def _get_state_email_template(self):
        return 'school_management.email_template_major_enrollment_status'

    def _get_state_change_recipients(self):
        return self.student_id.email or self.student_id.parent_email

    def action_drop_student(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise AccessError(_("Only administrators can update enrollment status."))
        for rec in self:
            rec.status = 'dropped'

    def action_complete_student(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise AccessError(_("Only administrators can update enrollment status."))
        for rec in self:
            rec.status = 'completed'

    def action_reenroll_student(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise AccessError(_("Only administrators can update enrollment status."))
        for rec in self:
            rec.status = 'enrolled'
