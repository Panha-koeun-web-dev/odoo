from odoo import models, fields, _

class SchoolTeacher(models.Model):
    _name = 'school.teacher'
    _description = 'School Teacher'
    _order = 'name'

    name = fields.Char(string='Full Name', required=True)
    employee_id = fields.Char(string='Employee ID', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    date_of_birth = fields.Date(string='Date of Birth')
    hire_date = fields.Date(string='Hire Date', default=fields.Date.today)
    subject_ids = fields.Many2many('school.subject', string='Subjects')
    class_ids = fields.One2many('school.class', 'teacher_id', string='Assigned Classes')
    photo = fields.Image(string='Photo')
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Related User')
    notes = fields.Text(string='Notes')