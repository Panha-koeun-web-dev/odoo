from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

def _open_records(self, model_name, domain):
    action = self.env['ir.actions.act_window']._for_xml_id(f'school_management.action_{model_name}')
    action['domain'] = domain
    return action


class SchoolStudent(models.Model):
    _name = 'school.student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
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

    # Study Status Management (Stop / Kick / Continue Study)
    study_status = fields.Selection([
        ('studying', 'Studying'),
        ('stopped', 'Stopped Studying'),
    ], string='Study Status', default='studying', required=True, copy=False)
    stop_date = fields.Date(string='Stop Date', copy=False, help="Date when student stopped studying")
    stop_reason = fields.Text(string='Reason for Stopping', copy=False, help="Reason why the student stopped studying or was kicked")
    recontinue_date = fields.Date(string='Resumed Date', copy=False, help="Date when student resumed studying")

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
    grade_count = fields.Integer(string='Total Exams', compute='_compute_grade_stats')
    average_score = fields.Float(string='Average Score (%)', compute='_compute_grade_stats', digits=(5, 1))
    passed_exam_count = fields.Integer(string='Passed Exams', compute='_compute_grade_stats')
    failed_exam_count = fields.Integer(string='Failed Exams', compute='_compute_grade_stats')
    academic_performance = fields.Char(string='Overall Grade', compute='_compute_grade_stats')
    fee_ids = fields.One2many('school.fee', 'student_id', string='Fees')
    fee_count = fields.Integer(string='Fee Count', compute='_compute_fee_count')
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
    next_payment_deadline = fields.Date(string='Next Due Date', compute='_compute_payment_summary')
    next_deadline_status = fields.Selection([
        ('no_deadline', 'No Deadline'),
        ('paid', 'Fully Paid'),
        ('today', 'Due Today'),
        ('upcoming', 'Upcoming'),
        ('overdue', 'Overdue'),
    ], string='Next Deadline Status', compute='_compute_payment_summary')

    notes = fields.Text(string='Notes')

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

    @api.depends('grade_ids.percentage', 'grade_ids.result')
    def _compute_grade_stats(self):
        for rec in self:
            grades = rec.grade_ids
            rec.grade_count = len(grades)
            if grades:
                percentages = grades.mapped('percentage')
                rec.average_score = round(sum(percentages) / len(percentages), 1) if percentages else 0.0
                rec.passed_exam_count = len(grades.filtered(lambda g: g.result == 'pass'))
                rec.failed_exam_count = len(grades.filtered(lambda g: g.result == 'fail'))
                avg = rec.average_score
                if avg >= 90:
                    rec.academic_performance = 'Excellent (A+)'
                elif avg >= 80:
                    rec.academic_performance = 'Very Good (A)'
                elif avg >= 70:
                    rec.academic_performance = 'Good (B)'
                elif avg >= 60:
                    rec.academic_performance = 'Satisfactory (C)'
                elif avg >= 50:
                    rec.academic_performance = 'Pass (D)'
                else:
                    rec.academic_performance = 'Needs Improvement (F)'
            else:
                rec.average_score = 0.0
                rec.passed_exam_count = 0
                rec.failed_exam_count = 0
                rec.academic_performance = 'No Exams Yet'

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
        """Action button on student form to ensure payment follows the assigned class."""
        self.ensure_one()
        if not self.class_id:
            raise UserError(_('This student is not assigned to any class.'))\

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

    # ==================== STOP / CONTINUE STUDY ACTIONS ====================
    def action_stop_study(self):
        """Direct action to stop / kick student(s) from studying."""
        for rec in self:
            rec.write({
                'study_status': 'stopped',
                'stop_date': fields.Date.today(),
                'stop_reason': rec.stop_reason or _('Marked as stopped studying by administrator.'),
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Student(s) Stopped'),
                'message': _('Selected student(s) marked as Stopped Studying.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_continue_study(self):
        """Direct action to resume / continue study for student(s)."""
        for rec in self:
            rec.write({
                'study_status': 'studying',
                'recontinue_date': fields.Date.today(),
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Study Continued'),
                'message': _('Selected student(s) are now active and Studying.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_stop_study_wizard(self):
        self.ensure_one()
        return {
            'name': _('Stop Student Study (Kick / Drop Out)'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.stop.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.id,
                'default_stop_date': fields.Date.today(),
            },
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
        is_student = self.env.user.has_group('school_management.group_school_student') and not self.env.is_admin()
        certs = self.env['school.certificate'].sudo().generate_certificates(self, certificate_type='transcript')
        cert = certs[:1]
        if not cert:
            return {
                'type': 'ir.actions.act_window_close',
            }
        action = {
            'name': _('Academic Transcript & Report Card'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.certificate',
            'view_mode': 'form',
            'res_id': cert.id,
            'target': 'current',
        }
        if is_student:
            action['context'] = {'create': False, 'edit': False, 'delete': False}
            action['flags'] = {'mode': 'readonly'}
        return action

    def action_print_academic_transcript(self):
        """Directly generate and print the official Academic Transcript / Report Card PDF."""
        self.ensure_one()
        certs = self.env['school.certificate'].generate_certificates(self, certificate_type='transcript')
        if not certs:
            return {'type': 'ir.actions.act_window_close'}
        return certs[:1].action_print_transcript()

    def action_print_student_certificates(self):
        certs = self.env['school.certificate'].generate_certificates(self, certificate_type='completion')
        if not certs:
            return {
                'type': 'ir.actions.act_window_close',
            }
        return self.env.ref('school_management.action_report_school_certificate').report_action(
            certs)

    def action_create_user(self):
        self.ensure_one()
        if not self.email:
            raise UserError(_('Please provide an email address for the student first.'))

        login = self.email.strip().lower()
        existing_user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        group_student = self.env.ref('school_management.group_school_student')
        group_internal = self.env.ref('base.group_user')
        group_portal = self.env.ref('base.group_portal', raise_if_not_found=False)
        action_student = self.env.ref('school_management.action_student', raise_if_not_found=False)

        default_pwd = 'password123'
        groups_to_add = [(4, group_student.id), (4, group_internal.id)]
        if group_portal:
            groups_to_add.append((3, group_portal.id))

        if existing_user:
            existing_user.sudo().write({
                'name': self.name,
                'email': self.email,
                'group_ids': groups_to_add,
                'action_id': action_student.id if action_student else False,
            })
            self.sudo().write({'user_id': existing_user.id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('User Account Linked'),
                    'message': _('Linked to existing user account.\nEmail / Login: %s\nPassword: %s') % (login, default_pwd),
                    'type': 'success',
                    'sticky': True,
                }
            }
        else:
            new_user = self.env['res.users'].sudo().create({
                'name': self.name,
                'login': login,
                'email': self.email,
                'password': default_pwd,
                'group_ids': [(6, 0, [group_student.id, group_internal.id])],
                'action_id': action_student.id if action_student else False,
            })
            self.sudo().write({'user_id': new_user.id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Login Created Successfully'),
                    'message': _('Created login account for Student %s!\nEmail / Login: %s\nPassword: %s') % (self.name, login, default_pwd),
                    'type': 'success',
                    'sticky': True,
                }
            }

    def action_reset_user_password(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(_('No user account is linked to this student.'))
        default_pwd = 'password123'
        self.user_id.sudo().write({'password': default_pwd})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Password Reset'),
                'message': _('Password for %s has been reset to: %s') % (self.user_id.login, default_pwd),
                'type': 'info',
                'sticky': True,
            }
        }

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

    def action_open_add_to_exam_wizard(self):
        return {
            'name': _('Add Student(s) to Exam'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.exam.select.student.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_ids': self.ids,
            },
        }


class SchoolStudentStopWizard(models.TransientModel):
    _name = 'school.student.stop.wizard'
    _description = 'Stop Student Study Wizard'

    student_id = fields.Many2one('school.student', string='Student', required=True)
    stop_date = fields.Date(string='Stop Date', required=True, default=fields.Date.today)
    reason_type = fields.Selection([
        ('kicked', 'Dismissed / Kicked (Disciplinary)'),
        ('dropped', 'Requested to Stop / Dropped Out'),
        ('financial', 'Financial Difficulty'),
        ('personal', 'Personal / Family Reasons'),
        ('transfer', 'Transferred to Another School'),
        ('health', 'Health / Medical Reasons'),
        ('other', 'Other Reason'),
    ], string='Reason Category', required=True, default='dropped')
    stop_reason = fields.Text(string='Detailed Reason / Remarks')

    def action_confirm_stop(self):
        self.ensure_one()
        category_label = dict(self._fields['reason_type'].selection).get(self.reason_type, '')
        full_reason = f"[{category_label}] {self.stop_reason}" if self.stop_reason else f"[{category_label}]"
        self.student_id.write({
            'study_status': 'stopped',
            'stop_date': self.stop_date,
            'stop_reason': full_reason,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Student Stopped Studying'),
                'message': _("Student '%s' has been marked as Stopped Studying.") % self.student_id.name,
                'type': 'warning',
                'sticky': False,
            }
        }
