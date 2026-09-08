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

    # Total
    total_amount = fields.Float(string='Total Year Amount', compute='_compute_total_amount', store=True)
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
            if 'currency_id' in fields_list and not defaults.get('currency_id') and cls.currency_id:
                defaults['currency_id'] = cls.currency_id.id
        return defaults

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            cls = self.student_id.class_id
            if cls:
                self.class_id = cls.id
                if cls.payment_year and not self.year:
                    self.year = cls.payment_year
                if cls.year_start and not self.year_start:
                    self.year_start = cls.year_start
                if cls.year_end and not self.year_end:
                    self.year_end = cls.year_end
                if cls.total_payment or (cls.installment_1_amount or cls.installment_2_amount):
                    if not self.installment_1_amount:
                        self.installment_1_amount = cls.installment_1_amount
                    if not self.installment_2_amount:
                        self.installment_2_amount = cls.installment_2_amount
                    if not self.installment_1_due_date:
                        self.installment_1_due_date = cls.installment_1_due_date
                    if not self.installment_2_due_date:
                        self.installment_2_due_date = cls.installment_2_due_date
                    if cls.currency_id:
                        self.currency_id = cls.currency_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('student_id'):
                student = self.env['school.student'].browse(vals['student_id'])
                cls = student.class_id
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
                    if 'currency_id' not in vals and cls.currency_id:
                        vals['currency_id'] = cls.currency_id.id
        return super().create(vals_list)

    def action_sync_from_class(self):
        self.ensure_one()
        cls = self.class_id or self.student_id.class_id
        if not cls:
            raise UserError(_('No class is associated with this student.'))
        if not cls.total_payment and not (cls.installment_1_amount or cls.installment_2_amount):
            raise UserError(_("The class '%s' does not have payment amounts configured.") % cls.name)

        if self.installment_1_paid_amount > 0 or self.installment_2_paid_amount > 0:
            raise UserError(_('Cannot reset payment amounts from class because payments have already been recorded.'))

        self.write({
            'class_id': cls.id,
            'year': cls.payment_year or self.year,
            'year_start': cls.year_start or self.year_start,
            'year_end': cls.year_end or self.year_end,
            'installment_1_amount': cls.installment_1_amount,
            'installment_1_due_date': cls.installment_1_due_date,
            'installment_2_amount': cls.installment_2_amount,
            'installment_2_due_date': cls.installment_2_due_date,
            'currency_id': cls.currency_id.id if cls.currency_id else self.currency_id.id,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment Loaded'),
                'message': _("Successfully loaded payment schedule from class '%s'.") % cls.name,
                'type': 'success',
                'sticky': False,
            }
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

    @api.depends('installment_1_amount', 'installment_2_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.installment_1_amount + rec.installment_2_amount

    @api.depends('installment_1_paid_amount', 'installment_2_paid_amount')
    def _compute_total_paid(self):
        for rec in self:
            rec.total_paid = rec.installment_1_paid_amount + rec.installment_2_paid_amount

    @api.depends('total_amount', 'total_paid')
    def _compute_total_balance(self):
        for rec in self:
            rec.total_balance = rec.total_amount - rec.total_paid

    @api.depends('installment_1_status', 'installment_2_status', 'installment_1_amount', 'installment_2_amount')
    def _compute_overall_status(self):
        today = fields.Date.today()
        for rec in self:
            inst1_paid = rec.installment_1_paid_amount >= rec.installment_1_amount if rec.installment_1_amount > 0 else True
            inst2_paid = rec.installment_2_paid_amount >= rec.installment_2_amount if rec.installment_2_amount > 0 else True

            if inst1_paid and inst2_paid:
                rec.overall_status = 'paid'
            elif rec.installment_1_paid_amount > 0 or rec.installment_2_paid_amount > 0:
                rec.overall_status = 'partial'
            elif (rec.installment_1_due_date and rec.installment_1_due_date < today and rec.installment_1_amount > 0) or \
                 (rec.installment_2_due_date and rec.installment_2_due_date < today and rec.installment_2_amount > 0):
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
