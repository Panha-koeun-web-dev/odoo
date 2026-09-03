# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SchoolMajor(models.Model):
    _name = 'school.major'
    _description = 'Student Major / Program of Study'
    _order = 'name'

    name = fields.Char(string='Major Name', required=True)
    code = fields.Char(string='Code')
    department = fields.Char(string='Department')
    duration_years = fields.Integer(string='Duration (years)', default=4)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    enrollment_ids = fields.One2many('school.major.enrollment', 'major_id', string='Enrollments')
    class_ids = fields.One2many('school.class', 'major_id', string='Classes')
    student_ids = fields.Many2many(
        'school.student',
        'school_major_student_rel',
        'major_id',
        'student_id',
        string='Students',
        compute='_compute_students',
    )
    student_count = fields.Integer(string='Student Count', compute='_compute_students')

    @api.depends('enrollment_ids.student_id')
    def _compute_students(self):
        for rec in self:
            rec.student_ids = rec.enrollment_ids.mapped('student_id')
            rec.student_count = len(rec.student_ids)

    def action_open_major_students(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Students - %s') % self.name,
            'res_model': 'school.student',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.student_ids.ids)],
            'context': dict(self.env.context),
        }


class SchoolMajorEnrollment(models.Model):
    _name = 'school.major.enrollment'
    _description = 'Student Major Enrollment'
    _order = 'enrollment_date desc, id desc'
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    student_code = fields.Char(string='Student ID', related='student_id.student_id')
    major_id = fields.Many2one('school.major', string='Major', required=True, ondelete='cascade')
    academic_year = fields.Char(string='Academic Year', required=True, default='2025-2026')
    status = fields.Selection([
        ('enrolled', 'Enrolled'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ], string='Status', default='enrolled')
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_major_enrollment',
         'unique(student_id, major_id, academic_year)',
         'This student is already enrolled in this major for the selected academic year!'),
    ]

    def action_drop_student(self):
        for rec in self:
            rec.status = 'dropped'

    def action_reenroll_student(self):
        for rec in self:
            rec.status = 'enrolled'
