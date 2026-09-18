from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SchoolStudentSubject(models.Model):
    _name = 'school.student.subject'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Student Weekly Study Subject'
    _order = 'student_id, subject_id'
    _rec_name = 'display_name'

    student_id = fields.Many2one(
        'school.student',
        string='Student',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    student_code = fields.Char(string='Student ID', related='student_id.student_id', readonly=True)
    class_id = fields.Many2one(
        'school.class',
        string='Class',
        compute='_compute_class_id',
        store=True,
        readonly=False,
        index=True
    )
    subject_id = fields.Many2one(
        'school.subject',
        string='Subject',
        required=True,
        index=True,
        tracking=True
    )
    teacher_id = fields.Many2one(
        'school.teacher',
        string='Subject Teacher',
        compute='_compute_teacher_and_hours',
        store=True,
        readonly=False,
        tracking=True,
        help="Teacher delivering this subject to the student."
    )
    subject_type = fields.Selection([
        ('core', 'Core Subject'),
        ('elective', 'Elective Course'),
        ('extra', 'Extra / Remedial'),
    ], string='Subject Type', default='core', required=True, tracking=True)

    weekly_hours = fields.Float(
        string='Weekly Study Hours',
        default=3.0,
        required=True,
        tracking=True,
        help="Target weekly hours of lecture / study required for this subject."
    )
    weekly_sessions = fields.Integer(
        string='Weekly Sessions',
        default=2,
        required=True,
        tracking=True,
        help="Target number of weekly class timetable sessions."
    )

    # Timetable scheduling stats
    scheduled_hours = fields.Float(
        string='Scheduled Hours / Week',
        compute='_compute_timetable_stats',
        store=True,
        help="Actual scheduled weekly hours based on school.timetable sessions for this class & subject."
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

    study_status = fields.Selection([
        ('active', 'Studying'),
        ('exempt', 'Exempt'),
        ('completed', 'Completed'),
    ], string='Study Status', default='active', required=True, tracking=True)

    notes = fields.Text(string='Learning Goals & Remarks')
    active = fields.Boolean(default=True, tracking=True)
    display_name = fields.Char(string='Name', compute='_compute_display_name', store=True)

    _unique_student_subject_teacher = models.Constraint(
        'unique(student_id, subject_id, teacher_id)',
        'This subject and teacher combination is already registered in the weekly study plan for this student!',
    )

    @api.constrains('student_id', 'subject_id', 'teacher_id')
    def _check_unique_student_subject_teacher(self):
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('student_id', '=', rec.student_id.id),
                ('subject_id', '=', rec.subject_id.id),
            ]
            if rec.teacher_id:
                domain.append(('teacher_id', '=', rec.teacher_id.id))
            else:
                domain.append(('teacher_id', '=', False))
            if self.search_count(domain):
                t_name = rec.teacher_id.name if rec.teacher_id else _('Unassigned')
                raise ValidationError(_(
                    "Student '%(student)s' is already enrolled in Subject '%(subject)s' with Teacher '%(teacher)s'."
                ) % {
                    'student': rec.student_id.name,
                    'subject': rec.subject_id.name,
                    'teacher': t_name,
                })

    @api.depends('student_id.name', 'subject_id.name', 'weekly_hours')
    def _compute_display_name(self):
        for rec in self:
            stu_name = rec.student_id.name or _('Student')
            sub_name = rec.subject_id.name or _('Subject')
            rec.display_name = f"{stu_name} - {sub_name} ({rec.weekly_hours}h/wk)"

    @api.depends('student_id.class_id')
    def _compute_class_id(self):
        for rec in self:
            if rec.student_id.class_id:
                rec.class_id = rec.student_id.class_id

    @api.depends('class_id', 'subject_id')
    def _compute_teacher_and_hours(self):
        Assignment = self.env['school.teaching.assignment']
        for rec in self:
            if rec.class_id and rec.subject_id:
                asg = Assignment.search([
                    ('class_id', '=', rec.class_id.id),
                    ('subject_id', '=', rec.subject_id.id),
                ], limit=1)
                if asg:
                    if not rec.teacher_id:
                        rec.teacher_id = asg.teacher_id
                    if rec.weekly_hours == 3.0 and asg.weekly_hours:
                        rec.weekly_hours = asg.weekly_hours
                    if rec.weekly_sessions == 2 and asg.weekly_sessions:
                        rec.weekly_sessions = asg.weekly_sessions

    @api.depends('student_id', 'class_id', 'subject_id', 'teacher_id', 'weekly_hours')
    def _compute_timetable_stats(self):
        Timetable = self.env['school.timetable']
        for rec in self:
            if rec.subject_id:
                domain = [
                    ('active', '=', True),
                    '|',
                    ('subject_id', '=', rec.subject_id.id),
                    ('subject_ids', 'in', rec.subject_id.id),
                ]
                if rec.teacher_id:
                    domain.append(('teacher_id', '=', rec.teacher_id.id))

                if rec.student_id and rec.class_id:
                    domain.extend([
                        '|',
                        '|',
                        ('student_id', '=', rec.student_id.id),
                        ('student_ids', 'in', rec.student_id.id),
                        '&',
                        ('student_id', '=', False),
                        ('class_id', '=', rec.class_id.id),
                    ])
                elif rec.student_id:
                    domain.extend([
                        '|',
                        ('student_id', '=', rec.student_id.id),
                        ('student_ids', 'in', rec.student_id.id),
                    ])
                elif rec.class_id:
                    domain.append(('class_id', '=', rec.class_id.id))
                slots = Timetable.search(domain)
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
                raise ValidationError(_("Weekly study hours must be greater than zero."))
            if rec.weekly_sessions <= 0:
                raise ValidationError(_("Weekly sessions count must be greater than zero."))

    def action_view_timetable(self):
        self.ensure_one()
        domain = [
            ('active', '=', True),
            '|',
            ('subject_id', '=', self.subject_id.id),
            ('subject_ids', 'in', self.subject_id.id),
        ]
        if self.teacher_id:
            domain.append(('teacher_id', '=', self.teacher_id.id))

        if self.student_id and self.class_id:
            domain.extend([
                '|',
                '|',
                ('student_id', '=', self.student_id.id),
                ('student_ids', 'in', self.student_id.id),
                '&',
                ('student_id', '=', False),
                ('class_id', '=', self.class_id.id),
            ])
        elif self.student_id:
            domain.extend([
                '|',
                ('student_id', '=', self.student_id.id),
                ('student_ids', 'in', self.student_id.id),
            ])
        elif self.class_id:
            domain.append(('class_id', '=', self.class_id.id))

        title = _("Timetable: %s") % self.subject_id.name
        if self.student_id:
            title += " (%s)" % self.student_id.name
        elif self.class_id:
            title += " - %s" % self.class_id.name

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': domain,
            'context': {
                'default_class_id': self.class_id.id if self.class_id else False,
                'default_student_id': self.student_id.id if self.student_id else False,
                'default_subject_id': self.subject_id.id,
                'default_subject_ids': [(6, 0, [self.subject_id.id])],
                'default_teacher_id': self.teacher_id.id if self.teacher_id else False,
            },
        }
