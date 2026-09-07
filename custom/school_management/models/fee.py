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

    def action_mark_paid(self):
        for rec in self:
            rec.status = 'paid'
            rec.paid_date = fields.Date.today()
            rec.paid_amount = rec.amount