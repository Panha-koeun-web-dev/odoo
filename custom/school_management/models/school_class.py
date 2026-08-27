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
    student_count = fields.Integer(string='Students', compute='_compute_student_count')
    capacity = fields.Integer(string='Capacity', default=40)
    room = fields.Char(string='Room Number')
    active = fields.Boolean(default=True)

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = self.env['school.student'].search_count([
                ('class_id', '=', rec.id)
            ])