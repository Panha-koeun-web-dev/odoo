from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

def _open_records(self, model_name, domain):
    action = self.env['ir.actions.act_window']._for_xml_id(f'school_management.action_{model_name}')
    action['domain'] = domain
    return action


class SchoolStudent(models.Model):
    _name = 'school.student'
    _description = 'School Student'
    _order = 'name'

    name = fields.Char(string='Full Name', required=True)
    student_id = fields.Char(string='Student ID', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', required=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    class_id = fields.Many2one('school.class', string='Class')
    parent_name = fields.Char(string='Parent/Guardian Name')
    parent_phone = fields.Char(string='Parent Phone')
    parent_email = fields.Char(string='Parent Email')
    address = fields.Text(string='Address')
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today)
    study_start_date = fields.Date(string='Study Start Date', default=fields.Date.today)
    study_end_date = fields.Date(string='Study End Date')
    study_period = fields.Char(string='Study Period', compute='_compute_study_period', store=True)
    photo = fields.Image(string='Photo')
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Related User')

    attendance_ids = fields.One2many('school.attendance', 'student_id', string='Attendance')
    attendance_count = fields.Integer(string='Total Attendance', compute='_compute_attendance_stats', store=True)
    absent_count = fields.Integer(string='Absent Days', compute='_compute_attendance_stats', store=True)
    present_count = fields.Integer(string='Present Days', compute='_compute_attendance_stats', store=True)
    late_count = fields.Integer(string='Late Days', compute='_compute_attendance_stats', store=True)
    excused_count = fields.Integer(string='Excused Days', compute='_compute_attendance_stats', store=True)
    attendance_rate = fields.Float(string='Attendance Rate (%)', compute='_compute_attendance_stats', digits=(5, 1), store=True)
    today_attendance_status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('not_marked', 'Not Marked'),
    ], string="Today's Attendance", compute='_compute_today_attendance')
    today_attendance_id = fields.Many2one('school.attendance', string="Today's Attendance Record", compute='_compute_today_attendance')

    grade_ids = fields.One2many('school.grade', 'student_id', string='Grades')
    fee_ids = fields.One2many('school.fee', 'student_id', string='Fees')
    enrollment_ids = fields.One2many('school.enrollment', 'student_id', string='Enrollments')
    major_enrollment_ids = fields.One2many('school.major.enrollment', 'student_id', string='Major Enrollments')
    major_ids = fields.Many2many(
        'school.major',
        'school_major_student_rel',
        'student_id',
        'major_id',
        string='Majors',
        compute='_compute_majors',
    )
    certificate_ids = fields.One2many('school.certificate', 'student_id', string='Certificates')

    # Currency and Class Payment Integration
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

    notes = fields.Text(string='Notes')

    @api.depends_context('company')
    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for rec in self:
            rec.currency_id = currency

    @api.depends('year_payment_ids.total_amount', 'year_payment_ids.total_paid', 'year_payment_ids.total_balance', 'year_payment_ids.overall_status')
    def _compute_payment_summary(self):
        for rec in self:
            payments = rec.year_payment_ids
            rec.year_payment_count = len(payments)
            rec.total_year_amount = sum(payments.mapped('total_amount'))
            rec.total_year_paid = sum(payments.mapped('total_paid'))
            rec.total_year_balance = sum(payments.mapped('total_balance'))
            if not payments:
                rec.year_payment_status = 'no_record'
            elif any(p.overall_status == 'overdue' for p in payments):
                rec.year_payment_status = 'overdue'
            elif all(p.overall_status == 'paid' for p in payments):
                rec.year_payment_status = 'paid'
            elif any(p.overall_status in ('paid', 'partial') for p in payments):
                rec.year_payment_status = 'partial'
            else:
                rec.year_payment_status = 'pending'

    def _sync_year_payment_with_class(self):
        year_payment_model = self.env['school.student.year.payment']
        for rec in self:
            if rec.class_id and (rec.class_id.total_payment or rec.class_id.installment_1_amount or rec.class_id.installment_2_amount):
                academic_year = rec.class_id.payment_year or '2024-2025'
                existing = year_payment_model.search([
                    ('student_id', '=', rec.id),
                    ('year', '=', academic_year),
                ], limit=1)

                vals = {
                    'class_id': rec.class_id.id,
                    'year': academic_year,
                    'year_start': rec.class_id.year_start or fields.Date.today(),
                    'year_end': rec.class_id.year_end or (fields.Date.today() + timedelta(days=300)),
                    'installment_1_amount': rec.class_id.installment_1_amount,
                    'installment_1_due_date': rec.class_id.installment_1_due_date,
                    'installment_2_amount': rec.class_id.installment_2_amount,
                    'installment_2_due_date': rec.class_id.installment_2_due_date,
                    'currency_id': rec.class_id.currency_id.id if rec.class_id.currency_id else False,
                }

                if not existing:
                    vals['student_id'] = rec.id
                    year_payment_model.create(vals)
                elif existing.installment_1_paid_amount == 0 and existing.installment_2_paid_amount == 0:
                    existing.write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        students = super().create(vals_list)
        students._sync_year_payment_with_class()
        return students

    def write(self, vals):
        res = super().write(vals)
        if 'class_id' in vals:
            self._sync_year_payment_with_class()
        return res

    def action_sync_year_payment_from_class(self):
        self.ensure_one()
        if not self.class_id:
            raise UserError(_('This student is not assigned to any class.'))
        self._sync_year_payment_with_class()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Year Payment Synchronized'),
                'message': _("Payment schedule synchronized from class '%s'.") % self.class_id.name,
                'type': 'success',
                'sticky': False,
            }
        }

    @api.depends('major_enrollment_ids.major_id')
    def _compute_majors(self):
        for rec in self:
            rec.major_ids = rec.major_enrollment_ids.mapped('major_id')

    @api.depends('date_of_birth')
    def _compute_age(self):
        for rec in self:
            if rec.date_of_birth:
                today = fields.Date.today()
                rec.age = today.year - rec.date_of_birth.year - (
                    (today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day)
                )
            else:
                rec.age = 0

    @api.depends('study_start_date', 'study_end_date')
    def _compute_study_period(self):
        for rec in self:
            start_year = rec.study_start_date.year if rec.study_start_date else ''
            end_year = rec.study_end_date.year if rec.study_end_date else ''
            if start_year and end_year:
                rec.study_period = f'{start_year}-{end_year}'
            elif start_year:
                rec.study_period = str(start_year)
            else:
                rec.study_period = ''

    @api.constrains('study_start_date', 'study_end_date')
    def _check_study_dates(self):
        for rec in self:
            if rec.study_start_date and rec.study_end_date and rec.study_end_date < rec.study_start_date:
                raise ValidationError(_('Study End Date must be after Study Start Date.'))

    @api.depends('attendance_ids.status')
    def _compute_attendance_stats(self):
        for rec in self:
            attendances = rec.attendance_ids
            total = len(attendances)
            present = sum(1 for a in attendances if a.status == 'present')
            absent = sum(1 for a in attendances if a.status == 'absent')
            late = sum(1 for a in attendances if a.status == 'late')
            excused = sum(1 for a in attendances if a.status == 'excused')
            attended = present + late + excused

            rec.attendance_count = total
            rec.present_count = present
            rec.absent_count = absent
            rec.late_count = late
            rec.excused_count = excused
            rec.attendance_rate = round((attended / total * 100), 1) if total else 0.0

    def _compute_today_attendance(self):
        today = fields.Date.today()
        for rec in self:
            today_record = rec.attendance_ids.filtered(lambda a: a.date == today)[:1]
            if today_record:
                rec.today_attendance_id = today_record.id
                rec.today_attendance_status = today_record.status
            else:
                rec.today_attendance_id = False
                rec.today_attendance_status = 'not_marked'

    def _mark_today_attendance(self, status):
        today = fields.Date.today()
        attendance_model = self.env['school.attendance']
        for rec in self:
            record = attendance_model.search([
                ('student_id', '=', rec.id),
                ('date', '=', today),
            ], limit=1)
            if record:
                record.status = status
            else:
                attendance_model.create({
                    'student_id': rec.id,
                    'date': today,
                    'status': status,
                })

    def action_mark_present_today(self):
        self._mark_today_attendance('present')

    def action_mark_absent_today(self):
        self._mark_today_attendance('absent')

    def action_mark_late_today(self):
        self._mark_today_attendance('late')

    def action_mark_excused_today(self):
        self._mark_today_attendance('excused')

    def open_attendance(self):
        action = _open_records(self, 'attendance', [('student_id', '=', self.id)])
        action['context'] = {
            'default_student_id': self.id,
            'default_class_id': self.class_id.id if self.class_id else False,
        }
        return action

    def open_absent_attendance(self):
        action = _open_records(self, 'attendance', [
            ('student_id', '=', self.id),
            ('status', '=', 'absent'),
        ])
        action['name'] = _('Absent Days - %s') % (self.name or '')
        action['context'] = {
            'default_student_id': self.id,
            'default_status': 'absent',
            'default_class_id': self.class_id.id if self.class_id else False,
        }
        return action

    def open_grades(self):
        return _open_records(self, 'grade', [('student_id', '=', self.id)])

    def open_fees(self):
        return _open_records(self, 'fee', [('student_id', '=', self.id)])

    def open_enrollments(self):
        return _open_records(self, 'enrollment', [('student_id', '=', self.id)])

    def open_major_enrollments(self):
        return _open_records(self, 'major_enrollment', [('student_id', '=', self.id)])

    def open_year_payments(self):
        action = _open_records(self, 'student_year_payment', [('student_id', '=', self.id)])
        action['context'] = {
            'default_student_id': self.id,
            'default_class_id': self.class_id.id if self.class_id else False,
        }
        return action

    def action_generate_certificate(self):
        self.ensure_one()
        certs = self.env['school.certificate'].generate_certificates(self)
        cert = certs[:1]
        if not cert:
            return {
                'type': 'ir.actions.act_window_close',
            }
        return {
            'name': _('Certificate'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.certificate',
            'view_mode': 'form',
            'res_id': cert.id,
            'target': 'current',
        }

    def action_print_student_certificates(self):
        certs = self.env['school.certificate'].generate_certificates(self)
        if not certs:
            return {
                'type': 'ir.actions.act_window_close',
            }
        return self.env.ref('school_management.action_report_school_certificate').report_action(
            certs)

    def action_bulk_enroll(self):
        return {
            'name': 'Bulk Enroll Students',
            'type': 'ir.actions.act_window',
            'res_model': 'school.enroll.students.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_ids': self.ids,
            },
        }
