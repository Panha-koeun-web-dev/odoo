from odoo import models, fields, api, _


class SchoolSubject(models.Model):
    _name = 'school.subject'
    _description = 'School Subject'
    _order = 'name'

    name = fields.Char(string='Subject Name', required=True)
    code = fields.Char(string='Subject Code', required=True)
    department = fields.Selection([
        ('languages', 'Languages & Literature'),
        ('science', 'Sciences & Technology'),
        ('mathematics', 'Mathematics'),
        ('arts', 'Arts & Humanities'),
        ('social', 'Social Sciences & History'),
        ('business', 'Business & Economics'),
        ('sports', 'Physical Education & Sports'),
        ('other', 'General / Other'),
    ], string='Department / Category', default='languages')
    course_type = fields.Selection([
        ('core', 'Core Course'),
        ('elective', 'Elective Course'),
        ('lab', 'Practical / Lab'),
    ], string='Course Type', default='core')
    credits = fields.Integer(string='Credits / Units', default=3)
    color = fields.Integer(string='Color Index', default=4)
    description = fields.Text(string='Description & Syllabus')
    active = fields.Boolean(default=True)

    # Relations
    teacher_ids = fields.Many2many(
        'school.teacher',
        'school_subject_school_teacher_rel',
        'school_subject_id',
        'school_teacher_id',
        string='Assigned Teachers',
    )
    class_ids = fields.Many2many(
        'school.class',
        'school_class_school_subject_rel',
        'school_subject_id',
        'school_class_id',
        string='Classes',
    )
    exam_ids = fields.One2many('school.exam', 'subject_id', string='Exams')

    # Weekly Teaching & Study Assignments
    teaching_assignment_ids = fields.One2many('school.teaching.assignment', 'subject_id', string='Teaching Assignments')
    student_subject_ids = fields.One2many('school.student.subject', 'subject_id', string='Enrolled Students Studying')

    # Stat counters
    teacher_count = fields.Integer(string='Total Teachers', compute='_compute_stats', store=True)
    class_count = fields.Integer(string='Total Classes', compute='_compute_stats', store=True)
    exam_count = fields.Integer(string='Total Exams', compute='_compute_stats', store=True)
    student_study_count = fields.Integer(string='Students Studying', compute='_compute_stats', store=True)

    @api.depends('teacher_ids', 'class_ids', 'exam_ids', 'student_subject_ids', 'student_subject_ids.study_status')
    def _compute_stats(self):
        for rec in self:
            rec.teacher_count = len(rec.teacher_ids)
            rec.class_count = len(rec.class_ids)
            rec.exam_count = len(rec.exam_ids)
            active_studies = rec.student_subject_ids.filtered(lambda s: s.study_status == 'active')
            rec.student_study_count = len(active_studies)

    def action_view_teachers(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].sudo()._for_xml_id('school_management.action_teacher')
        action['domain'] = [('id', 'in', self.teacher_ids.ids)]
        action['context'] = {'default_subject_ids': [(4, self.id)]}
        return action

    def action_view_classes(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].sudo()._for_xml_id('school_management.action_class')
        action['domain'] = [('id', 'in', self.class_ids.ids)]
        return action

    def action_view_exams(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].sudo()._for_xml_id('school_management.action_exam')
        action['domain'] = [('subject_id', '=', self.id)]
        action['context'] = {'default_subject_id': self.id}
        return action

    def action_view_students_studying(self):
        self.ensure_one()
        student_ids = self.student_subject_ids.mapped('student_id').ids
        return {
            'name': _("Students Studying - %s") % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', student_ids)],
            'context': {'default_subject_id': self.id},
        }

    def action_view_teaching_assignments(self):
        self.ensure_one()
        return {
            'name': _("Teaching Assignments - %s") % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.teaching.assignment',
            'view_mode': 'list,form',
            'domain': [('subject_id', '=', self.id)],
            'context': {'default_subject_id': self.id},
        }
