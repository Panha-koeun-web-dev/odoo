from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SchoolTeachingAssignment(models.Model):
    _name = 'school.teaching.assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Teacher Weekly Teaching Assignment'
    _order = 'teacher_id, class_id, subject_id'
    _rec_name = 'display_name'

    teacher_id = fields.Many2one(
        'school.teacher',
        string='Teacher',
        required=True,
        tracking=True,
        index=True,
        ondelete='cascade'
    )
    subject_id = fields.Many2one(
        'school.subject',
        string='Subject',
        required=True,
        tracking=True,
        index=True,
        ondelete='cascade'
    )
    class_id = fields.Many2one(
        'school.class',
        string='Class',
        required=True,
        tracking=True,
        index=True,
        ondelete='cascade'
    )
    weekly_hours = fields.Float(
        string='Weekly Teaching Hours',
        default=3.0,
        required=True,
        tracking=True,
        help="Planned number of hours this teacher must teach this subject to this class each week."
    )
    weekly_sessions = fields.Integer(
        string='Weekly Sessions',
        default=2,
        required=True,
        tracking=True,
        help="Target number of class periods / timetable sessions per week."
    )

    # Students reached
    student_ids = fields.Many2many(
        'school.student',
        string='Students Taught',
        compute='_compute_students',
        store=True,
        help="Students enrolled in this class who are receiving instruction in this subject."
    )
    student_count = fields.Integer(
        string='Students Count',
        compute='_compute_students',
        store=True
    )

    # Timetable integration
    scheduled_hours = fields.Float(
        string='Scheduled Hours / Week',
        compute='_compute_timetable_stats',
        store=True,
        help="Actual scheduled weekly hours based on school.timetable sessions."
    )
    scheduled_sessions = fields.Integer(
        string='Scheduled Sessions',
        compute='_compute_timetable_stats',
        store=True,
        help="Actual scheduled weekly periods based on school.timetable sessions."
    )
    schedule_status = fields.Selection([
        ('not_scheduled', 'Not Scheduled'),
        ('under_scheduled', 'Under Scheduled'),
        ('fully_scheduled', 'Fully Scheduled'),
        ('over_scheduled', 'Over Scheduled'),
    ], string='Schedule Status', compute='_compute_timetable_stats', store=True)

    notes = fields.Text(string='Syllabus & Lesson Objectives')
    active = fields.Boolean(default=True, tracking=True)
    display_name = fields.Char(string='Assignment Name', compute='_compute_display_name', store=True)

    _unique_assignment = models.Constraint(
        'unique(teacher_id, subject_id, class_id)',
        'This teacher is already assigned to teach this subject in this class!',
    )

    @api.depends('teacher_id.name', 'subject_id.name', 'class_id.name', 'weekly_hours')
    def _compute_display_name(self):
        for rec in self:
            t_name = rec.teacher_id.name or _('Teacher')
            s_name = rec.subject_id.name or _('Subject')
            c_name = rec.class_id.name or _('Class')
            rec.display_name = f"{s_name} - {c_name} ({t_name}, {rec.weekly_hours}h/wk)"

    @api.depends('class_id.student_ids', 'class_id.student_ids.study_status', 'class_id.student_ids.active')
    def _compute_students(self):
        for rec in self:
            if rec.class_id:
                active_students = rec.class_id.student_ids.filtered(
                    lambda s: s.active and s.study_status == 'studying'
                )
                rec.student_ids = [(6, 0, active_students.ids)]
                rec.student_count = len(active_students)
            else:
                rec.student_ids = [(5, 0, 0)]
                rec.student_count = 0

    @api.depends('teacher_id', 'subject_id', 'class_id', 'weekly_hours')
    def _compute_timetable_stats(self):
        Timetable = self.env['school.timetable']
        for rec in self:
            if rec.class_id and rec.subject_id and rec.teacher_id:
                slots = Timetable.search([
                    ('class_id', '=', rec.class_id.id),
                    ('teacher_id', '=', rec.teacher_id.id),
                    ('active', '=', True),
                    '|',
                    ('subject_id', '=', rec.subject_id.id),
                    ('subject_ids', 'in', rec.subject_id.id),
                ])
                total_hours = sum(max(0.0, (s.end_time or 0.0) - (s.start_time or 0.0)) for s in slots)
                rec.scheduled_hours = round(total_hours, 2)
                rec.scheduled_sessions = len(slots)
            else:
                rec.scheduled_hours = 0.0
                rec.scheduled_sessions = 0

            target = rec.weekly_hours or 0.0
            if rec.scheduled_sessions == 0:
                rec.schedule_status = 'not_scheduled'
            elif rec.scheduled_hours < (target - 0.05):
                rec.schedule_status = 'under_scheduled'
            elif abs(rec.scheduled_hours - target) <= 0.05:
                rec.schedule_status = 'fully_scheduled'
            else:
                rec.schedule_status = 'over_scheduled'

    @api.constrains('weekly_hours', 'weekly_sessions')
    def _check_workload(self):
        for rec in self:
            if rec.weekly_hours <= 0:
                raise ValidationError(_("Weekly teaching hours must be greater than zero."))
            if rec.weekly_sessions <= 0:
                raise ValidationError(_("Weekly sessions count must be greater than zero."))

    def action_view_students(self):
        self.ensure_one()
        return {
            'name': _("Students in %s - %s") % (self.class_id.name, self.subject_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.student_ids.ids)],
            'context': {
                'default_class_id': self.class_id.id,
            },
        }

    def action_view_timetable(self):
        self.ensure_one()
        return {
            'name': _("Timetable: %s - %s") % (self.subject_id.name, self.class_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': [
                ('class_id', '=', self.class_id.id),
                ('teacher_id', '=', self.teacher_id.id),
                '|',
                ('subject_id', '=', self.subject_id.id),
                ('subject_ids', 'in', self.subject_id.id),
            ],
            'context': {
                'default_class_id': self.class_id.id,
                'default_subject_ids': [(6, 0, [self.subject_id.id])],
                'default_subject_id': self.subject_id.id,
                'default_teacher_id': self.teacher_id.id,
            },
        }

    def action_open_schedule_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quick Schedule Session'),
            'res_model': 'school.assign.subject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mode': 'schedule_quick',
                'default_teacher_id': self.teacher_id.id,
                'default_subject_id': self.subject_id.id,
                'default_class_id': self.class_id.id,
                'default_room': self.class_id.room if self.class_id else '',
            }
        }
