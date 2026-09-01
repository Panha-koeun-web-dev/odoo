from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolEnrollStudentsWizard(models.TransientModel):
    _name = 'school.enroll.students.wizard'
    _description = 'Bulk Enroll Students'

    enrollment_type = fields.Selection([
        ('single', 'Single Student'),
        ('bulk', 'Multiple Students')
    ], string='Enrollment Type', required=True, default='single')
    student_id = fields.Many2one('school.student', string='Student')
    student_ids = fields.Many2many('school.student', string='Students')
    class_id = fields.Many2one('school.class', string='Class', required=True)
    academic_year = fields.Char(string='Academic Year', required=True, default='2025-2026')
    semester = fields.Selection([
        ('1', 'Semester 1'),
        ('2', 'Semester 2'),
        ('full', 'Full Year'),
    ], string='Semester', required=True, default='1')
    enrollment_date = fields.Date(string='Enrollment Date', required=True, default=fields.Date.today)
    subject_ids = fields.Many2many('school.subject', string='Subjects to Learn')

    student_count = fields.Integer(
        string='Students Selected',
        compute='_compute_student_count',
    )

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            self.subject_ids = self.class_id.subject_ids

    def action_enroll(self):
        self.ensure_one()
        if self.enrollment_type == 'single':
            if not self.student_id:
                raise UserError(_('Please select a student to enroll.'))
            students = self.student_id
        else:
            if not self.student_ids:
                raise UserError(_('Please select at least one student to enroll.'))
            students = self.student_ids
            
        enrollment_model = self.env['school.enrollment']

        duplicate_student_ids = set(enrollment_model.search([
            ('student_id', 'in', students.ids),
            ('class_id', '=', self.class_id.id),
            ('academic_year', '=', self.academic_year),
            ('semester', '=', self.semester),
        ]).student_id.ids)

        to_enroll = students.filtered(lambda s: s.id not in duplicate_student_ids)
        if not to_enroll:
            raise UserError(_(
                'All selected students are already enrolled in this class for the selected '
                'academic year and semester.'
            ))

        subjects = self.subject_ids or self.class_id.subject_ids
        vals_list = [{
            'student_id': student.id,
            'class_id': self.class_id.id,
            'academic_year': self.academic_year,
            'semester': self.semester,
            'enrollment_date': self.enrollment_date,
            'subject_ids': [(6, 0, subjects.ids)],
        } for student in to_enroll]

        created = enrollment_model.create(vals_list)


        action = self.env['ir.actions.act_window']._for_xml_id('school_management.action_enrollment')
        action['domain'] = [('id', 'in', created.ids)]
        return action