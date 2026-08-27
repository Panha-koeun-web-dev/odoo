from odoo import models, fields, _


class SchoolExam(models.Model):
    _name = 'school.exam'
    _description = 'School Exam'
    _order = 'date desc'

    name = fields.Char(string='Exam Name', required=True)
    subject_id = fields.Many2one('school.subject', string='Subject', required=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    exam_type = fields.Selection([
        ('midterm', 'Midterm'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
    ], string='Exam Type', required=True)
    date = fields.Date(string='Exam Date', required=True)
    total_marks = fields.Integer(string='Total Marks', default=100)
    passing_marks = fields.Integer(string='Passing Marks', default=40)
    grade_ids = fields.One2many('school.grade', 'exam_id', string='Grades')
    active = fields.Boolean(default=True)