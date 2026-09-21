from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SchoolPermission(models.Model):
    _name = 'school.permission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Student Permission Request'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )

    @api.model
    def _default_student_id(self):
        student = self.env['school.student'].search([('user_id', '=', self.env.uid)], limit=1)
        if student:
            return student.id
        return self.env.context.get('default_student_id', False)

    student_id = fields.Many2one(
        'school.student',
        string='Student',
        required=True,
        tracking=True,
        default=_default_student_id,
    )
    student_code = fields.Char(
        related='student_id.student_id',
        string='Student ID',
        readonly=True,
    )
    student_phone = fields.Char(
        related='student_id.phone',
        string='Student Phone',
        readonly=True,
    )
    student_email = fields.Char(
        related='student_id.email',
        string='Student Email',
        readonly=True,
    )
    class_id = fields.Many2one(
        'school.class',
        related='student_id.class_id',
        string='Class',
        store=True,
        readonly=True,
    )
    teacher_id = fields.Many2one(
        'school.teacher',
        related='class_id.teacher_id',
        string='Class Teacher',
        store=True,
        readonly=True,
    )

    permission_type = fields.Selection([
        ('leave', 'Leave of Absence'),
        ('sick', 'Sick Leave'),
        ('emergency', 'Family / Emergency Affair'),
        ('activity', 'School Activity / Official Duty'),
        ('late', 'Late Arrival / Early Departure'),
        ('other', 'Other Reason'),
    ], string='Permission Type', required=True, default='leave', tracking=True)

    session_type = fields.Selection([
        ('full_day', 'Full Day(s)'),
        ('morning', 'Morning Session'),
        ('afternoon', 'Afternoon Session'),
        ('custom', 'Specific Hours'),
    ], string='Time Period', required=True, default='full_day', tracking=True)

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    start_time = fields.Float(string='Start Time', default=8.0)
    end_time = fields.Float(string='End Time', default=12.0)

    duration_days = fields.Float(
        string='Duration (Days)',
        compute='_compute_duration_days',
        store=True,
        help='Duration of the requested permission in days.',
    )

    reason = fields.Text(
        string='Reason / Description',
        required=True,
        tracking=True,
    )
    contact_phone = fields.Char(
        string='Contact Phone during Absence',
        help='Emergency contact telephone while on leave.',
    )
    parent_informed = fields.Boolean(
        string='Parent / Guardian Informed',
        default=True,
        help='Indicate whether parents or guardians are aware of this absence.',
    )

    state = fields.Selection([
        ('draft', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Not Approved'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, default='draft', tracking=True, copy=False)

    approved_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    approval_date = fields.Datetime(
        string='Review Date',
        readonly=True,
        copy=False,
    )
    approver_role = fields.Selection([
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
    ], string='Approver Role', compute='_compute_approver_role', store=True)

    rejection_reason = fields.Text(
        string='Reason for Non-Approval',
        copy=False,
        tracking=True,
    )

    auto_update_attendance = fields.Boolean(
        string='Auto-mark Excused in Attendance',
        default=True,
        help='Automatically record or update attendance as Excused for the approved dates.',
    )
    attendance_ids = fields.One2many(
        'school.attendance',
        'permission_id',
        string='Excused Attendance Records',
        readonly=True,
    )
    attendance_count = fields.Integer(
        string='Attendance Count',
        compute='_compute_attendance_count',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'school_permission_ir_attachments_rel',
        'permission_id',
        'attachment_id',
        string='Supporting Documents',
    )

    is_current_user_approver = fields.Boolean(
        string='Is Current User Approver',
        compute='_compute_user_roles',
    )
    is_current_user_student = fields.Boolean(
        string='Is Current User Student',
        compute='_compute_user_roles',
    )

    @api.depends('student_id', 'permission_type', 'name')
    def _compute_display_name(self):
        type_dict = dict(self._fields['permission_type'].selection)
        for rec in self:
            student_name = rec.student_id.name if rec.student_id else _('New')
            type_label = type_dict.get(rec.permission_type, _('Permission'))
            ref_part = f"[{rec.name}] " if rec.name and rec.name != 'New' else ""
            rec.display_name = f"{ref_part}{student_name} - {type_label}"

    @api.depends('start_date', 'end_date', 'session_type', 'start_time', 'end_time')
    def _compute_duration_days(self):
        for rec in self:
            if not rec.start_date or not rec.end_date:
                rec.duration_days = 0.0
                continue
            if rec.end_date < rec.start_date:
                rec.duration_days = 0.0
                continue

            day_span = (rec.end_date - rec.start_date).days + 1
            if day_span == 1:
                if rec.session_type in ('morning', 'afternoon'):
                    rec.duration_days = 0.5
                elif rec.session_type == 'custom':
                    hours = max(0.0, rec.end_time - rec.start_time)
                    rec.duration_days = max(0.1, round(hours / 8.0, 2))
                else:
                    rec.duration_days = 1.0
            else:
                rec.duration_days = float(day_span)

    @api.depends('approved_by')
    def _compute_approver_role(self):
        for rec in self:
            if not rec.approved_by:
                rec.approver_role = False
            elif rec.approved_by.has_group('school_management.group_school_admin'):
                rec.approver_role = 'admin'
            elif rec.approved_by.has_group('school_management.group_school_teacher'):
                rec.approver_role = 'teacher'
            else:
                rec.approver_role = False

    @api.depends_context('uid')
    def _compute_user_roles(self):
        is_teacher = self.env.user.has_group('school_management.group_school_teacher')
        is_admin = self.env.user.has_group('school_management.group_school_admin')
        for rec in self:
            rec.is_current_user_approver = is_teacher or is_admin
            rec.is_current_user_student = not (is_teacher or is_admin)

    @api.depends('attendance_ids')
    def _compute_attendance_count(self):
        for rec in self:
            rec.attendance_count = len(rec.attendance_ids)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End Date cannot be earlier than Start Date."))

    @api.constrains('start_time', 'end_time', 'session_type')
    def _check_times(self):
        for rec in self:
            if rec.session_type == 'custom':
                if rec.start_time < 0 or rec.end_time > 24 or rec.end_time <= rec.start_time:
                    raise ValidationError(_("End Time must be greater than Start Time and within 00:00 - 24:00."))

    @api.model_create_multi
    def create(self, vals_list):
        is_student_only = self.env.user.has_group('school_management.group_school_student') and not (
            self.env.user.has_group('school_management.group_school_teacher') or self.env.user.has_group('school_management.group_school_admin')
        )
        my_student = False
        if is_student_only:
            my_student = self.env['school.student'].search([('user_id', '=', self.env.uid)], limit=1)

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('school.permission') or 'PERM-0001'

            # If user is a student, ensure they only create for themselves and cannot set approved state
            if is_student_only:
                if my_student:
                    vals['student_id'] = my_student.id
                vals['state'] = 'draft'
                vals['approved_by'] = False
                vals['approval_date'] = False
                vals['rejection_reason'] = False

        records = super().create(vals_list)
        for rec in records:
            rec.message_post(
                body=_("Permission request submitted for %s (%s to %s).") % (
                    rec.student_id.name, rec.start_date, rec.end_date
                )
            )
        return records

    def write(self, vals):
        is_student_only = self.env.user.has_group('school_management.group_school_student') and not (
            self.env.user.has_group('school_management.group_school_teacher') or self.env.user.has_group('school_management.group_school_admin')
        )
        if is_student_only:
            for rec in self:
                if rec.state != 'draft' and 'state' in vals and vals['state'] not in ('draft', 'cancel'):
                    raise UserError(_("Students can only modify or cancel pending requests."))
                if 'state' in vals and vals['state'] in ('approved', 'rejected'):
                    raise UserError(_("Students cannot approve or reject permission requests."))
                if 'approved_by' in vals or 'approval_date' in vals:
                    vals.pop('approved_by', None)
                    vals.pop('approval_date', None)

        return super().write(vals)

    def _check_approver_rights(self):
        is_teacher = self.env.user.has_group('school_management.group_school_teacher')
        is_admin = self.env.user.has_group('school_management.group_school_admin')
        if not (is_teacher or is_admin):
            raise UserError(_("Only administrators and teachers have permission to approve or reject requests."))

    def action_approve(self):
        self._check_approver_rights()
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only pending requests can be approved. Current state: %s") % rec.state)

            role = 'admin' if self.env.user.has_group('school_management.group_school_admin') else 'teacher'
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now(),
                'rejection_reason': False,
            })

            if rec.auto_update_attendance and rec.student_id:
                rec._sync_excused_attendance()

            role_label = _("Administrator") if role == 'admin' else _("Teacher")
            rec.message_post(
                body=_("<b>Approved</b> by %s (%s).") % (self.env.user.name, role_label)
            )

    def action_reject(self, reason=None):
        self._check_approver_rights()
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only pending requests can be marked as not approved. Current state: %s") % rec.state)

            role = 'admin' if self.env.user.has_group('school_management.group_school_admin') else 'teacher'
            vals = {
                'state': 'rejected',
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            }
            if reason:
                vals['rejection_reason'] = reason

            rec.write(vals)

            role_label = _("Administrator") if role == 'admin' else _("Teacher")
            body_msg = _("<b>Not Approved (Rejected)</b> by %s (%s).") % (self.env.user.name, role_label)
            if rec.rejection_reason:
                body_msg += f"<br/><b>Reason:</b> {rec.rejection_reason}"
            rec.message_post(body=body_msg)

    def action_open_reject_wizard(self):
        self.ensure_one()
        self._check_approver_rights()
        return {
            'name': _("Not Approve Permission Request"),
            'type': 'ir.actions.act_window',
            'res_model': 'school.permission.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_permission_id': self.id,
                'default_rejection_reason': self.rejection_reason or '',
            },
        }

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'approved'):
                raise UserError(_("Cannot cancel a request with status: %s") % rec.state)
            is_student_only = self.env.user.has_group('school_management.group_school_student') and not (
                self.env.user.has_group('school_management.group_school_teacher') or self.env.user.has_group('school_management.group_school_admin')
            )
            if is_student_only and rec.state != 'draft':
                raise UserError(_("Students can only cancel pending requests."))

            rec.write({'state': 'cancel'})
            rec.message_post(body=_("Permission request cancelled by %s.") % self.env.user.name)

    def action_reset_draft(self):
        self._check_approver_rights()
        for rec in self:
            rec.write({
                'state': 'draft',
                'approved_by': False,
                'approval_date': False,
                'rejection_reason': False,
            })
            rec.message_post(body=_("Permission request reset to Pending Approval by %s.") % self.env.user.name)

    def _sync_excused_attendance(self):
        self.ensure_one()
        Attendance = self.env['school.attendance'].sudo()
        cur_date = self.start_date
        delta = timedelta(days=1)
        type_dict = dict(self._fields['permission_type'].selection)
        type_name = type_dict.get(self.permission_type, self.permission_type)

        while cur_date <= self.end_date:
            existing = Attendance.search([
                ('student_id', '=', self.student_id.id),
                ('date', '=', cur_date),
            ], limit=1)

            excuse_note = _("Excused - Approved Permission %s (%s): %s") % (
                self.name, type_name, self.reason or ''
            )

            if existing:
                existing.write({
                    'status': 'excused',
                    'permission_id': self.id,
                    'notes': ((existing.notes or '') + ' | ' + excuse_note).strip(' | '),
                })
            else:
                Attendance.create({
                    'student_id': self.student_id.id,
                    'date': cur_date,
                    'status': 'excused',
                    'permission_id': self.id,
                    'notes': excuse_note,
                })
            cur_date += delta

    def action_view_attendance(self):
        self.ensure_one()
        return {
            'name': _("Excused Attendance Records - %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.attendance',
            'view_mode': 'list,form',
            'domain': [('permission_id', '=', self.id)],
            'context': {'default_student_id': self.student_id.id},
        }
