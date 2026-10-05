from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolEnrollment(models.Model):
    _name = 'school.enrollment'
    _description = 'Student Enrollment & Weekly Subjects'
    _order = 'enrollment_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(string='Name', compute='_compute_display_name', store=True)
    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade', tracking=True)
    student_code = fields.Char(string='Student ID', related='student_id.student_id', readonly=True)
    student_email = fields.Char(string='Student Email', related='student_id.email', readonly=True)
    student_phone = fields.Char(string='Student Phone', related='student_id.phone', readonly=True)
    class_id = fields.Many2one('school.class', string='Class', required=True, ondelete='cascade', tracking=True)
    academic_year = fields.Char(string='Academic Year', required=True, default='2025-2026', tracking=True)
    semester = fields.Selection([
        ('1', 'Semester 1'),
        ('2', 'Semester 2'),
        ('full', 'Full Year'),
    ], string='Semester', required=True, default='1', tracking=True)
    enrollment_date = fields.Date(string='Enrollment Date', required=True, default=fields.Date.today, tracking=True)
    subject_ids = fields.Many2many('school.subject', string='Enrolled Curriculum Subjects')

    # Weekly Study Subjects Integration
    student_subject_ids = fields.Many2many(
        'school.student.subject',
        string='Weekly Study Subjects',
        compute='_compute_student_subjects',
        help='Weekly study subjects registered for this student and class.'
    )
    student_subject_count = fields.Integer(
        string='Weekly Subjects Count',
        compute='_compute_student_subjects',
        search='_search_student_subject_count',
    )
    total_weekly_hours = fields.Float(
        string='Target Weekly Hours',
        compute='_compute_student_subjects',
    )
    scheduled_weekly_hours = fields.Float(
        string='Scheduled Weekly Hours',
        compute='_compute_student_subjects',
    )

    notes = fields.Text(string='Notes')

    _unique_enrollment = models.Constraint(
        'unique(student_id, class_id, academic_year, semester)',
        'This student is already enrolled in this class and semester for the selected academic year!',
    )

    @api.depends('student_id.name', 'class_id.name', 'academic_year', 'semester')
    def _compute_display_name(self):
        for rec in self:
            stu_name = rec.student_id.name or _('Student')
            cls_name = rec.class_id.name or _('Class')
            sem_name = dict(self._fields['semester'].selection).get(rec.semester, rec.semester or '')
            rec.display_name = f"{stu_name} - {cls_name} ({rec.academic_year} {sem_name})"

    @api.depends('student_id', 'class_id', 'subject_ids')
    def _compute_student_subjects(self):
        StudentSubject = self.env['school.student.subject']
        for rec in self:
            if rec.student_id:
                domain = [('student_id', '=', rec.student_id.id)]
                if rec.class_id:
                    domain.append(('class_id', '=', rec.class_id.id))
                subs = StudentSubject.search(domain)
                rec.student_subject_ids = [(6, 0, subs.ids)]
                rec.student_subject_count = len(subs)
                rec.total_weekly_hours = sum(s.weekly_hours for s in subs)
                rec.scheduled_weekly_hours = sum(s.scheduled_hours for s in subs)
            else:
                rec.student_subject_ids = [(6, 0, [])]
                rec.student_subject_count = 0
                rec.total_weekly_hours = 0.0
                rec.scheduled_weekly_hours = 0.0

    def _search_student_subject_count(self, operator, value):
        self.env.cr.execute("""
            SELECT DISTINCT e.id
            FROM school_enrollment e
            JOIN school_student_subject ss ON (ss.student_id = e.student_id)
            WHERE ss.active = true
        """)
        res = [r[0] for r in self.env.cr.fetchall()]
        if (operator in ('>', '!=') and value == 0) or (operator == '=' and value > 0):
            return [('id', 'in', res)]
        elif (operator == '=' and value == 0):
            return [('id', 'not in', res)]
        return [('id', 'in', res)]

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            self.subject_ids = self.class_id.subject_ids

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id and not self.class_id:
            self.class_id = self.student_id.class_id

    def _sync_student_subjects(self):
        """Automatically create or update school.student.subject weekly study plans for enrolled subjects."""
        StudentSubject = self.env['school.student.subject']
        Assignment = self.env['school.teaching.assignment']
        total_synced = 0
        for rec in self:
            if not rec.student_id:
                continue
            subjects = rec.subject_ids
            if not subjects and rec.class_id and rec.class_id.subject_ids:
                subjects = rec.class_id.subject_ids
            if not subjects:
                continue

            for sub in subjects:
                assigned_teacher = False
                w_hours = 3.0
                w_sessions = 2
                if rec.class_id:
                    asg = Assignment.search([
                        ('class_id', '=', rec.class_id.id),
                        ('subject_id', '=', sub.id),
                        ('active', '=', True),
                    ], limit=1)
                    if asg:
                        assigned_teacher = asg.teacher_id
                        if asg.weekly_hours:
                            w_hours = asg.weekly_hours
                        if asg.weekly_sessions:
                            w_sessions = asg.weekly_sessions

                if not assigned_teacher and sub.teacher_ids:
                    assigned_teacher = sub.teacher_ids[0]
                if not assigned_teacher and rec.class_id and rec.class_id.teacher_id:
                    assigned_teacher = rec.class_id.teacher_id

                existing = StudentSubject.search([
                    ('student_id', '=', rec.student_id.id),
                    ('subject_id', '=', sub.id),
                ], limit=1)

                if existing:
                    vals = {}
                    if rec.class_id and not existing.class_id:
                        vals['class_id'] = rec.class_id.id
                    if assigned_teacher and not existing.teacher_id:
                        vals['teacher_id'] = assigned_teacher.id
                    if not existing.active:
                        vals['active'] = True
                    if vals:
                        existing.write(vals)
                else:
                    StudentSubject.create({
                        'student_id': rec.student_id.id,
                        'class_id': rec.class_id.id if rec.class_id else False,
                        'subject_id': sub.id,
                        'teacher_id': assigned_teacher.id if assigned_teacher else False,
                        'weekly_hours': w_hours,
                        'weekly_sessions': w_sessions,
                        'study_status': 'active',
                        'active': True,
                    })
                total_synced += 1
        return total_synced

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.class_id and rec.student_id:
                rec.student_id.class_id = rec.class_id
            rec._sync_student_subjects()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('class_id', 'student_id', 'subject_ids')):
            for rec in self:
                if rec.class_id and rec.student_id:
                    rec.student_id.class_id = rec.class_id
                rec._sync_student_subjects()
        return res

    def action_enroll_weekly_subjects(self):
        """Open the Weekly Subject Enrollment wizard pre-filled for this student."""
        self.ensure_one()
        return {
            'name': _("Enroll in Weekly Subjects - %s") % (self.student_id.name or _("Student")),
            'type': 'ir.actions.act_window',
            'res_model': 'school.assign.subject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mode': 'student_enroll',
                'default_class_id': self.class_id.id if self.class_id else False,
                'default_student_ids': [(6, 0, [self.student_id.id])],
                'default_subject_ids': [(6, 0, self.subject_ids.ids)] if self.subject_ids else False,
            }
        }

    def action_sync_weekly_subjects(self):
        """Action button to trigger immediate auto-generation of weekly study subjects."""
        self.ensure_one()
        count = self._sync_student_subjects()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Weekly Subjects Synchronized'),
                'message': _('Successfully synchronized %d weekly study subject(s) for %s.') % (count, self.student_id.name or _("Student")),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_student_subjects(self):
        """Stat button to navigate to weekly study subjects for this student."""
        self.ensure_one()
        domain = [('student_id', '=', self.student_id.id)]
        if self.class_id:
            domain.append(('class_id', '=', self.class_id.id))
        return {
            'name': _("Weekly Subjects - %s") % (self.student_id.name or _("Student")),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.subject',
            'view_mode': 'list,kanban,form',
            'domain': domain,
            'context': {
                'default_student_id': self.student_id.id,
                'default_class_id': self.class_id.id if self.class_id else False,
            }
        }

    def action_view_timetable(self):
        """Stat button to inspect weekly timetable sessions for this class."""
        self.ensure_one()
        domain = [('active', '=', True)]
        if self.class_id:
            domain.append(('class_id', '=', self.class_id.id))
        return {
            'name': _("Class Timetable - %s") % (self.class_id.name if self.class_id else (self.student_id.name or _("Student"))),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': domain,
            'context': {
                'default_class_id': self.class_id.id if self.class_id else False,
            }
        }
