from odoo import models, fields, api, _


class SchoolStudent(models.Model):
    _name = 'school.student'
    _description = 'School Student'
    _order = 'name'

    name = fields.Char(string='Full Name', required=True)
    student_id = fields.Char(string='Student ID', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', required=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    parent_name = fields.Char(string='Parent/Guardian Name')
    parent_phone = fields.Char(string='Parent Phone')
    parent_email = fields.Char(string='Parent Email')
    address = fields.Text(string='Address')
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today)
    photo = fields.Image(string='Photo')
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Related User')
    attendance_ids = fields.One2many('school.attendance', 'student_id', string='Attendance')
    grade_ids = fields.One2many('school.grade', 'student_id', string='Grades')
    fee_ids = fields.One2many('school.fee', 'student_id', string='Fees')
    notes = fields.Text(string='Notes')

    @api.depends('date_of_birth')
    def _compute_age(self):
        for rec in self:
            if rec.date_of_birth:
                today = fields.Date.today()
                rec.age = today.year - rec.date_of_birth.year - (
                    (today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day)
                )
            else:
                rec.age = 0