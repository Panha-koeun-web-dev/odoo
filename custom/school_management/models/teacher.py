from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SchoolTeacher(models.Model):
    _name = 'school.teacher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'School Teacher'
    _order = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    employee_id = fields.Char(string='Teacher ID', required=True, tracking=True, copy=False)
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    date_of_birth = fields.Date(string='Date of Birth')
    hire_date = fields.Date(string='Hire Date', default=fields.Date.today, tracking=True)
    subject_ids = fields.Many2many('school.subject', string='Subjects')
    class_ids = fields.One2many('school.class', 'teacher_id', string='Assigned Classes')
    photo = fields.Image(string='Photo', max_width=512, max_height=512, verify_resolution=True)
    active = fields.Boolean(default=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Related User')
    notes = fields.Text(string='Notes')

    # Timetable & Teaching Schedule Integration
    timetable_ids = fields.Many2many(
        'school.timetable',
        string='Teaching Schedule & School Timetable',
        compute='_compute_timetable_ids',
        help="All teaching sessions assigned to this teacher as well as school holidays."
    )
    timetable_count = fields.Integer(string='Timetable Sessions', compute='_compute_timetable_ids')
    holiday_count = fields.Integer(string='Class & School Holidays Count', compute='_compute_timetable_ids')

    # Weekly Teaching Assignments & Load
    teaching_assignment_ids = fields.One2many('school.teaching.assignment', 'teacher_id', string='Teaching Assignments')
    teaching_assignment_count = fields.Integer(string='Assignment Count', compute='_compute_teaching_stats')
    total_weekly_teaching_hours = fields.Float(string='Weekly Teaching Hours', compute='_compute_teaching_stats')
    total_weekly_teaching_sessions = fields.Integer(string='Weekly Teaching Sessions', compute='_compute_teaching_stats')
    total_scheduled_teaching_hours = fields.Float(string='Scheduled Teaching Hours', compute='_compute_teaching_stats')
    students_taught_ids = fields.Many2many('school.student', string='Students Taught', compute='_compute_teaching_stats')
    students_taught_count = fields.Integer(string='Students Taught Count', compute='_compute_teaching_stats')
    student_feedback_ids = fields.One2many(
        'school.feedback',
        'teacher_id',
        string='Student Feedback Given',
        domain=[('report_type', '=', 'teacher_to_student')],
    )
    teaching_evaluation_ids = fields.One2many(
        'school.feedback',
        'teacher_id',
        string='Teaching Evaluations Received',
        domain=[('report_type', '=', 'student_to_teacher')],
    )
    student_feedback_count = fields.Integer(string='Student Feedback', compute='_compute_teacher_feedback_counts')
    teaching_evaluation_count = fields.Integer(string='Teaching Reports', compute='_compute_teacher_feedback_counts')

    class_count = fields.Integer(string='Class Count', compute='_compute_teacher_stats')
    student_count = fields.Integer(string='Student Count', compute='_compute_teacher_stats')
    subject_count = fields.Integer(string='Subject Count', compute='_compute_teacher_stats')

    # Permission & Leave Integration
    permission_ids = fields.One2many(
        'school.permission',
        'teacher_id',
        string='Permission Requests',
        domain=[('applicant_type', '=', 'teacher')],
    )
    permission_count = fields.Integer(
        string='Permissions Count',
        compute='_compute_permission_count',
    )
    permission_approved_count = fields.Integer(
        string='Approved Leaves',
        compute='_compute_permission_count',
    )
    permission_pending_count = fields.Integer(
        string='Pending Permissions',
        compute='_compute_permission_count',
    )
    permission_total_days = fields.Float(
        string='Total Leave Days',
        compute='_compute_permission_count',
    )

    @api.depends('permission_ids.state', 'permission_ids.duration_days')
    def _compute_permission_count(self):
        for rec in self:
            perms = rec.permission_ids
            rec.permission_count = len(perms)
            approved = perms.filtered(lambda p: p.state == 'approved')
            rec.permission_approved_count = len(approved)
            rec.permission_pending_count = len(perms.filtered(lambda p: p.state == 'draft'))
            rec.permission_total_days = sum(approved.mapped('duration_days'))

    def action_request_permission(self):
        self.ensure_one()
        return {
            'name': _('New Teacher Leave Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.permission',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_applicant_type': 'teacher',
                'default_teacher_id': self.id,
            },
        }

    def _compute_teacher_feedback_counts(self):
        for rec in self:
            rec.student_feedback_count = self.env['school.feedback'].search_count([
                ('teacher_id', '=', rec.id),
                ('report_type', '=', 'teacher_to_student'),
            ])
            rec.teaching_evaluation_count = self.env['school.feedback'].search_count([
                ('teacher_id', '=', rec.id),
                ('report_type', '=', 'student_to_teacher'),
            ])

    def action_view_student_feedback(self):
        self.ensure_one()
        return {
            'name': _("Student Feedback by %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.feedback',
            'view_mode': 'list,form',
            'domain': [('teacher_id', '=', self.id), ('report_type', '=', 'teacher_to_student')],
            'context': {'default_teacher_id': self.id, 'default_report_type': 'teacher_to_student'},
        }

    def action_view_teaching_evaluations(self):
        self.ensure_one()
        return {
            'name': _("Teaching Quality Reports: %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.feedback',
            'view_mode': 'list,form',
            'domain': [('teacher_id', '=', self.id), ('report_type', '=', 'student_to_teacher')],
            'context': {'default_teacher_id': self.id, 'default_report_type': 'student_to_teacher'},
        }

    def action_view_permissions(self):
        self.ensure_one()
        return {
            'name': _('Permissions & Leaves - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.permission',
            'view_mode': 'list,kanban,calendar,form',
            'domain': [('teacher_id', '=', self.id), ('applicant_type', '=', 'teacher')],
            'context': {
                'default_applicant_type': 'teacher',
                'default_teacher_id': self.id,
            },
        }

    @api.depends('class_ids', 'class_ids.student_ids', 'subject_ids')
    def _compute_teacher_stats(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)
            students = rec.class_ids.mapped('student_ids')
            rec.student_count = len(students)
            rec.subject_count = len(rec.subject_ids)

    @api.depends(
        'teaching_assignment_ids',
        'teaching_assignment_ids.weekly_hours',
        'teaching_assignment_ids.weekly_sessions',
        'teaching_assignment_ids.scheduled_hours',
        'teaching_assignment_ids.student_ids',
        'teaching_assignment_ids.active',
    )
    def _compute_teaching_stats(self):
        for rec in self:
            active_asgs = rec.teaching_assignment_ids.filtered(lambda a: a.active)
            rec.teaching_assignment_count = len(active_asgs)
            rec.total_weekly_teaching_hours = sum(active_asgs.mapped('weekly_hours'))
            rec.total_weekly_teaching_sessions = sum(active_asgs.mapped('weekly_sessions'))
            rec.total_scheduled_teaching_hours = sum(active_asgs.mapped('scheduled_hours'))
            students = active_asgs.mapped('student_ids')
            rec.students_taught_ids = [(6, 0, students.ids)]
            rec.students_taught_count = len(students)

    def _compute_timetable_ids(self):
        Timetable = self.env['school.timetable']
        for teacher in self:
            class_ids = teacher.class_ids.ids
            # Teacher sees their own teaching sessions + school/class holidays
            domain = [
                ('active', '=', True),
                '|',
                ('teacher_id', '=', teacher.id),
                '&',
                ('is_holiday', '=', True),
                '|',
                ('class_id', '=', False),
                ('class_id', 'in', class_ids or [False])
            ]
            sessions = Timetable.search(domain)
            teacher.timetable_ids = [(6, 0, sessions.ids)]
            teacher.timetable_count = len(sessions)
            holiday_domain = [
                ('active', '=', True),
                ('is_holiday', '=', True),
                '|',
                ('class_id', '=', False),
                ('class_id', 'in', class_ids or [False]),
            ]
            teacher.holiday_count = Timetable.search_count(holiday_domain)

    def _compute_timetable_count(self):
        return self._compute_timetable_ids()

    def action_view_timetable(self):
        self.ensure_one()
        class_ids = self.class_ids.ids
        domain = [
            ('active', '=', True),
            '|',
            ('teacher_id', '=', self.id),
            '&',
            ('is_holiday', '=', True),
            '|',
            ('class_id', '=', False),
            ('class_id', 'in', class_ids or [False])
        ]
        return {
            'name': _('Teaching Schedule - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': domain,
            'context': {
                'default_teacher_id': self.id,
                'search_default_filter_mon_fri': 1,
            },
        }

    def action_view_master_timetable(self):
        self.ensure_one()
        return {
            'name': _('Master Timetable & Calendar'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'context': {'search_default_filter_mon_fri': 1},
        }

    def action_view_holidays(self):
        self.ensure_one()
        class_ids = self.class_ids.ids
        domain = [
            ('active', '=', True),
            ('is_holiday', '=', True),
            '|',
            ('class_id', '=', False),
            ('class_id', 'in', class_ids or [False]),
        ]
        return {
            'name': _('My Teaching & Class Holidays - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': domain,
            'context': {
                'default_is_holiday': True,
                'search_default_filter_holidays': 1,
            },
        }

    def action_view_teaching_assignments(self):
        self.ensure_one()
        return {
            'name': _('Teaching Assignments - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.teaching.assignment',
            'view_mode': 'list,form',
            'domain': [('teacher_id', '=', self.id)],
            'context': {'default_teacher_id': self.id},
        }

    def action_view_students_taught(self):
        self.ensure_one()
        students = self.students_taught_ids.ids or self.class_ids.mapped('student_ids').ids
        return {
            'name': _('Students Taught - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', students)],
            'context': {'default_teacher_id': self.id},
        }

    def action_view_classes(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('school_management.action_class')
        action['domain'] = [('teacher_id', '=', self.id)]
        action['context'] = {'default_teacher_id': self.id}
        return action

    def action_view_students(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('school_management.action_student')
        student_ids = self.class_ids.mapped('student_ids').ids
        action['domain'] = [('id', 'in', student_ids)]
        return action

    def action_view_subjects(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('school_management.action_subject')
        action['domain'] = [('id', 'in', self.subject_ids.ids)]
        return action

    def action_create_user(self):
        """Create or link an Odoo user account for this teacher with default password 'password123'."""
        # Step 1: Ensure this action is run on a single teacher record
        self.ensure_one()

        # Step 2: Validate that email exists because it will be used as the login username
        if not self.email:
            raise UserError(_("Please provide an email address for the teacher first."))

        login = self.email.strip().lower()
        existing_user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        group_teacher = self.env.ref('school_management.group_school_teacher')
        group_internal = self.env.ref('base.group_user')
        # Step 3: Default password preset for teacher accounts
        action_teacher = self.env.ref('school_management.action_teacher', raise_if_not_found=False)

        default_pwd = 'password123'
        groups_to_add = [(4, group_teacher.id), (4, group_internal.id)]

        if existing_user:
            # Step 4A: Account already exists -> Grant teacher groups and link to this record
            existing_user.sudo().write({
                'name': self.name,
                'email': self.email,
                'password': default_pwd,  # Set password to default_pwd ('password123')
                'group_ids': groups_to_add,
                'action_id': action_teacher.id if action_teacher else False,
            })
            self.sudo().write({'user_id': existing_user.id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("User Account Linked"),
                    'message': _("Existing user account linked for Teacher %s.\nEmail / Login: %s\nPassword: %s") % (self.name, login, default_pwd),
                    'type': 'success',
                    'sticky': True,
                }
            }

        # Step 4B: Account does not exist -> Create new partner and user with password 'password123'
        partner_vals = {'name': self.name, 'email': self.email}
        if 'autopost_bills' in self.env['res.partner']._fields:
            partner_vals['autopost_bills'] = 'never'
        partner = self.env['res.partner'].sudo().create(partner_vals)

        user_vals = {
            'name': self.name,
            'login': login,
            'email': self.email,
            'password': default_pwd,  # Direct password setup: 'password123'
            'partner_id': partner.id,
            'group_ids': [(6, 0, [group_internal.id, group_teacher.id])],
            'action_id': action_teacher.id if action_teacher else False,
        }
        new_user = self.env['res.users'].sudo().create(user_vals)
        self.sudo().write({'user_id': new_user.id})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Account Created Successfully"),
                'message': _("Created login account for Teacher %s!\nEmail / Login: %s\nPassword: %s") % (self.name, login, default_pwd),
                'type': 'success',
                'sticky': True,
            }
        }

    def action_reset_user_password(self):
        """
        Reset teacher's portal/system user password to default 'password123'.
        Allows school administrators to immediately restore access for teachers without email dependency.
        """
        # Step 1: Ensure this action is executed on a single teacher record
        self.ensure_one()

        # Step 2: Check if there is an associated user account
        if not self.user_id:
            raise UserError(_("No user account is linked to this teacher."))

        # Step 3: Define the default password for reset
        default_pwd = 'password123'

        # Step 4: Write the new password directly to res.users table with sudo privileges
        self.user_id.sudo().write({'password': default_pwd})

        # Step 5: Show an informative notification to the administrator displaying credentials
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Password Reset Successfully"),
                'message': _("Password for teacher '%s' (%s) has been reset to: %s") % (
                    self.name, self.user_id.login, default_pwd
                ),
                'type': 'info',
                'sticky': True,
            }
        }

    def action_open_assign_wizard(self):
        self.ensure_one()
        return {
            'name': _('Assign Subject & Students - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.assign.subject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_assign_target': 'teacher',
                'default_teacher_id': self.id,
            },
        }

    @api.constrains('employee_id')
    def _check_unique_employee_id(self):
        for rec in self:
            if rec.employee_id:
                dup = self.search([
                    ('employee_id', '=', rec.employee_id.strip()),
                    ('id', '!=', rec.id)
                ], limit=1)
                if dup:
                    raise ValidationError(_("Teacher ID '%s' is already in use by %s. Teacher IDs must be unique.") % (rec.employee_id, dup.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('employee_id'):
                last_teacher = self.search([('employee_id', '=like', 'TCH-%')], order='id desc', limit=1)
                next_num = 1
                if last_teacher and last_teacher.employee_id:
                    try:
                        num_part = int(last_teacher.employee_id.replace('TCH-', ''))
                        next_num = num_part + 1
                    except (ValueError, TypeError):
                        next_num = self.search_count([]) + 1
                else:
                    next_num = self.search_count([]) + 1
                vals['employee_id'] = f"TCH-{next_num:03d}"
            elif isinstance(vals.get('employee_id'), str):
                vals['employee_id'] = vals['employee_id'].strip()
        return super().create(vals_list)

    def write(self, vals):
        if 'employee_id' in vals:
            if not self.env.user.has_group('school_management.group_school_admin') and not self.env.is_superuser():
                raise UserError(_("Only a School Administrator can change the Teacher ID."))
            if isinstance(vals['employee_id'], str):
                vals['employee_id'] = vals['employee_id'].strip()
        return super().write(vals)
