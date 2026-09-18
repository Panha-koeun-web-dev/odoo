from odoo import models, fields, api, _


class SchoolFee(models.Model):
    _name = 'school.fee'
    _inherit = ['school.state.notification']
    _description = 'Student Fee'
    _order = 'due_date desc'
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True)
    class_id = fields.Many2one(related='student_id.class_id', string='Class', store=True)
    fee_type = fields.Selection([
        ('tuition', 'Tuition Fee'),
        ('exam', 'Exam Fee'),
        ('library', 'Library Fee'),
        ('lab', 'Lab Fee'),
        ('transport', 'Transport Fee'),
        ('other', 'Other'),
    ], string='Fee Type', required=True)
    amount = fields.Float(string='Amount', required=True)
    due_date = fields.Date(string='Due Date', required=True)
    paid_date = fields.Date(string='Paid Date')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('partial', 'Partial'),
    ], string='Status', default='pending')
    paid_amount = fields.Float(string='Paid Amount', default=0)
    balance = fields.Float(string='Balance', compute='_compute_balance', store=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('online', 'Online'),
    ], string='Payment Method')
    receipt_number = fields.Char(string='Receipt Number')
    notes = fields.Text(string='Notes')

    @api.depends('amount', 'paid_amount')
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.amount - rec.paid_amount

    def _get_state_email_template(self):
        return 'school_management.email_template_fee_status'

    def _get_state_change_recipients(self):
        return self.student_id.email or self.student_id.parent_email

    def _generate_receipt_number(self):
        year = fields.Date.today().year
        return f"REC-FEE-{year}-{self.id:04d}"

    def action_mark_paid(self):
        for rec in self:
            rec.status = 'paid'
            rec.paid_date = fields.Date.today()
            rec.paid_amount = rec.amount
            if not rec.payment_method:
                rec.payment_method = 'cash'
            if not rec.receipt_number:
                rec.receipt_number = rec._generate_receipt_number()

    def action_print_receipt(self):
        self.ensure_one()
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        return self.env.ref('school_management.action_report_student_fee_receipt').with_context(
            active_model='school.fee',
            active_id=self.id,
            active_ids=[self.id]
        ).report_action(self, data={'active_model': 'school.fee'})

    def action_export_xlsx(self):
        ids = self.ids or self.env.context.get('active_ids') or []
        ids_str = ','.join(str(x) for x in ids) if ids else ''
        return {
            'type': 'ir.actions.act_url',
            'url': f'/school_management/export_report_xlsx?report_type=fee&ids={ids_str}',
            'target': 'self',
        }
