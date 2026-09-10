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

    class_count = fields.Integer(string='Classes', compute='_compute_teacher_stats')
    student_count = fields.Integer(string='Students', compute='_compute_teacher_stats')

    @api.depends('class_ids', 'class_ids.student_ids')
    def _compute_teacher_stats(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)
            students = rec.class_ids.mapped('student_ids')
            rec.student_count = len(students)

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

    def action_create_user(self):
        self.ensure_one()
        if not self.email:
            raise UserError(_("Please provide an email address for the teacher first."))

        login = self.email.strip().lower()
        existing_user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        group_teacher = self.env.ref('school_management.group_school_teacher')
        group_internal = self.env.ref('base.group_user')
        group_portal = self.env.ref('base.group_portal', raise_if_not_found=False)
        action_student = self.env.ref('school_management.action_student', raise_if_not_found=False)

        default_pwd = 'password123'
        groups_to_add = [(4, group_teacher.id), (4, group_internal.id)]
        if group_portal:
            groups_to_add.append((3, group_portal.id))

        if existing_user:
            existing_user.sudo().write({
                'name': self.name,
                'email': self.email,
                'group_ids': groups_to_add,
                'action_id': action_student.id if action_student else False,
            })
            self.sudo().write({'user_id': existing_user.id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('User Account Linked'),
                    'message': _('Linked to existing user account.\nEmail / Login: %s\nPassword: %s') % (login, default_pwd),
                    'type': 'success',
                    'sticky': True,
                }
            }
        else:
            new_user = self.env['res.users'].sudo().create({
                'name': self.name,
                'login': login,
                'email': self.email,
                'password': default_pwd,
                'group_ids': [(6, 0, [group_teacher.id, group_internal.id])],
                'action_id': action_student.id if action_student else False,
            })
            self.sudo().write({'user_id': new_user.id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Login Created Successfully'),
                    'message': _('Created login account for Teacher %s!\nEmail / Login: %s\nPassword: %s') % (self.name, login, default_pwd),
                    'type': 'success',
                    'sticky': True,
                }
            }

    def action_reset_user_password(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(_("No user account is linked to this teacher."))
        default_pwd = 'password123'
        self.user_id.sudo().write({'password': default_pwd})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Password Reset'),
                'message': _('Password for %s has been reset to: %s') % (self.user_id.login, default_pwd),
                'type': 'info',
                'sticky': True,
            }
        }
