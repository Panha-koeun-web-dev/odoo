from odoo import models, fields

class SchoolSubject(models.Model):
    _name = 'school.subject'
    _description = 'School Subject'
    _order = 'name'

    name = fields.Char(string='Subject Name', required=True)
    code = fields.Char(string='Subject Code', required=True)
    description = fields.Text(string='Description')
    teacher_ids = fields.Many2many('school.teacher', string='Assigned Teachers')
    active = fields.Boolean(default=True)
    