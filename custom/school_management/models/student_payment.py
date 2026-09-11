from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolStudentPayment(models.Model):
    _inherit = 'school.student'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        default=lambda self: self.env.company.currency_id,
    )
    class_total_payment = fields.Monetary(
        related='class_id.total_payment',
        string='Class Total Payment',
        currency_field='currency_id',
        readonly=True,
    )
    year_payment_ids = fields.One2many('school.student.year.payment', 'student_id', string='Year Payments')
    year_payment_count = fields.Integer(string='Year Payment Count', compute='_compute_payment_summary')
    total_year_amount = fields.Monetary(string='Total Year Payment', currency_field='currency_id', compute='_compute_payment_summary')
    total_year_paid = fields.Monetary(string='Total Year Paid', currency_field='currency_id', compute='_compute_payment_summary')
    total_year_balance = fields.Monetary(string='Total Year Balance', currency_field='currency_id', compute='_compute_payment_summary')
    year_payment_status = fields.Selection([
        ('paid', 'Fully Paid'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('pending', 'Pending'),
        ('no_record', 'No Payment Record'),
    ], string='Year Payment Status', compute='_compute_payment_summary')
    next_payment_deadline = fields.Date(string='Next Due Date', compute='_compute_payment_summary')
    next_deadline_status = fields.Selection([
        ('no_deadline', 'No Deadline'),
        ('paid', 'Fully Paid'),
        ('today', 'Due Today'),
        ('upcoming', 'Upcoming'),
        ('overdue', 'Overdue'),
    ], string='Next Deadline Status', compute='_compute_payment_summary')
    fee_ids = fields.One2many('school.fee', 'student_id', string='Fees')
    fee_count = fields.Integer(string='Fee Count', compute='_compute_fee_count')

    @api.depends_context('company')
    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for rec in self:
            rec.currency_id = currency

    @api.depends(
        'year_payment_ids.total_amount',
        'year_payment_ids.total_paid',
        'year_payment_ids.total_balance',
        'year_payment_ids.overall_status',
        'year_payment_ids.next_deadline',
        'year_payment_ids.deadline_status',
    )
    def _compute_payment_summary(self):
        for rec in self:
            payments = rec.year_payment_ids
            rec.year_payment_count = len(payments)
            rec.total_year_amount = sum(payments.mapped('total_amount'))
            rec.total_year_paid = sum(payments.mapped('total_paid'))
            rec.total_year_balance = sum(payments.mapped('total_balance'))
            if not payments:
                rec.year_payment_status = 'no_record'
                rec.next_payment_deadline = False
                rec.next_deadline_status = 'no_deadline'
            else:
                if any(p.overall_status == 'overdue' for p in payments):
                    rec.year_payment_status = 'overdue'
                elif all(p.overall_status == 'paid' for p in payments):
                    rec.year_payment_status = 'paid'
                elif any(p.overall_status in ('paid', 'partial') for p in payments):
                    rec.year_payment_status = 'partial'
                else:
                    rec.year_payment_status = 'pending'

                active_deadlines = payments.filtered(lambda p: p.total_balance > 0 and p.next_deadline)
                if active_deadlines:
                    earliest = min(active_deadlines, key=lambda p: p.next_deadline)
                    rec.next_payment_deadline = earliest.next_deadline
                    rec.next_deadline_status = earliest.deadline_status
                elif all(p.overall_status == 'paid' for p in payments):
                    rec.next_payment_deadline = False
                    rec.next_deadline_status = 'paid'
                else:
                    rec.next_payment_deadline = False
                    rec.next_deadline_status = 'no_deadline'

    @api.depends('fee_ids')
    def _compute_fee_count(self):
        for rec in self:
            rec.fee_count = len(rec.fee_ids)

    def _sync_year_payment_with_class(self):
        """Sync student payment record to follow the payment configured by the student's class."""
        year_payment_model = self.env['school.student.year.payment']
        for rec in self:
            if rec.class_id and (rec.class_id.total_payment or rec.class_id.installment_1_amount or rec.class_id.installment_2_amount):
                cls = rec.class_id
                academic_year = cls.payment_year or '2024-2025'
                existing = year_payment_model.search([
                    ('student_id', '=', rec.id),
                    ('year', '=', academic_year),
                ], limit=1)

                vals = {
                    'class_id': cls.id,
                    'year': academic_year,
                    'year_start': cls.year_start or fields.Date.today(),
                    'year_end': cls.year_end or (fields.Date.today() + timedelta(days=300)),
                    'installment_1_amount': cls.installment_1_amount or 0.0,
                    'installment_1_due_date': cls.installment_1_due_date,
                    'installment_2_amount': cls.installment_2_amount or 0.0,
                    'installment_2_due_date': cls.installment_2_due_date,
                    'currency_id': cls.currency_id.id if cls.currency_id else False,
                }

                if not existing:
                    vals['student_id'] = rec.id
                    year_payment_model.create(vals)
                else:
                    existing.write(vals)

    def action_sync_year_payment_from_class(self):
        """Action button on student form to ensure payment follows the assigned class."""
        self.ensure_one()
        if not self.class_id:
            raise UserError(_('This student is not assigned to any class.'))
        self._sync_year_payment_with_class()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Year Payment Synchronized'),
                'message': _("Payment schedule successfully updated to follow class '%s' (Tuition: %s).") % (
                    self.class_id.name, self.class_id.total_payment
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_set_year_payment_deadline(self):
        self.ensure_one()
        cls = self.class_id
        academic_year = cls.payment_year if cls and cls.payment_year else '2024-2025'
        payment = self.env['school.student.year.payment'].search([
            ('student_id', '=', self.id),
            ('year', '=', academic_year),
        ], limit=1)
        if not payment:
            self._sync_year_payment_with_class()
            payment = self.env['school.student.year.payment'].search([
                ('student_id', '=', self.id),
                ('year', '=', academic_year),
            ], limit=1)
        if not payment:
            payment = self.year_payment_ids[:1]
        if not payment:
            raise UserError(_('No year payment record found for this student. Please configure class payment first.'))
        return payment.action_open_deadline_wizard()

    def open_fees(self):
        return self._open_records('fee', [('student_id', '=', self.id)])

    def open_year_payments(self):
        action = self._open_records('student_year_payment', [('student_id', '=', self.id)])
        action['context'] = {
            'default_student_id': self.id,
            'default_class_id': self.class_id.id if self.class_id else False,
        }
        return action
