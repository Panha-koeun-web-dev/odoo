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

    # Currency and Payment Configuration
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        default=lambda self: self.env.company.currency_id,
    )
    payment_year = fields.Char(string='Academic Year', default='2024-2025', help="Default academic year for class payment (e.g. 2024-2025)")
    year_start = fields.Date(string='Academic Year Start')
    year_end = fields.Date(string='Academic Year End')
    total_payment = fields.Monetary(string='Total Payment', currency_field='currency_id', help="Total tuition / payment required per student in this class")
    installment_1_amount = fields.Monetary(string='Installment 1 Amount', currency_field='currency_id')
    installment_1_due_date = fields.Date(string='Installment 1 Due Date')
    installment_2_amount = fields.Monetary(string='Installment 2 Amount', currency_field='currency_id')
    installment_2_due_date = fields.Date(string='Installment 2 Due Date')

    # Student Year Payments Integration & Analytics
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
                ('class_id', '=', rec.id)
            ])

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

    def action_generate_year_payments(self):
        self.ensure_one()
        if not self.student_ids:
            raise UserError(_('There are no students assigned to this class.'))

        academic_year = self.payment_year or '2024-2025'
        year_payment_model = self.env['school.student.year.payment']
        created_count = 0
        updated_count = 0

        for student in self.student_ids:
            payment_rec = year_payment_model.search([
                ('student_id', '=', student.id),
                ('year', '=', academic_year),
            ], limit=1)

            vals = {
                'class_id': self.id,
                'year': academic_year,
                'year_start': self.year_start or fields.Date.today(),
                'year_end': self.year_end or (fields.Date.today() + timedelta(days=300)),
                'installment_1_amount': self.installment_1_amount,
                'installment_1_due_date': self.installment_1_due_date,
                'installment_2_amount': self.installment_2_amount,
                'installment_2_due_date': self.installment_2_due_date,
                'currency_id': self.currency_id.id if self.currency_id else False,
            }

            if not payment_rec:
                vals['student_id'] = student.id
                year_payment_model.create(vals)
                created_count += 1
            else:
                if payment_rec.installment_1_paid_amount == 0 and payment_rec.installment_2_paid_amount == 0:
                    payment_rec.write(vals)
                    updated_count += 1

        msg = _("Payment synchronization complete: %d created, %d updated for class '%s'.") % (
            created_count, updated_count, self.name
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Student Year Payments'),
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
