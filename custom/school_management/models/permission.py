from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class SchoolPermission(models.Model):
    _name = 'school.permission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Permission & Leave Request'
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
    applicant_name = fields.Char(
        string='Applicant',
        compute='_compute_display_name',
        store=True,
    )

    @api.model
    def _default_applicant_type(self):
        if self.env.context.get('default_applicant_type'):
            return self.env.context.get('default_applicant_type')
        user = self.env.user
        if user.has_group('school_management.group_school_teacher') and not user.has_group('school_management.group_school_admin'):
            return 'teacher'
        return 'student'

    applicant_type = fields.Selection([
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ], string='Applicant Type', required=True, default=_default_applicant_type, tracking=True)

    @api.model
    def _default_student_id(self):
        if self.env.context.get('default_student_id'):
            return self.env.context.get('default_student_id')
        student = self.env['school.student'].search([('user_id', '=', self.env.uid)], limit=1)
        if student:
            return student.id
        return False

    student_id = fields.Many2one(
        'school.student',
        string='Student',
        tracking=True,
        default=_default_student_id,
        ondelete='cascade',
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
        string='Class',
        compute='_compute_class_id',
        store=True,
        readonly=False,
        tracking=True,
    )
    class_teacher_id = fields.Many2one(
        'school.teacher',
        related='class_id.teacher_id',
        string='Class Teacher',
        store=True,
        readonly=True,
    )

    timetable_id = fields.Many2one(
        'school.timetable',
        string='Class Session / Timetable',
        ondelete='set null',
        tracking=True,
        help='Specific timetable session the teacher is requesting absence from.',
    )

    @api.depends('student_id.class_id')
    def _compute_class_id(self):
        for rec in self:
            if rec.applicant_type == 'student' and rec.student_id and rec.student_id.class_id:
                rec.class_id = rec.student_id.class_id
            elif not rec.class_id:
                rec.class_id = False

    @api.model
    def _default_teacher_id(self):
        if self.env.context.get('default_teacher_id'):
            return self.env.context.get('default_teacher_id')
        teacher = self.env['school.teacher'].search([('user_id', '=', self.env.uid)], limit=1)
        if teacher:
            return teacher.id
        return False

    teacher_id = fields.Many2one(
        'school.teacher',
        string='Teacher',
        tracking=True,
        default=_default_teacher_id,
        ondelete='cascade',
    )
    teacher_employee_id = fields.Char(
        related='teacher_id.employee_id',
        string='Employee ID',
        readonly=True,
    )
    teacher_code = fields.Char(
        related='teacher_id.employee_id',
        string='Teacher Code / ID',
        readonly=True,
    )
    teacher_phone = fields.Char(
        related='teacher_id.phone',
        string='Teacher Phone',
        readonly=True,
    )
    teacher_email = fields.Char(
        related='teacher_id.email',
        string='Teacher Email',
        readonly=True,
    )
    teacher_subject_ids = fields.Many2many(
        related='teacher_id.subject_ids',
        string='Teaching Subjects',
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

    def _default_end_date(self):
        return fields.Date.context_today(self) + timedelta(days=1)

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=_default_end_date,
        tracking=True,
    )
    start_time = fields.Float(string='Start Time', default=8.0)
    end_time = fields.Float(string='End Time', default=12.0)
    custom_start_time = fields.Float(related='start_time', readonly=False)
    custom_end_time = fields.Float(related='end_time', readonly=False)

    duration_days = fields.Float(
        string='Duration (Days)',
        compute='_compute_duration_days',
        store=True,
        help='Duration of the requested permission in days (calculated as difference between End Date and Start Date).',
    )

    @api.onchange('timetable_id')
    def _onchange_timetable_id(self):
        if self.timetable_id:
            slot = self.timetable_id
            if slot.class_id:
                self.class_id = slot.class_id
            if slot.teacher_id:
                self.teacher_id = slot.teacher_id
            session_date = None
            if slot.start_datetime:
                local_dt = slot._utc_to_local(slot.start_datetime) if hasattr(slot, '_utc_to_local') else slot.start_datetime
                session_date = local_dt.date() if local_dt else None
            if not session_date:
                today = fields.Date.context_today(self)
                mon = today - timedelta(days=today.weekday())
                day_offset = int(slot.day_of_week) if slot.day_of_week else 0
                session_date = mon + timedelta(days=day_offset)
            self.start_date = session_date
            self.end_date = session_date
            self.session_type = 'custom'
            self.start_time = slot.start_time
            self.end_time = slot.end_time

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and (not self.end_date or self.end_date < self.start_date):
            self.end_date = self.start_date

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
        help='Automatically record or update attendance as Excused for the approved dates (Students only).',
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

    # Timetable integration for teachers on leave
    affected_timetable_ids = fields.Many2many(
        'school.timetable',
        string='Affected Teaching Sessions',
        compute='_compute_affected_timetables',
        help='Teaching sessions scheduled during this permission period.',
    )
    affected_timetable_count = fields.Integer(
        string='Affected Sessions Count',
        compute='_compute_affected_timetables',
    )

    can_approve = fields.Boolean(
        string='Can Current User Approve',
        compute='_compute_can_approve',
    )

    @api.depends_context('uid')
    @api.depends('applicant_type', 'teacher_id.user_id', 'student_id.user_id', 'state')
    def _compute_can_approve(self):
        is_admin = self.env.user.has_group('school_management.group_school_admin')
        is_teacher = self.env.user.has_group('school_management.group_school_teacher')
        for rec in self:
            if rec.state != 'draft':
                rec.can_approve = False
                continue
            if rec.applicant_type == 'teacher':
                # Only administrators can approve teacher requests, and cannot approve their own
                rec.can_approve = is_admin and (rec.teacher_id.user_id.id != self.env.uid)
            else:
                # Student requests: administrators or teachers can approve, and cannot approve their own
                rec.can_approve = (is_admin or is_teacher) and (rec.student_id.user_id.id != self.env.uid)

    @api.depends('applicant_type', 'student_id.name', 'teacher_id.name', 'permission_type', 'name')
    def _compute_display_name(self):
        type_dict = dict(self._fields['permission_type'].selection)
        for rec in self:
            type_label = type_dict.get(rec.permission_type, _('Permission'))
            ref_part = f"[{rec.name}] " if rec.name and rec.name != 'New' else ""
            if rec.applicant_type == 'teacher':
                pname = rec.teacher_id.name if rec.teacher_id else _('Teacher')
                rec.applicant_name = pname
                rec.display_name = f"{ref_part}{pname} (Teacher) - {type_label}"
            else:
                pname = rec.student_id.name if rec.student_id else _('Student')
                rec.applicant_name = pname
                rec.display_name = f"{ref_part}{pname} - {type_label}"

    @api.depends('applicant_type', 'teacher_id', 'timetable_id', 'start_date', 'end_date')
    def _compute_affected_timetables(self):
        for rec in self:
            if rec.applicant_type == 'teacher' and rec.teacher_id and rec.start_date and rec.end_date:
                cur = rec.start_date
                stop_date = (rec.end_date - timedelta(days=1)) if rec.end_date > rec.start_date else rec.end_date
                days_in_range = set()
                while cur <= stop_date:
                    days_in_range.add(str(cur.weekday()))
                    cur += timedelta(days=1)
                timetables = self.env['school.timetable'].search([
                    ('teacher_id', '=', rec.teacher_id.id),
                    ('day_of_week', 'in', list(days_in_range)),
                ])
                if rec.timetable_id and rec.timetable_id not in timetables:
                    timetables |= rec.timetable_id
                rec.affected_timetable_ids = [(6, 0, timetables.ids)]
                rec.affected_timetable_count = len(timetables)
            elif rec.timetable_id:
                rec.affected_timetable_ids = [(6, 0, rec.timetable_id.ids)]
                rec.affected_timetable_count = 1
            else:
                rec.affected_timetable_ids = [(6, 0, [])]
                rec.affected_timetable_count = 0

    @api.depends('start_date', 'end_date', 'session_type', 'start_time', 'end_time')
    def _compute_duration_days(self):
        for rec in self:
            if not rec.start_date or not rec.end_date:
                rec.duration_days = 0.0
                continue
            if rec.end_date < rec.start_date:
                rec.duration_days = 0.0
                continue

            day_diff = (rec.end_date - rec.start_date).days
            if day_diff == 0:
                if rec.session_type in ('morning', 'afternoon'):
                    rec.duration_days = 0.5
                elif rec.session_type == 'custom':
                    hours = max(0.0, rec.end_time - rec.start_time)
                    rec.duration_days = max(0.1, round(hours / 8.0, 2))
                else:
                    rec.duration_days = 1.0
            else:
                if rec.session_type in ('morning', 'afternoon'):
                    rec.duration_days = round(day_diff * 0.5, 2)
                elif rec.session_type == 'custom':
                    hours = max(0.0, rec.end_time - rec.start_time)
                    rec.duration_days = max(0.1, round(day_diff * (hours / 8.0), 2))
                else:
                    rec.duration_days = float(day_diff)

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

    @api.depends('attendance_ids')
    def _compute_attendance_count(self):
        for rec in self:
            rec.attendance_count = len(rec.attendance_ids)

    @api.constrains('applicant_type', 'student_id', 'teacher_id')
    def _check_applicants(self):
        for rec in self:
            if rec.applicant_type == 'student' and not rec.student_id:
                raise ValidationError(_("Please specify a student for the permission request."))
            if rec.applicant_type == 'teacher' and not rec.teacher_id:
                raise ValidationError(_("Please specify a teacher for the permission request."))

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
        is_admin = self.env.user.has_group('school_management.group_school_admin')
        is_teacher = self.env.user.has_group('school_management.group_school_teacher')
        is_student = self.env.user.has_group('school_management.group_school_student')

        my_student = self.env['school.student'].search([('user_id', '=', self.env.uid)], limit=1)
        my_teacher = self.env['school.teacher'].search([('user_id', '=', self.env.uid)], limit=1)

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('school.permission') or 'New'

            # If user is a student only, enforce own student_id and draft state
            if is_student and not (is_teacher or is_admin):
                vals['applicant_type'] = 'student'
                if my_student:
                    vals['student_id'] = my_student.id
                vals['state'] = 'draft'
                vals['approved_by'] = False
                vals['approval_date'] = False
                vals['rejection_reason'] = False

            # If user is a teacher only creating a teacher request, enforce own teacher_id and draft state
            if is_teacher and not is_admin:
                if vals.get('applicant_type') == 'teacher':
                    if my_teacher:
                        vals['teacher_id'] = my_teacher.id
                    vals['state'] = 'draft'
                    vals['approved_by'] = False
                    vals['approval_date'] = False
                    vals['rejection_reason'] = False

        records = super().create(vals_list)
        for rec in records:
            name_label = rec.applicant_name or rec.name
            role_label = _("Teacher") if rec.applicant_type == 'teacher' else _("Student")
            rec.message_post(
                body=_("Permission request submitted for %s (%s) from %s to %s.") % (
                    name_label, role_label, rec.start_date, rec.end_date
                )
            )
        return records

    def write(self, vals):
        is_admin = self.env.user.has_group('school_management.group_school_admin')
        is_teacher = self.env.user.has_group('school_management.group_school_teacher')
        is_student_only = self.env.user.has_group('school_management.group_school_student') and not (is_teacher or is_admin)
        is_teacher_only = is_teacher and not is_admin

        for rec in self:
            if is_student_only:
                if rec.state != 'draft' and 'state' in vals and vals['state'] not in ('draft', 'cancel'):
                    raise UserError(_("Students can only modify or cancel pending requests."))
                if 'state' in vals and vals['state'] in ('approved', 'rejected'):
                    raise UserError(_("Students cannot approve or reject permission requests."))
                if 'approved_by' in vals or 'approval_date' in vals:
                    vals.pop('approved_by', None)
                    vals.pop('approval_date', None)

            if is_teacher_only and rec.applicant_type == 'teacher':
                if 'state' in vals and vals['state'] in ('approved', 'rejected'):
                    raise UserError(_("Teacher permission requests must be approved or rejected by an Administrator."))
                if rec.state != 'draft' and 'state' in vals and vals['state'] not in ('draft', 'cancel'):
                    raise UserError(_("You can only modify or cancel pending permission requests."))

        return super().write(vals)

    def _check_approver_rights(self):
        is_teacher = self.env.user.has_group('school_management.group_school_teacher')
        is_admin = self.env.user.has_group('school_management.group_school_admin')
        for rec in self:
            if rec.applicant_type == 'teacher':
                if not is_admin:
                    raise UserError(_("Teacher permission requests must be reviewed and approved by an Administrator."))
                if rec.teacher_id.user_id.id == self.env.uid:
                    raise UserError(_("You cannot approve or reject your own permission request."))
            else:
                if not (is_teacher or is_admin):
                    raise UserError(_("Only administrators and teachers have permission to approve or reject requests."))
                if rec.student_id.user_id.id == self.env.uid:
                    raise UserError(_("You cannot approve or reject your own permission request."))

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

            if rec.applicant_type == 'student' and rec.auto_update_attendance and rec.student_id:
                rec._sync_excused_attendance()

            role_label = _("Administrator") if role == 'admin' else _("Teacher")
            extra_info = ""
            if rec.applicant_type == 'teacher' and rec.affected_timetable_count > 0:
                extra_info = _(" Note: %d scheduled teaching session(s) during this leave period.") % rec.affected_timetable_count

            rec.message_post(
                body=_("Approved by %s (%s).%s") % (self.env.user.name, role_label, extra_info)
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
            body_msg = _("Not Approved (Rejected) by %s (%s).") % (self.env.user.name, role_label)
            if rec.rejection_reason:
                body_msg += _(" Reason: %s") % rec.rejection_reason
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
            is_teacher_only = self.env.user.has_group('school_management.group_school_teacher') and not self.env.user.has_group('school_management.group_school_admin')

            if is_student_only and rec.state != 'draft':
                raise UserError(_("Students can only cancel pending requests."))
            if is_teacher_only and rec.applicant_type == 'teacher' and rec.state != 'draft':
                raise UserError(_("Teachers can only cancel pending requests."))

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
        stop_date = (self.end_date - timedelta(days=1)) if self.end_date > self.start_date else self.end_date
        delta = timedelta(days=1)
        type_dict = dict(self._fields['permission_type'].selection)
        type_name = type_dict.get(self.permission_type, self.permission_type)

        while cur_date <= stop_date:
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
            'context': {'default_permission_id': self.id, 'default_status': 'excused'},
        }

    def action_view_excused_attendance(self):
        return self.action_view_attendance()

    def action_view_affected_timetables(self):
        self.ensure_one()
        return {
            'name': _("Affected Teaching Sessions - %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'list,form,calendar',
            'domain': [('id', 'in', self.affected_timetable_ids.ids)],
        }
