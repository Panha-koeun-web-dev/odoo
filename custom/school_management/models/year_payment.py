from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class SchoolStudentYearPayment(models.Model):
    _name = 'school.student.year.payment'
    _description = 'Student Year Payment'
    _order = 'year desc, student_id'
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    class_id = fields.Many2one('school.class', string='Class', compute='_compute_class_id', store=True, readonly=False)
    fee_ids = fields.Many2many('school.fee', compute='_compute_fee_ids', string='Related Fees')
    year = fields.Char(string='Academic Year', required=True, help="Format: 2024-2025")
    year_start = fields.Date(string='Year Start', required=True)
    year_end = fields.Date(string='Year End', required=True)

    # Currency for monetary fields
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Installment 1
    installment_1_amount = fields.Float(string='Installment 1 Amount', required=True, default=0.0)
    installment_1_due_date = fields.Date(string='Installment 1 Due Date')
    installment_1_paid_date = fields.Date(string='Installment 1 Paid Date')
    installment_1_paid_amount = fields.Float(string='Installment 1 Paid Amount', default=0.0)
    installment_1_balance = fields.Float(string='Installment 1 Balance', compute='_compute_installment_1_balance', store=True)
    installment_1_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
    ], string='Installment 1 Status', default='pending', compute='_compute_installment_1_status', store=True)

    # Installment 2
    installment_2_amount = fields.Float(string='Installment 2 Amount', required=True, default=0.0)
    installment_2_due_date = fields.Date(string='Installment 2 Due Date')
    installment_2_paid_date = fields.Date(string='Installment 2 Paid Date')
    installment_2_paid_amount = fields.Float(string='Installment 2 Paid Amount', default=0.0)
    installment_2_balance = fields.Float(string='Installment 2 Balance', compute='_compute_installment_2_balance', store=True)
    installment_2_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
    ], string='Installment 2 Status', default='pending', compute='_compute_installment_2_status', store=True)

    # Specific Deadline Schedule & Tracking
    payment_deadline = fields.Date(
        string='Final Payment Deadline',
        help="Final date by which the student must complete the entire year tuition."
    )
    is_custom_deadline = fields.Boolean(
        string='Custom Deadline Schedule',
        default=False,
        help="If set, this student has a specific deadline schedule that won't be overwritten by class updates."
    )
    deadline_notes = fields.Char(
        string='Deadline / Extension Reason',
        help="Reason or notes regarding specific payment schedule or deadline extension."
    )
    next_deadline = fields.Date(
        string='Next Due Date',
        compute='_compute_deadlines_summary',
        store=True,
        help="Next upcoming deadline for pending payment."
    )
    days_until_deadline = fields.Integer(
        string='Days to Deadline',
        compute='_compute_deadlines_summary',
        store=True,
        help="Days remaining until the next deadline (negative if overdue)."
    )
    deadline_status = fields.Selection([
        ('no_deadline', 'No Deadline Set'),
        ('paid', 'Fully Paid'),
        ('today', 'Due Today'),
        ('upcoming', 'Upcoming'),
        ('overdue', 'Overdue'),
    ], string='Deadline Status', compute='_compute_deadlines_summary', store=True)

    # Total Year Amount
    total_amount = fields.Float(
        string='Total Year Amount',
        compute='_compute_total_amount',
        store=True,
        readonly=True,
        help="Total tuition for this year, following the class payment schedule"
    )
    total_paid = fields.Float(string='Total Paid', compute='_compute_total_paid', store=True)
    total_balance = fields.Float(string='Total Balance', compute='_compute_total_balance', store=True)
    overall_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Fully Paid'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
    ], string='Overall Status', compute='_compute_overall_status', store=True)

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('online', 'Online'),
    ], string='Payment Method')
    receipt_number = fields.Char(string='Receipt Number')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('student_id', 'student_id.class_id')
    def _compute_class_id(self):
        for rec in self:
            if rec.student_id and rec.student_id.class_id:
                rec.class_id = rec.student_id.class_id
            elif not rec.class_id:
                rec.class_id = False

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        student_id = defaults.get('student_id') or self.env.context.get('default_student_id')
        class_id = defaults.get('class_id') or self.env.context.get('default_class_id')
        student = self.env['school.student'].browse(student_id) if student_id else None
        cls = self.env['school.class'].browse(class_id) if class_id else (student.class_id if student else None)

        if cls:
            if 'class_id' in fields_list and not defaults.get('class_id'):
                defaults['class_id'] = cls.id
            if 'year' in fields_list and not defaults.get('year') and cls.payment_year:
                defaults['year'] = cls.payment_year
            if 'year_start' in fields_list and not defaults.get('year_start') and cls.year_start:
                defaults['year_start'] = cls.year_start
            if 'year_end' in fields_list and not defaults.get('year_end') and cls.year_end:
                defaults['year_end'] = cls.year_end
            if 'installment_1_amount' in fields_list and not defaults.get('installment_1_amount'):
                defaults['installment_1_amount'] = cls.installment_1_amount
            if 'installment_2_amount' in fields_list and not defaults.get('installment_2_amount'):
                defaults['installment_2_amount'] = cls.installment_2_amount
            if 'installment_1_due_date' in fields_list and not defaults.get('installment_1_due_date') and cls.installment_1_due_date:
                defaults['installment_1_due_date'] = cls.installment_1_due_date
            if 'installment_2_due_date' in fields_list and not defaults.get('installment_2_due_date') and cls.installment_2_due_date:
                defaults['installment_2_due_date'] = cls.installment_2_due_date
            if 'payment_deadline' in fields_list and not defaults.get('payment_deadline'):
                defaults['payment_deadline'] = getattr(cls, 'payment_deadline', False) or cls.installment_2_due_date
            if 'currency_id' in fields_list and not defaults.get('currency_id') and cls.currency_id:
                defaults['currency_id'] = cls.currency_id.id
        return defaults

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            cls = self.student_id.class_id
            if cls:
                self.class_id = cls.id
                if cls.payment_year:
                    self.year = cls.payment_year
                if cls.year_start:
                    self.year_start = cls.year_start
                if cls.year_end:
                    self.year_end = cls.year_end
                self.installment_1_amount = cls.installment_1_amount
                self.installment_2_amount = cls.installment_2_amount
                if not self.is_custom_deadline:
                    self.installment_1_due_date = cls.installment_1_due_date
                    self.installment_2_due_date = cls.installment_2_due_date
                    self.payment_deadline = getattr(cls, 'payment_deadline', False) or cls.installment_2_due_date
                if cls.currency_id:
                    self.currency_id = cls.currency_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('student_id'):
                student = self.env['school.student'].browse(vals['student_id']) \
                    if isinstance(vals['student_id'], int) else None
                cls = student.class_id if student else None
                if cls:
                    if 'class_id' not in vals:
                        vals['class_id'] = cls.id
                    if 'year' not in vals and cls.payment_year:
                        vals['year'] = cls.payment_year
                    if 'year_start' not in vals and cls.year_start:
                        vals['year_start'] = cls.year_start
                    if 'year_end' not in vals and cls.year_end:
                        vals['year_end'] = cls.year_end
                    if ('installment_1_amount' not in vals or vals.get('installment_1_amount') == 0.0) and cls.installment_1_amount:
                        vals['installment_1_amount'] = cls.installment_1_amount
                    if ('installment_2_amount' not in vals or vals.get('installment_2_amount') == 0.0) and cls.installment_2_amount:
                        vals['installment_2_amount'] = cls.installment_2_amount
                    if 'installment_1_due_date' not in vals and cls.installment_1_due_date:
                        vals['installment_1_due_date'] = cls.installment_1_due_date
                    if 'installment_2_due_date' not in vals and cls.installment_2_due_date:
                        vals['installment_2_due_date'] = cls.installment_2_due_date
                    if 'payment_deadline' not in vals and (getattr(cls, 'payment_deadline', False) or cls.installment_2_due_date):
                        vals['payment_deadline'] = getattr(cls, 'payment_deadline', False) or cls.installment_2_due_date
                    if 'currency_id' not in vals and cls.currency_id:
                        vals['currency_id'] = cls.currency_id.id
        return super().create(vals_list)

    def write(self, vals):
        deadline_fields = {'installment_1_due_date', 'installment_2_due_date', 'payment_deadline'}
        if any(f in vals for f in deadline_fields) and 'is_custom_deadline' not in vals:
            vals['is_custom_deadline'] = True
        return super().write(vals)

    def action_sync_from_class(self):
        """Re-sync payment schedule to follow the assigned class."""
        self.ensure_one()
        cls = self.class_id or self.student_id.class_id
        if not cls:
            raise UserError(_('No class is associated with this student.'))

        if not cls.total_payment and not (cls.installment_1_amount or cls.installment_2_amount):
            raise UserError(_("The class '%s' does not have payment amounts configured.") % cls.name)

        vals = {
            'class_id': cls.id,
            'year': cls.payment_year or self.year,
            'year_start': cls.year_start or self.year_start,
            'year_end': cls.year_end or self.year_end,
            'installment_1_amount': cls.installment_1_amount or 0.0,
            'installment_2_amount': cls.installment_2_amount or 0.0,
            'currency_id': cls.currency_id.id if cls.currency_id else self.currency_id.id,
        }
        if not self.is_custom_deadline:
            vals['installment_1_due_date'] = cls.installment_1_due_date
            vals['installment_2_due_date'] = cls.installment_2_due_date
            vals['payment_deadline'] = getattr(cls, 'payment_deadline', False) or cls.installment_2_due_date

        self.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment Loaded'),
                'message': _("Successfully updated payment schedule to follow class '%s'.") % cls.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_to_class_deadline(self):
        """Reset custom deadline schedule to follow the class default schedule."""
        for rec in self:
            cls = rec.class_id or rec.student_id.class_id
            if cls:
                rec.write({
                    'is_custom_deadline': False,
                    'installment_1_due_date': cls.installment_1_due_date,
                    'installment_2_due_date': cls.installment_2_due_date,
                    'payment_deadline': getattr(cls, 'payment_deadline', False) or cls.installment_2_due_date,
                    'deadline_notes': False,
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Schedule Reset'),
                'message': _('Deadline schedule has been reset to follow the class default schedule.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_deadline_wizard(self):
        """Open popup wizard to set specific deadline schedule."""
        self.ensure_one()
        return {
            'name': _('Set Deadline Schedule - %s') % self.student_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.year.payment.deadline.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'school.student.year.payment',
                'default_year_payment_ids': [(6, 0, self.ids)],
                'default_installment_1_due_date': self.installment_1_due_date,
                'default_installment_2_due_date': self.installment_2_due_date,
                'default_payment_deadline': self.payment_deadline or self.installment_2_due_date,
                'default_is_custom_deadline': True,
                'default_deadline_notes': self.deadline_notes,
            },
        }

    @api.depends('student_id', 'student_id.fee_ids')
    def _compute_fee_ids(self):
        for rec in self:
            rec.fee_ids = rec.student_id.fee_ids if rec.student_id else self.env['school.fee']

    @api.depends('installment_1_amount', 'installment_1_paid_amount')
    def _compute_installment_1_balance(self):
        for rec in self:
            rec.installment_1_balance = rec.installment_1_amount - rec.installment_1_paid_amount

    @api.depends('installment_1_amount', 'installment_1_paid_amount', 'installment_1_due_date')
    def _compute_installment_1_status(self):
        today = fields.Date.today()
        for rec in self:
            if rec.installment_1_paid_amount >= rec.installment_1_amount and rec.installment_1_amount > 0:
                rec.installment_1_status = 'paid'
            elif rec.installment_1_paid_amount > 0:
                rec.installment_1_status = 'partial'
            elif rec.installment_1_due_date and rec.installment_1_due_date < today:
                rec.installment_1_status = 'overdue'
            else:
                rec.installment_1_status = 'pending'

    @api.depends('installment_2_amount', 'installment_2_paid_amount')
    def _compute_installment_2_balance(self):
        for rec in self:
            rec.installment_2_balance = rec.installment_2_amount - rec.installment_2_paid_amount

    @api.depends('installment_2_amount', 'installment_2_paid_amount', 'installment_2_due_date')
    def _compute_installment_2_status(self):
        today = fields.Date.today()
        for rec in self:
            if rec.installment_2_paid_amount >= rec.installment_2_amount and rec.installment_2_amount > 0:
                rec.installment_2_status = 'paid'
            elif rec.installment_2_paid_amount > 0:
                rec.installment_2_status = 'partial'
            elif rec.installment_2_due_date and rec.installment_2_due_date < today:
                rec.installment_2_status = 'overdue'
            else:
                rec.installment_2_status = 'pending'

    @api.depends(
        'total_balance', 'total_amount',
        'installment_1_balance', 'installment_1_due_date',
        'installment_2_balance', 'installment_2_due_date',
        'payment_deadline'
    )
    def _compute_deadlines_summary(self):
        today = fields.Date.today()
        for rec in self:
            if rec.total_amount > 0 and rec.total_balance <= 0:
                rec.deadline_status = 'paid'
                rec.next_deadline = False
                rec.days_until_deadline = 0
                continue

            target = False
            if rec.installment_1_balance > 0 and rec.installment_1_due_date:
                target = rec.installment_1_due_date
            elif rec.installment_2_balance > 0 and rec.installment_2_due_date:
                target = rec.installment_2_due_date
            elif rec.payment_deadline:
                target = rec.payment_deadline
            elif rec.installment_2_due_date:
                target = rec.installment_2_due_date
            elif rec.installment_1_due_date:
                target = rec.installment_1_due_date

            rec.next_deadline = target
            if not target:
                rec.deadline_status = 'no_deadline'
                rec.days_until_deadline = 0
            else:
                delta = (target - today).days
                rec.days_until_deadline = delta
                if delta < 0:
                    rec.deadline_status = 'overdue'
                elif delta == 0:
                    rec.deadline_status = 'today'
                else:
                    rec.deadline_status = 'upcoming'

    @api.depends('installment_1_amount', 'installment_2_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = round((rec.installment_1_amount or 0.0) + (rec.installment_2_amount or 0.0), 2)

    @api.depends('installment_1_paid_amount', 'installment_2_paid_amount')
    def _compute_total_paid(self):
        for rec in self:
            rec.total_paid = rec.installment_1_paid_amount + rec.installment_2_paid_amount

    @api.depends('total_amount', 'total_paid')
    def _compute_total_balance(self):
        for rec in self:
            rec.total_balance = rec.total_amount - rec.total_paid

    @api.depends(
        'installment_1_status', 'installment_2_status',
        'installment_1_amount', 'installment_2_amount',
        'installment_1_balance', 'installment_2_balance',
        'installment_1_due_date', 'installment_2_due_date',
        'payment_deadline', 'total_balance'
    )
    def _compute_overall_status(self):
        today = fields.Date.today()
        for rec in self:
            inst1_paid = rec.installment_1_paid_amount >= rec.installment_1_amount if rec.installment_1_amount > 0 else True
            inst2_paid = rec.installment_2_paid_amount >= rec.installment_2_amount if rec.installment_2_amount > 0 else True

            if inst1_paid and inst2_paid and rec.total_balance <= 0:
                rec.overall_status = 'paid'
            elif rec.installment_1_paid_amount > 0 or rec.installment_2_paid_amount > 0 or (rec.total_paid > 0 and rec.total_balance > 0):
                rec.overall_status = 'partial'
            elif (rec.installment_1_due_date and rec.installment_1_due_date < today and rec.installment_1_amount > 0 and rec.installment_1_balance > 0) or \
                 (rec.installment_2_due_date and rec.installment_2_due_date < today and rec.installment_2_amount > 0 and rec.installment_2_balance > 0) or \
                 (rec.payment_deadline and rec.payment_deadline < today and rec.total_balance > 0):
                rec.overall_status = 'overdue'
            else:
                rec.overall_status = 'pending'

    def action_pay_installment_1(self):
        self.ensure_one()
        return {
            'name': _('Pay Installment 1'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.year.payment.pay.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_year_payment_id': self.id,
                'default_installment': '1',
                'default_amount': self.installment_1_balance,
            },
        }

    def action_pay_installment_2(self):
        self.ensure_one()
        return {
            'name': _('Pay Installment 2'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.year.payment.pay.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_year_payment_id': self.id,
                'default_installment': '2',
                'default_amount': self.installment_2_balance,
            },
        }

    def action_view_fees(self):
        self.ensure_one()
        return {
            'name': _('Related Fees'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.fee',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.student_id.id)],
            'context': {'default_student_id': self.student_id.id},
        }


class SchoolStudentYearPaymentPayWizard(models.TransientModel):
    _name = 'school.student.year.payment.pay.wizard'
    _description = 'Pay Installment Wizard'

    year_payment_id = fields.Many2one('school.student.year.payment', string='Year Payment', required=True)
    installment = fields.Selection([
        ('1', 'Installment 1'),
        ('2', 'Installment 2'),
    ], string='Installment', required=True)
    amount = fields.Float(string='Amount to Pay', required=True)
    paid_date = fields.Date(string='Payment Date', default=fields.Date.today, required=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('online', 'Online'),
    ], string='Payment Method', required=True)
    receipt_number = fields.Char(string='Receipt Number')
    notes = fields.Text(string='Notes')

    def action_confirm(self):
        self.ensure_one()
        year_payment = self.year_payment_id

        if self.installment == '1':
            year_payment.write({
                'installment_1_paid_amount': year_payment.installment_1_paid_amount + self.amount,
                'installment_1_paid_date': self.paid_date,
                'payment_method': self.payment_method,
                'receipt_number': self.receipt_number,
                'notes': self.notes,
            })
        else:
            year_payment.write({
                'installment_2_paid_amount': year_payment.installment_2_paid_amount + self.amount,
                'installment_2_paid_date': self.paid_date,
                'payment_method': self.payment_method,
                'receipt_number': self.receipt_number,
                'notes': self.notes,
            })

        return {'type': 'ir.actions.act_window_close'}


class SchoolStudentYearPaymentDeadlineWizard(models.TransientModel):
    _name = 'school.student.year.payment.deadline.wizard'
    _description = 'Set Student Payment Deadline Schedule Wizard'

    year_payment_ids = fields.Many2many(
        'school.student.year.payment',
        'school_year_pmt_deadline_wiz_rel',
        'wizard_id',
        'payment_id',
        string='Year Payments',
        required=True
    )
    student_count = fields.Integer(string='Students Count', compute='_compute_student_info')
    single_student_name = fields.Char(string='Student', compute='_compute_student_info')
    single_class_name = fields.Char(string='Class', compute='_compute_student_info')
    single_year = fields.Char(string='Academic Year', compute='_compute_student_info')
    single_balance = fields.Float(string='Remaining Balance', compute='_compute_student_info')
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_student_info')

    installment_1_due_date = fields.Date(string='Installment 1 Deadline')
    installment_2_due_date = fields.Date(string='Installment 2 Deadline')
    payment_deadline = fields.Date(
        string='Final Payment Deadline',
        help="The final date by which the student must settle their total year tuition."
    )
    is_custom_deadline = fields.Boolean(
        string='Mark as Custom Student Schedule',
        default=True,
        help="If enabled, class-wide updates will not overwrite these deadlines for this student."
    )
    deadline_notes = fields.Char(
        string='Schedule Reason / Notes',
        help="Reason or notes regarding specific payment schedule or deadline extension."
    )

    @api.depends('year_payment_ids')
    def _compute_student_info(self):
        for rec in self:
            rec.student_count = len(rec.year_payment_ids)
            if len(rec.year_payment_ids) == 1:
                payment = rec.year_payment_ids[0]
                rec.single_student_name = payment.student_id.name
                rec.single_class_name = payment.class_id.name if payment.class_id else False
                rec.single_year = payment.year
                rec.single_balance = payment.total_balance
                rec.currency_id = payment.currency_id
            else:
                rec.single_student_name = False
                rec.single_class_name = False
                rec.single_year = False
                rec.single_balance = sum(rec.year_payment_ids.mapped('total_balance'))
                rec.currency_id = rec.env.company.currency_id

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if active_model == 'school.student.year.payment' and active_ids:
            defaults['year_payment_ids'] = [(6, 0, active_ids)]
            if len(active_ids) == 1:
                payment = self.env['school.student.year.payment'].browse(active_ids[0])
                defaults['installment_1_due_date'] = payment.installment_1_due_date
                defaults['installment_2_due_date'] = payment.installment_2_due_date
                defaults['payment_deadline'] = payment.payment_deadline or payment.installment_2_due_date
                defaults['is_custom_deadline'] = True
                defaults['deadline_notes'] = payment.deadline_notes
        return defaults

    def action_apply_deadlines(self):
        self.ensure_one()
        if not self.year_payment_ids:
            raise UserError(_('No payment records selected.'))

        vals = {
            'is_custom_deadline': self.is_custom_deadline,
        }
        if self.deadline_notes is not False:
            vals['deadline_notes'] = self.deadline_notes
        if self.installment_1_due_date:
            vals['installment_1_due_date'] = self.installment_1_due_date
        if self.installment_2_due_date:
            vals['installment_2_due_date'] = self.installment_2_due_date
        if self.payment_deadline:
            vals['payment_deadline'] = self.payment_deadline

        self.year_payment_ids.write(vals)

        msg = _("Successfully updated deadline schedule for %d student payment record(s).") % len(self.year_payment_ids)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deadline Schedule Updated'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }
