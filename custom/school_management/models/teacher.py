from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SchoolTeacher(models.Model):
    _name = 'school.teacher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'School Teacher'
    _order = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    employee_id = fields.Char(string='Employee ID', required=True, tracking=True)
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
    photo = fields.Image(string='Photo')
    active = fields.Boolean(default=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Related User')
    notes = fields.Text(string='Notes')

    class_count = fields.Integer(string='Class Count', compute='_compute_teacher_stats')
    student_count = fields.Integer(string='Student Count', compute='_compute_teacher_stats')
    subject_count = fields.Integer(string='Subject Count', compute='_compute_teacher_stats')

    @api.depends('class_ids', 'class_ids.student_ids', 'subject_ids')
    def _compute_teacher_stats(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)
            students = rec.class_ids.mapped('student_ids')
            rec.student_count = len(students)
            rec.subject_count = len(rec.subject_ids)

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
        self.ensure_one()
        if not self.email:
            raise UserError(_("Please provide an email address for the teacher first."))

        login = self.email.strip().lower()
        existing_user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        group_teacher = self.env.ref('school_management.group_school_teacher')
        group_internal = self.env.ref('base.group_user')

        if existing_user:
            existing_user.sudo().write({
                'groups_id': [(4, group_teacher.id), (4, group_internal.id)]
            })
            self.user_id = existing_user.id
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Account Linked"),
                    'message': _("Existing user account (%s) linked as teacher.") % login,
                    'type': 'success',
                    'sticky': False,
                }
            }

        user_vals = {
            'name': self.name,
            'login': login,
            'email': login,
            'groups_id': [(6, 0, [group_internal.id, group_teacher.id])],
        }
        new_user = self.env['res.users'].sudo().create(user_vals)
        self.user_id = new_user.id
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Account Created"),
                'message': _("User account (%s) created successfully.") % login,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_user_password(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(_("No login account is associated with this teacher."))
        self.user_id.action_reset_password()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Password Reset Sent"),
                'message': _("A password reset email has been sent to %s.") % self.user_id.email,
                'type': 'info',
                'sticky': False,
            }
        }
