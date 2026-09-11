from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


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
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise AccessError(_("Only administrators are permitted to register payments."))
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
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise AccessError(_("Only administrators are permitted to configure payment deadlines."))
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
