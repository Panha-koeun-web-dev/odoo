from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'School Class'
    _order = 'name'

    name = fields.Char(string='Class Name', required=True)
    code = fields.Char(string='Class Code')
    section = fields.Char(string='Section')
    major_id = fields.Many2one('school.major', string='Major')
    teacher_id = fields.Many2one('school.teacher', string='Class Teacher')
    subject_ids = fields.Many2many('school.subject', string='Subjects')
    student_ids = fields.One2many('school.student', 'class_id', string='Students')
    enrollment_ids = fields.One2many('school.enrollment', 'class_id', string='Enrollments')
    student_count = fields.Integer(string='Student Count', compute='_compute_student_count')
    capacity = fields.Integer(string='Capacity', default=40)
    room = fields.Char(string='Room Number')
    active = fields.Boolean(default=True)
    capacity_progress = fields.Float(string='Capacity %', compute='_compute_capacity_progress')

    # Academic Term Integration (1 Year = 12 Months = 3 Terms, 3 Months per Term)
    current_term_id = fields.Many2one(
        'school.term',
        string='Current Academic Term',
        help="Currently active academic term for this class."
    )
    term_ids = fields.Many2many(
        'school.term',
        'school_term_class_rel',
        'class_id',
        'term_id',
        string='Academic Terms',
        help="All terms in which this class studies."
    )

    # Timetable Integration
    timetable_ids = fields.One2many('school.timetable', 'class_id', string='Timetable')
    timetable_count = fields.Integer(string='Timetable Sessions', compute='_compute_timetable_count')
    holiday_count = fields.Integer(string='Class & School Holidays Count', compute='_compute_timetable_count')

    # Teacher Permission / Leave Integration
    permission_ids = fields.One2many('school.permission', 'class_id', string='Teacher Permissions')
    permission_count = fields.Integer(string='Teacher Leave Requests', compute='_compute_permission_count')

    # Weekly Teaching Assignments & Subject Allocation
    teaching_assignment_ids = fields.One2many('school.teaching.assignment', 'class_id', string='Subject Teaching Staff')
    teaching_assignment_count = fields.Integer(string='Assigned Subjects Count', compute='_compute_teaching_assignment_stats')
    total_weekly_class_hours = fields.Float(string='Total Weekly Class Hours', compute='_compute_teaching_assignment_stats')
    total_weekly_class_sessions = fields.Integer(string='Total Weekly Sessions', compute='_compute_teaching_assignment_stats')

    # Currency and Payment Configuration for the Class
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        default=lambda self: self.env.company.currency_id,
    )
    payment_year = fields.Char(
        string='Academic Year',
        default='2026-2027',
        help="Academic year for this class's payment (e.g. 2024-2025)"
    )
    year_start = fields.Date(string='Academic Year Start')
    year_end = fields.Date(string='Academic Year End')
    total_payment = fields.Monetary(
        string='Total Payment',
        currency_field='currency_id',
        help="Tuition / payment required per student studying in this class"
    )
    installment_1_amount = fields.Monetary(string='Installment 1 Amount', currency_field='currency_id')
    installment_1_due_date = fields.Date(string='Installment 1 Due Date')
    installment_2_amount = fields.Monetary(string='Installment 2 Amount', currency_field='currency_id')
    installment_2_due_date = fields.Date(string='Installment 2 Due Date')
    payment_deadline = fields.Date(
        string='Final Payment Deadline',
        help="Class-wide final deadline for full tuition settlement."
    )

    # Student Year Payments Integration & Analytics for this Class
    year_payment_ids = fields.One2many('school.student.year.payment', 'class_id', string='Student Year Payments')
    year_payment_count = fields.Integer(string='Payment Count', compute='_compute_payment_statistics')
    total_payment_expected = fields.Monetary(string='Total Expected', currency_field='currency_id', compute='_compute_payment_statistics')
    total_payment_collected = fields.Monetary(string='Total Collected', currency_field='currency_id', compute='_compute_payment_statistics')
    total_payment_balance = fields.Monetary(string='Total Balance', currency_field='currency_id', compute='_compute_payment_statistics')
    payment_collection_rate = fields.Float(string='Collection Rate %', compute='_compute_payment_statistics')

    @api.depends_context('company')
    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for rec in self:
            rec.currency_id = currency

    def _compute_capacity_progress(self):
        for rec in self:
            rec.capacity_progress = (rec.student_count / rec.capacity * 100) if rec.capacity else 0

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = self.env['school.student'].search_count([
                ('class_id', '=', rec.id),
                ('study_status', '=', 'studying'),
            ])

    def _compute_timetable_count(self):
        for rec in self:
            rec.timetable_count = len(rec.timetable_ids)
            domain = [
                ('active', '=', True),
                ('is_holiday', '=', True),
                '|',
                ('class_id', '=', rec.id),
                ('class_id', '=', False),
            ]
            rec.holiday_count = self.env['school.timetable'].search_count(domain)

    def _compute_permission_count(self):
        for rec in self:
            rec.permission_count = self.env['school.permission'].search_count([
                ('class_id', '=', rec.id),
                ('applicant_type', '=', 'teacher'),
            ])

    @api.depends(
        'teaching_assignment_ids',
        'teaching_assignment_ids.weekly_hours',
        'teaching_assignment_ids.weekly_sessions',
        'teaching_assignment_ids.active',
    )
    def _compute_teaching_assignment_stats(self):
        for rec in self:
            active_asgs = rec.teaching_assignment_ids.filtered(lambda a: a.active)
            rec.teaching_assignment_count = len(active_asgs)
            rec.total_weekly_class_hours = sum(active_asgs.mapped('weekly_hours'))
            rec.total_weekly_class_sessions = sum(active_asgs.mapped('weekly_sessions'))

    @api.depends('year_payment_ids.total_amount', 'year_payment_ids.total_paid', 'year_payment_ids.total_balance')
    def _compute_payment_statistics(self):
        for rec in self:
            payments = rec.year_payment_ids
            total_expected = sum(payments.mapped('total_amount'))
            total_collected = sum(payments.mapped('total_paid'))
            total_balance = sum(payments.mapped('total_balance'))
            rec.year_payment_count = len(payments)
            rec.total_payment_expected = total_expected
            rec.total_payment_collected = total_collected
            rec.total_payment_balance = total_balance
            rec.payment_collection_rate = round((total_collected / total_expected * 100), 1) if total_expected else 0.0

    @api.onchange('total_payment')
    def _onchange_total_payment(self):
        if self.total_payment is not None:
            current_sum = (self.installment_1_amount or 0.0) + (self.installment_2_amount or 0.0)
            if round(current_sum, 2) != round(self.total_payment, 2):
                inst1 = round(self.total_payment / 2.0, 2)
                self.installment_1_amount = inst1
                self.installment_2_amount = round(self.total_payment - inst1, 2)

    @api.onchange('installment_1_amount', 'installment_2_amount')
    def _onchange_installments(self):
        inst_sum = (self.installment_1_amount or 0.0) + (self.installment_2_amount or 0.0)
        if inst_sum and round(inst_sum, 2) != round(self.total_payment or 0.0, 2):
            self.total_payment = inst_sum

    @api.onchange('year_start')
    def _onchange_year_start(self):
        if self.year_start:
            if not self.year_end:
                self.year_end = self.year_start + timedelta(days=300)
            if not self.installment_1_due_date:
                self.installment_1_due_date = self.year_start + timedelta(days=30)
            if not self.installment_2_due_date and self.year_end:
                self.installment_2_due_date = self.year_start + timedelta(days=150)
            if not self.payment_deadline and self.year_end:
                self.payment_deadline = self.year_end

    def _sync_students_class_payment(self):
        """Synchronize payment for all students enrolled in this class.
        Each student follows the payment configured for this class."""
        for rec in self:
            if not rec.total_payment and not (rec.installment_1_amount or rec.installment_2_amount):
                continue
            academic_year = rec.payment_year or '2024-2025'
            year_payment_model = self.env['school.student.year.payment']
            for student in rec.student_ids:
                payment_rec = year_payment_model.search([
                    ('student_id', '=', student.id),
                    ('year', '=', academic_year),
                ], limit=1)

                vals = {
                    'class_id': rec.id,
                    'year': academic_year,
                    'year_start': rec.year_start or fields.Date.today(),
                    'year_end': rec.year_end or (fields.Date.today() + timedelta(days=300)),
                    'installment_1_amount': rec.installment_1_amount or 0.0,
                    'installment_1_due_date': rec.installment_1_due_date,
                    'installment_2_amount': rec.installment_2_amount or 0.0,
                    'installment_2_due_date': rec.installment_2_due_date,
                    'payment_deadline': rec.payment_deadline or rec.installment_2_due_date,
                    'currency_id': rec.currency_id.id if rec.currency_id else False,
                }

                if not payment_rec:
                    vals['student_id'] = student.id
                    year_payment_model.create(vals)
                else:
                    if payment_rec.is_custom_deadline:
                        vals.pop('installment_1_due_date', None)
                        vals.pop('installment_2_due_date', None)
                        vals.pop('payment_deadline', None)
                    payment_rec.write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.student_ids and (rec.total_payment or rec.installment_1_amount or rec.installment_2_amount):
                rec._sync_students_class_payment()
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {
            'total_payment', 'installment_1_amount', 'installment_2_amount',
            'installment_1_due_date', 'installment_2_due_date', 'payment_deadline',
            'payment_year', 'year_start', 'year_end', 'currency_id'
        }
        if any(f in vals for f in sync_fields) or 'student_ids' in vals:
            for rec in self:
                rec._sync_students_class_payment()
        return res

    def action_generate_year_payments(self):
        """Action button to sync or apply class payment to all students enrolled in this class."""
        self.ensure_one()
        if not self.student_ids:
            raise UserError(_('There are no students assigned to this class.'))
        if not self.total_payment and not (self.installment_1_amount or self.installment_2_amount):
            raise UserError(_('Please configure the Total Payment or Installment amounts for this class first.'))

        self._sync_students_class_payment()

        msg = _("Payment synchronization complete: All %d students in class '%s' now follow this class's payment configuration (Total: %s).") % (
            len(self.student_ids), self.name, self.total_payment
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Class Payment Synced'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_year_payments(self):
        self.ensure_one()
        return {
            'name': _('Year Payments - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.year.payment',
            'view_mode': 'kanban,list,form',
            'domain': [('class_id', '=', self.id)],
            'context': {
                'default_class_id': self.id,
            },
        }

    def action_view_timetable(self):
        self.ensure_one()
        ctx = {
            'default_class_id': self.id,
            'default_room': self.room,
            'default_teacher_id': self.teacher_id.id if self.teacher_id else False,
            'search_default_class_id': self.id,
            'search_default_filter_mon_fri': 1,
        }
        if self.current_term_id:
            ctx['default_term_id'] = self.current_term_id.id
            ctx['search_default_term_id'] = self.current_term_id.id
            if self.current_term_id.date_start:
                ctx['initial_date'] = self.current_term_id.date_start.isoformat()
        domain = [
            '|',
            ('class_id', '=', self.id),
            '&',
            ('is_holiday', '=', True),
            ('class_id', '=', False),
        ]
        return {
            'name': _('Class Timetable & Calendar - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': domain,
            'context': ctx,
        }

    def action_view_master_timetable(self):
        self.ensure_one()
        ctx = {
            'search_default_filter_mon_fri': 1,
            'search_default_filter_active_term': 1,
        }
        if self.current_term_id:
            ctx['search_default_term_id'] = self.current_term_id.id
            if self.current_term_id.date_start:
                ctx['initial_date'] = self.current_term_id.date_start.isoformat()
        return {
            'name': _('Master Timetable & Calendar'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'context': ctx,
        }

    def action_view_holidays(self):
        self.ensure_one()
        return {
            'name': _('Class Holidays & Days Off - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': [
                ('active', '=', True),
                ('is_holiday', '=', True),
                '|',
                ('class_id', '=', self.id),
                ('class_id', '=', False),
            ],
            'context': {
                'default_is_holiday': True,
                'default_class_id': self.id,
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
            'domain': [('class_id', '=', self.id)],
            'context': {'default_class_id': self.id},
        }

    def action_sync_subjects_to_students(self):
        """Propagate class curriculum / teaching assignments to all enrolled studying students."""
        for cls in self:
            students = cls.student_ids.filtered(lambda s: s.active and s.study_status == 'studying')
            if not students:
                raise UserError(_("Class '%s' has no active enrolled students to synchronize.") % cls.name)
            students.action_sync_subjects_from_class()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Curriculum Propagated"),
                'message': _("Weekly subjects synchronized to %d students in class '%s'.") % (
                    len(students), self.name
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_take_attendance(self):
        self.ensure_one()
        wizard = self.env['school.daily.attendance.wizard'].create({
            'class_id': self.id,
            'date': fields.Date.today(),
        })
        wizard._populate_students()
        return {
            'name': _('Take Daily Attendance - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.daily.attendance.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    def action_export_xlsx(self):
        ids = self.ids or self.env.context.get('active_ids') or []
        ids_str = ','.join(str(x) for x in ids) if ids else ''
        return {
            'type': 'ir.actions.act_url',
            'url': f'/school_management/export_report_xlsx?report_type=class&ids={ids_str}',
            'target': 'self',
        }

    def action_open_assign_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Curriculum & Teachers to %s') % self.name,
            'res_model': 'school.assign.subject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mode': 'teacher_assign',
                'default_class_id': self.id,
                'default_teacher_id': self.teacher_id.id if self.teacher_id else False,
            }
        }

    def action_open_term_schedule_wizard(self):
        """Open schedule planner wizard for this class and current/selected term."""
        self.ensure_one()
        active_term = self.current_term_id or self.env['school.term'].search([('state', '=', 'active')], limit=1)
        return {
            'name': _('Create / Manage Term Schedule - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.term.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_class_id': self.id,
                'default_term_id': active_term.id if active_term else False,
                'default_source_term_id': (active_term.previous_term_id.id if active_term and active_term.previous_term_id else False),
            }
        }

    def action_request_teacher_permission(self):
        """Allow a teacher or admin to submit a leave / absence permission request for this class."""
        self.ensure_one()
        current_teacher = self.env['school.teacher'].search([('user_id', '=', self.env.uid)], limit=1)
        target_teacher_id = current_teacher.id if current_teacher else (self.teacher_id.id if self.teacher_id else False)
        return {
            'name': _('Request Leave from Class - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.permission',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_applicant_type': 'teacher',
                'default_teacher_id': target_teacher_id,
                'default_class_id': self.id,
                'default_permission_type': 'leave',
                'default_start_date': fields.Date.context_today(self),
                'default_end_date': fields.Date.context_today(self),
            },
        }

    def action_view_teacher_permissions(self):
        """View all teacher leave requests for this class."""
        self.ensure_one()
        return {
            'name': _('Teacher Leave Requests - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.permission',
            'view_mode': 'list,form,calendar',
            'domain': [('class_id', '=', self.id), ('applicant_type', '=', 'teacher')],
            'context': {
                'default_applicant_type': 'teacher',
                'default_class_id': self.id,
            },
        }
