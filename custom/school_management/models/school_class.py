from odoo import models, fields, _


class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'School Class'
    _order = 'name'

    name = fields.Char(string='Class Name', required=True)
    section = fields.Char(string='Section')
    teacher_id = fields.Many2one('school.teacher', string='Class Teacher')
    subject_ids = fields.Many2many('school.subject', string='Subjects')
    student_ids = fields.One2many('school.student', 'class_id', string='Students')
    student_count = fields.Integer(string='Student Count', compute='_compute_student_count')
    capacity = fields.Integer(string='Capacity', default=40)
    room = fields.Char(string='Room Number')
    active = fields.Boolean(default=True)
    capacity_progress = fields.Float(string='Capacity %', compute='_compute_capacity_progress')

    def _compute_capacity_progress(self):
        for rec in self:
            rec.capacity_progress = (rec.student_count / rec.capacity * 100) if rec.capacity else 0

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = self.env['school.student'].search_count([
                ('class_id', '=', rec.id)
            ])
