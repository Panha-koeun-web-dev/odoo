from odoo import models, fields, api, _


class SchoolGrade(models.Model):
    _name = 'school.grade'
    _description = 'Student Grade'
    _order = 'student_id, exam_id'
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True)
    exam_id = fields.Many2one('school.exam', string='Exam', required=True)
    subject_id = fields.Many2one(related='exam_id.subject_id', string='Subject', store=True)
    marks_obtained = fields.Float(string='Marks Obtained')
    total_marks = fields.Integer(related='exam_id.total_marks', string='Total Marks')
    percentage = fields.Float(string='Percentage', compute='_compute_percentage', store=True)
    grade_letter = fields.Selection([
        ('a+', 'A+'), ('a', 'A'), ('a-', 'A-'),
        ('b+', 'B+'), ('b', 'B'), ('b-', 'B-'),
        ('c+', 'C+'), ('c', 'C'), ('c-', 'C-'),
        ('d', 'D'), ('f', 'F'),
    ], string='Grade', compute='_compute_grade', store=True)
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', compute='_compute_result', store=True)
    remarks = fields.Text(string='Remarks')

    @api.depends('marks_obtained', 'total_marks')
    def _compute_percentage(self):
        for rec in self:
            rec.percentage = (rec.marks_obtained / rec.total_marks * 100) if rec.total_marks else 0

    @api.depends('percentage')
    def _compute_grade(self):
        for rec in self:
            p = rec.percentage
            if p >= 90:
                rec.grade_letter = 'a+'
            elif p >= 80:
                rec.grade_letter = 'a'
            elif p >= 70:
                rec.grade_letter = 'b+'
            elif p >= 60:
                rec.grade_letter = 'b'
            elif p >= 50:
                rec.grade_letter = 'c+'
            elif p >= 40:
                rec.grade_letter = 'c'
            elif p >= 30:
                rec.grade_letter = 'd'
            else:
                rec.grade_letter = 'f'

    @api.depends('marks_obtained', 'exam_id.passing_marks')
    def _compute_result(self):
        for rec in self:
            if rec.exam_id and rec.marks_obtained >= rec.exam_id.passing_marks:
                rec.result = 'pass'
            else:
                rec.result = 'fail'