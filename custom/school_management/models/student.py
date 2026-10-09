from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

def _open_records(self, model_name, domain):
    action = self.env['ir.actions.act_window'].sudo()._for_xml_id(f'school_management.action_{model_name}')
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
    age = fields.Integer(string='Age', compute='_compute_age', store=True, compute_sudo=True)
    class_id = fields.Many2one('school.class', string='Class')
    parent_name = fields.Char(string='Parent/Guardian Name')
    parent_phone = fields.Char(string='Parent Phone')
    parent_email = fields.Char(string='Parent Email')
    address = fields.Text(string='Address')
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today)
    study_start_date = fields.Date(string='Study Start Date', default=fields.Date.today)
    study_end_date = fields.Date(string='Study End Date')
    study_period = fields.Char(string='Study Period', compute='_compute_study_period', store=True, compute_sudo=True)
    photo = fields.Image(string='Photo', max_width=512, max_height=512, verify_resolution=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Related User')

    blood_group = fields.Selection([
        ('a_pos', 'A+'),
        ('a_neg', 'A-'),
        ('b_pos', 'B+'),
        ('b_neg', 'B-'),
        ('ab_pos', 'AB+'),
        ('ab_neg', 'AB-'),
        ('o_pos', 'O+'),
        ('o_neg', 'O-'),
        ('unknown', 'Unknown'),
    ], string='Blood Group', default='unknown')
    id_card_qr_code = fields.Binary(
        string='ID Card QR Code',
        compute='_compute_id_card_qr_code',
        help='Machine-scannable QR code containing student identity and verification details.',
    )

    # Study Status Management (Stop / Kick / Continue Study)
    study_status = fields.Selection([
        ('studying', 'Studying'),
        ('stopped', 'Stopped Studying'),
    ], string='Study Status', default='studying', required=True, copy=False)
    stop_date = fields.Date(string='Stop Date', copy=False, help="Date when student stopped studying")
    stop_reason = fields.Text(string='Reason for Stopping', copy=False, help="Reason why the student stopped studying or was kicked")
    recontinue_date = fields.Date(string='Resumed Date', copy=False, help="Date when student resumed studying")

    attendance_ids = fields.One2many('school.attendance', 'student_id', string='Attendance')
    attendance_count = fields.Integer(string='Total Attendance', compute='_compute_attendance_stats', store=True, compute_sudo=True)
    absent_count = fields.Integer(string='Absent Days', compute='_compute_attendance_stats', store=True, compute_sudo=True)
    present_count = fields.Integer(string='Present Days', compute='_compute_attendance_stats', store=True, compute_sudo=True)
    late_count = fields.Integer(string='Late Days', compute='_compute_attendance_stats', store=True, compute_sudo=True)
    excused_count = fields.Integer(string='Excused Days', compute='_compute_attendance_stats', store=True, compute_sudo=True)
    attendance_rate = fields.Float(string='Attendance Rate (%)', compute='_compute_attendance_stats', digits=(5, 1), store=True, compute_sudo=True)
    today_attendance_status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('not_marked', 'Not Marked'),
    ], string="Today's Attendance", compute='_compute_today_attendance')
    today_attendance_id = fields.Many2one('school.attendance', string="Today's Attendance Record", compute='_compute_today_attendance')

    grade_ids = fields.One2many('school.grade', 'student_id', string='Grades')
    grade_count = fields.Integer(string='Total Exams', compute='_compute_grade_stats', store=True, compute_sudo=True)
    exam_average_score = fields.Float(
        string='Exam Average (%)',
        compute='_compute_grade_stats',
        digits=(5, 1),
        store=True,
        compute_sudo=True,
        help="Average score across all exams (weighted at 90% of overall grade)."
    )
    average_score = fields.Float(
        string='Average Score (%)',
        compute='_compute_grade_stats',
        digits=(5, 1),
        store=True,
        compute_sudo=True,
        help="Overall academic average weighted as: 90% Exams + 10% Attendance."
    )
    gpa = fields.Float(
        string='GPA (4.0)',
        compute='_compute_grade_stats',
        digits=(3, 2),
        store=True,
        compute_sudo=True,
        help="Overall Grade Point Average on 4.0 scale weighted as: 90% Exams + 10% Attendance."
    )
    passed_exam_count = fields.Integer(string='Passed Exams', compute='_compute_grade_stats', store=True, compute_sudo=True)
    failed_exam_count = fields.Integer(string='Failed Exams', compute='_compute_grade_stats', store=True, compute_sudo=True)
    academic_performance = fields.Char(string='Overall Grade', compute='_compute_grade_stats', store=True, compute_sudo=True)
    fee_ids = fields.One2many('school.fee', 'student_id', string='Fees')
    fee_count = fields.Integer(string='Fee Count', compute='_compute_fee_count')
    exam_count = fields.Integer(string='Scheduled Exams', compute='_compute_student_exam_stats')
    upcoming_exam_count = fields.Integer(string='Upcoming Exams', compute='_compute_student_exam_stats')
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

    # Weekly Study Subjects & Workload
    study_subject_ids = fields.One2many('school.student.subject', 'student_id', string='Weekly Study Subjects')
    timetable_ids = fields.Many2many(
        'school.timetable',
        string='Timetable Sessions',
        compute='_compute_timetable_ids',
        help="All active timetable sessions for this student (both individual tutoring, elective groups, and class sessions)."
    )

    study_subject_count = fields.Integer(string='Study Subjects Count', compute='_compute_study_stats')
    total_weekly_study_hours = fields.Float(string='Total Weekly Study Hours', compute='_compute_study_stats')
    total_weekly_study_sessions = fields.Integer(string='Total Weekly Sessions', compute='_compute_study_stats')
    total_scheduled_study_hours = fields.Float(string='Total Scheduled Hours', compute='_compute_study_stats')
    study_teacher_ids = fields.Many2many('school.teacher', string='Instructing Teachers', compute='_compute_study_stats')
    study_teacher_count = fields.Integer(string='Teachers Count', compute='_compute_study_stats')
    study_subject_all_ids = fields.Many2many('school.subject', string='Enrolled Subjects', compute='_compute_study_stats')
    permission_ids = fields.One2many('school.permission', 'student_id', string='Permission Requests')
    permission_count = fields.Integer(string='Permissions', compute='_compute_permission_count')
    permission_approved_count = fields.Integer(string='Approved Leaves', compute='_compute_permission_count')
    permission_pending_count = fields.Integer(string='Pending Permissions', compute='_compute_permission_count')
    permission_total_days = fields.Float(string='Total Excused Days', compute='_compute_permission_count')
    teacher_feedback_ids = fields.One2many(
        'school.feedback',
        'student_id',
        string='Teacher Feedback Records',
        domain=[('report_type', '=', 'teacher_to_student'), ('state', '!=', 'draft')],
    )
    teaching_report_ids = fields.One2many(
        'school.feedback',
        'student_id',
        string='Teaching Reports Filed',
        domain=[('report_type', '=', 'student_to_teacher')],
    )
    teacher_feedback_count = fields.Integer(string='Teacher Feedback', compute='_compute_feedback_counts')
    teaching_report_count = fields.Integer(string='Teaching Reports', compute='_compute_feedback_counts')

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

    timetable_count = fields.Integer(string='Schedule Sessions Count', compute='_compute_timetable_ids')
    holiday_count = fields.Integer(string='Class & School Holidays Count', compute='_compute_timetable_ids')

    def _compute_timetable_count(self):
        return self._compute_timetable_ids()

    def action_view_timetable(self):
        self.ensure_one()
        domain = [
            ('active', '=', True),
            '|',
            ('is_holiday', '=', True),
            '|',
            ('student_id', '=', self.id),
            ('student_ids', 'in', [self.id]),
        ]
        if self.class_id:
            domain = [
                ('active', '=', True),
                '|',
                ('is_holiday', '=', True),
                '|',
                '|',
                ('student_id', '=', self.id),
                ('student_ids', 'in', [self.id]),
                '&',
                ('class_id', '=', self.class_id.id),
                ('student_id', '=', False),
            ]
        ctx = {
            'default_student_id': self.id,
            'default_class_id': self.class_id.id if self.class_id else False,
            'search_default_filter_mon_fri': 1,
            'create': False,
        }
        if self.class_id and self.class_id.current_term_id and self.class_id.current_term_id.date_start:
            ctx['initial_date'] = self.class_id.current_term_id.date_start.isoformat()
        return {
            'name': _('Study Schedule - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': domain,
            'context': ctx,
        }

    @api.depends('fee_ids')
    def _compute_fee_count(self):
        for rec in self:
            rec.fee_count = len(rec.fee_ids)

    @api.depends(
        'grade_ids',
        'grade_ids.marks_obtained',
        'grade_ids.total_marks',
        'grade_ids.percentage',
        'grade_ids.result',
        'grade_ids.grade_letter',
        'grade_ids.subject_id.credits',
        'attendance_rate',
        'attendance_count',
        'attendance_ids',
        'attendance_ids.status',
    )
    def _compute_grade_stats(self):
        grade_pts_map = {
            'a+': 4.0, 'a': 4.0, 'a-': 3.7,
            'b+': 3.3, 'b': 3.0, 'b-': 2.7,
            'c+': 2.3, 'c': 2.0, 'c-': 1.7,
            'd': 1.0, 'f': 0.0,
        }
        for rec in self:
            grades = rec.grade_ids
            rec.grade_count = len(grades)
            if grades:
                percentages = grades.mapped('percentage')
                exam_avg = sum(percentages) / len(percentages) if percentages else 0.0
                rec.exam_average_score = round(exam_avg, 1)
                rec.passed_exam_count = len(grades.filtered(lambda g: g.result == 'pass'))
                rec.failed_exam_count = len(grades.filtered(lambda g: g.result == 'fail'))

                # Weighting: 90% Exam + 10% Attendance
                if rec.attendance_count > 0:
                    att_score = rec.attendance_rate
                else:
                    att_score = exam_avg  # No attendance records yet; unpenalized baseline

                rec.average_score = round((exam_avg * 0.90) + (att_score * 0.10), 1)

                # Quality Points & GPA on Standard 4.0 Scale
                total_creds = 0
                total_pts = 0.0
                for g in grades:
                    creds = g.subject_id.credits or 3
                    gp = grade_pts_map.get((g.grade_letter or '').lower())
                    if gp is None:
                        pct = g.percentage if g.percentage else ((g.marks_obtained / g.total_marks * 100) if g.total_marks else 0.0)
                        if pct >= 90:
                            gp = 4.0
                        elif pct >= 80:
                            gp = 4.0
                        elif pct >= 70:
                            gp = 3.3
                        elif pct >= 60:
                            gp = 3.0
                        elif pct >= 50:
                            gp = 2.3
                        elif pct >= 40:
                            gp = 2.0
                        elif pct >= 30:
                            gp = 1.0
                        else:
                            gp = 0.0
                    total_creds += creds
                    total_pts += (gp * creds)

                exam_gpa = (total_pts / total_creds) if total_creds else 0.0
                if rec.attendance_count > 0:
                    att_gpa = (rec.attendance_rate / 100.0) * 4.0
                else:
                    att_gpa = exam_gpa

                rec.gpa = round((exam_gpa * 0.90) + (att_gpa * 0.10), 2)

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
                rec.exam_average_score = 0.0
                rec.average_score = 0.0
                rec.gpa = 0.0
                rec.passed_exam_count = 0
                rec.failed_exam_count = 0
                rec.academic_performance = 'No Exams Yet'

    @api.depends('grade_ids', 'grade_ids.exam_id', 'grade_ids.exam_datetime')
    def _compute_student_exam_stats(self):
        now = fields.Datetime.now()
        for student in self:
            grades = student.grade_ids
            student.exam_count = len(grades)
            student.upcoming_exam_count = len(grades.filtered(
                lambda g: g.exam_datetime and g.exam_datetime >= now and g.attendance_status == 'scheduled'
            ))

    def action_view_student_exams(self):
        self.ensure_one()
        return {
            'name': _('My Examinations - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.grade',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {
                'default_student_id': self.id,
            },
        }

    def action_recompute_academic_metrics(self):
        """Action button to trigger full academic metrics recalculation."""
        self._compute_attendance_stats()
        self._compute_grade_stats()
        certs = self.env['school.certificate'].search([('student_id', 'in', self.ids)])
        if certs:
            certs.action_recompute_metrics()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recalculation Complete'),
                'message': _('Academic metrics updated: 90%% Exam + 10%% Attendance for %s student(s).') % len(self),
                'type': 'success',
                'sticky': False,
            }
        }

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

    @api.depends(
        'study_subject_ids',
        'study_subject_ids.weekly_hours',
        'study_subject_ids.weekly_sessions',
        'study_subject_ids.scheduled_hours',
        'study_subject_ids.study_status',
        'study_subject_ids.active',
    )
    def _compute_study_stats(self):
        for rec in self:
            active_subs = rec.study_subject_ids.filtered(lambda s: s.active and s.study_status == 'active')
            rec.study_subject_count = len(active_subs)
            rec.total_weekly_study_hours = sum(active_subs.mapped('weekly_hours'))
            rec.total_weekly_study_sessions = sum(active_subs.mapped('weekly_sessions'))
            rec.total_scheduled_study_hours = sum(active_subs.mapped('scheduled_hours'))

    def _compute_timetable_ids(self):
        Timetable = self.env['school.timetable']
        for student in self:
            domain = [('active', '=', True), ('is_holiday', '=', False)]
            if student.class_id:
                domain.extend([
                    '|',
                    '|',
                    ('student_id', '=', student.id),
                    ('student_ids', 'in', student.id),
                    '&',
                    ('student_id', '=', False),
                    ('class_id', '=', student.class_id.id),
                ])
            else:
                domain.extend([
                    '|',
                    ('student_id', '=', student.id),
                    ('student_ids', 'in', student.id),
                ])
            sessions = Timetable.search(domain)
            student.timetable_ids = [(6, 0, sessions.ids)]
            student.timetable_count = len(sessions)

            holiday_domain = [
                ('active', '=', True),
                ('is_holiday', '=', True),
                '|',
                ('class_id', '=', False),
                '|',
                ('student_id', '=', student.id),
                ('student_ids', 'in', [student.id]),
            ]
            if student.class_id:
                holiday_domain = [
                    ('active', '=', True),
                    ('is_holiday', '=', True),
                    '|',
                    ('class_id', '=', False),
                    '|',
                    '|',
                    ('student_id', '=', student.id),
                    ('student_ids', 'in', [student.id]),
                    ('class_id', '=', student.class_id.id),
                ]
            student.holiday_count = Timetable.search_count(holiday_domain)

    def action_sync_subjects_from_class(self):
        """Populate or update student's weekly study subjects from class curriculum / teaching assignments and active timetable."""
        StudentSubject = self.env['school.student.subject']
        Timetable = self.env['school.timetable']
        for student in self:
            existing_by_sub = {rec.subject_id.id: rec for rec in student.study_subject_ids}

            # 1. Sync from Class Teaching Assignments
            if student.class_id:
                assignments = student.class_id.teaching_assignment_ids
                if assignments:
                    for asg in assignments:
                        if asg.subject_id.id in existing_by_sub:
                            rec = existing_by_sub[asg.subject_id.id]
                            rec.write({
                                'teacher_id': asg.teacher_id.id,
                                'weekly_hours': asg.weekly_hours,
                                'weekly_sessions': asg.weekly_sessions,
                                'class_id': student.class_id.id,
                            })
                        else:
                            new_rec = StudentSubject.create({
                                'student_id': student.id,
                                'class_id': student.class_id.id,
                                'subject_id': asg.subject_id.id,
                                'teacher_id': asg.teacher_id.id,
                                'weekly_hours': asg.weekly_hours,
                                'weekly_sessions': asg.weekly_sessions,
                                'subject_type': 'core',
                            })
                            existing_by_sub[asg.subject_id.id] = new_rec
                elif student.class_id.subject_ids:
                    for sub in student.class_id.subject_ids:
                        if sub.id not in existing_by_sub:
                            new_rec = StudentSubject.create({
                                'student_id': student.id,
                                'class_id': student.class_id.id,
                                'subject_id': sub.id,
                                'weekly_hours': 3.0,
                                'weekly_sessions': 2,
                                'subject_type': 'core',
                            })
                            existing_by_sub[sub.id] = new_rec

            # 2. Sync from Scheduled Timetable Sessions
            tt_domain = [('active', '=', True)]
            if student.class_id:
                tt_domain.extend([
                    '|',
                    '|',
                    ('student_id', '=', student.id),
                    ('student_ids', 'in', student.id),
                    '&',
                    ('student_id', '=', False),
                    ('class_id', '=', student.class_id.id),
                ])
            else:
                tt_domain.extend([
                    '|',
                    ('student_id', '=', student.id),
                    ('student_ids', 'in', student.id),
                ])
            sessions = Timetable.search(tt_domain)
            for sess in sessions:
                subs = sess.subject_ids or (sess.subject_id if sess.subject_id else self.env['school.subject'])
                duration = max(0.0, (sess.end_time or 0.0) - (sess.start_time or 0.0))
                for sub in subs:
                    if sub.id in existing_by_sub:
                        rec = existing_by_sub[sub.id]
                        if not rec.teacher_id and sess.teacher_id:
                            rec.teacher_id = sess.teacher_id.id
                    else:
                        new_rec = StudentSubject.create({
                            'student_id': student.id,
                            'class_id': student.class_id.id if student.class_id else (sess.class_id.id if sess.class_id else False),
                            'subject_id': sub.id,
                            'teacher_id': sess.teacher_id.id if sess.teacher_id else False,
                            'weekly_hours': duration or 2.0,
                            'weekly_sessions': 1,
                            'subject_type': 'core',
                        })
                        existing_by_sub[sub.id] = new_rec

            # 3. Always recompute timetable stats for all student subjects
            student.study_subject_ids._compute_timetable_stats()

    def action_manual_sync_subjects_from_class(self):
        self.ensure_one()
        if not self.class_id:
            raise UserError(_("This student is not assigned to any class."))
        self.action_sync_subjects_from_class()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Weekly Subjects Synchronized"),
                'message': _("Study plan synchronized with class '%s' (%d subjects).") % (
                    self.class_id.name, len(self.study_subject_ids)
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_study_subjects(self):
        self.ensure_one()
        return {
            'name': _("Weekly Study Subjects - %s") % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.subject',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {
                'default_student_id': self.id,
                'default_class_id': self.class_id.id if self.class_id else False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        students = super().create(vals_list)
        students._sync_year_payment_with_class()
        students.action_sync_subjects_from_class()
        return students

    def write(self, vals):
        res = super().write(vals)
        if 'class_id' in vals:
            self._sync_year_payment_with_class()
            self.action_sync_subjects_from_class()
        return res

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

    # ==================== STOP / CONTINUE STUDY ACTIONS ====================\
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

    @api.depends('attendance_ids', 'attendance_ids.status', 'attendance_ids.student_id')
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

    def action_recompute_academic_stats(self):
        """Manually trigger full academic & attendance recalculation (90% Exam + 10% Attendance)."""
        for rec in self:
            rec._compute_attendance_stats()
            rec._compute_grade_stats()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Academic Metrics Recalculated'),
                'message': _('Recalculated GPA and Average Score (90% Exam + 10% Attendance) successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

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

    def action_view_class_timetable(self):
        self.ensure_one()
        if not self.class_id:
            raise UserError(_("This student is not assigned to any class."))
        return {
            'name': _('Class Timetable - %s') % self.class_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': [('class_id', '=', self.class_id.id)],
            'context': {
                'default_class_id': self.class_id.id,
            },
        }

    def action_generate_certificate(self):
        self.ensure_one()
        is_student = (
            self.env.user.has_group('school_management.group_school_student')
            and not self.env.user.has_group('school_management.group_school_teacher')
            and not self.env.user.has_group('school_management.group_school_admin')
            and not self.env.is_admin()
        )
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
        certs = self.env['school.certificate'].sudo().generate_certificates(self, certificate_type='transcript')
        if not certs:
            return {'type': 'ir.actions.act_window_close'}
        is_student = (
            self.env.user.has_group('school_management.group_school_student')
            and not self.env.user.has_group('school_management.group_school_teacher')
            and not self.env.user.has_group('school_management.group_school_admin')
            and not self.env.is_admin()
            and not self.env.su
        )
        if is_student:
            unapproved = certs.filtered(lambda c: c.print_state != 'approved')
            if unapproved:
                first_unapproved = unapproved[0]
                return {
                    'name': _('Academic Transcript & Report Card'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'school.certificate',
                    'view_mode': 'form',
                    'res_id': first_unapproved.id,
                    'target': 'current',
                    'context': {'create': False, 'edit': False, 'delete': False},
                }
        if len(certs) == 1:
            return certs.action_print_transcript()
        return self.env.ref('school_management.action_report_school_transcript_student').report_action(self)

    def action_print_student_certificates(self):
        certs = self.env['school.certificate'].sudo().generate_certificates(self, certificate_type='completion')
        if not certs:
            return {'type': 'ir.actions.act_window_close'}
        is_student = (
            self.env.user.has_group('school_management.group_school_student')
            and not self.env.user.has_group('school_management.group_school_teacher')
            and not self.env.user.has_group('school_management.group_school_admin')
            and not self.env.is_admin()
            and not self.env.su
        )
        if is_student:
            unapproved = certs.filtered(lambda c: c.print_state != 'approved')
            if unapproved:
                first_unapproved = unapproved[0]
                return {
                    'name': _('Official Certificate'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'school.certificate',
                    'view_mode': 'form',
                    'res_id': first_unapproved.id,
                    'target': 'current',
                    'context': {'create': False, 'edit': False, 'delete': False},
                }
        if len(certs) == 1:
            return certs.action_print_certificate()
        return self.env.ref('school_management.action_report_school_certificate_student').report_action(self)

    def action_create_user(self):
        self.ensure_one()
        if not self.email:
            raise UserError(_('Please provide an email address for the student first.'))

        login = self.email.strip().lower()
        existing_user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        group_student = self.env.ref('school_management.group_school_student')
        group_internal = self.env.ref('base.group_user')
        group_portal = self.env.ref('base.group_portal', raise_if_not_found=False)
        action_home = self.env.ref('school_management.action_timetable', raise_if_not_found=False)

        # Set Default password After reset by admin
        default_pwd = 'password123'
        groups_to_add = [(4, group_student.id), (4, group_internal.id)]
        if group_portal:
            groups_to_add.append((3, group_portal.id))

        if existing_user:
            existing_user.sudo().write({
                'email': self.email,
                'name': self.name,
                'group_ids': groups_to_add,
                'action_id': action_home.id if action_home else False,
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
            partner_vals = {'name': self.name, 'email': self.email}
            if 'autopost_bills' in self.env['res.partner']._fields:
                partner_vals['autopost_bills'] = 'never'
            partner = self.env['res.partner'].sudo().create(partner_vals)
            new_user = self.env['res.users'].sudo().create({
                'name': self.name,
                'login': login,
                'email': self.email,
                'password': default_pwd,
                'partner_id': partner.id,
                'group_ids': [(6, 0, [group_student.id, group_internal.id])],
                'action_id': action_home.id if action_home else False,
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

    def action_print_payment_receipt(self):
        self.ensure_one()
        payment = self.year_payment_ids.filtered(lambda p: p.overall_status in ('paid', 'partial'))[:1]
        if payment:
            return payment.action_print_receipt()
        fee = self.fee_ids.filtered(lambda f: f.status in ('paid', 'partial'))[:1]
        if fee:
            return fee.action_print_receipt()
        if self.year_payment_ids:
            return self.year_payment_ids[0].action_print_receipt()
        if self.fee_ids:
            return self.fee_ids[0].action_print_receipt()
        raise UserError(_("No payment or fee records found for student %s.") % self.name)

    def _get_id_card_qr_payload(self):
        self.ensure_one()
        blood = dict(self._fields['blood_group'].selection).get(self.blood_group, 'N/A') if self.blood_group and self.blood_group != 'unknown' else 'N/A'
        school_name = self.env.company.name if (self.env.company.name and self.env.company.name != 'My Company') else 'Passerelles Numériques Cambodia'
        status_label = 'Active (Studying)' if self.study_status == 'studying' else 'Stopped'
        class_name = self.class_id.name if self.class_id else 'Unassigned'
        dob_str = str(self.date_of_birth) if self.date_of_birth else 'N/A'
        emergency = self.parent_phone or self.phone or 'N/A'
        return (
            f"STUDENT ID: {self.student_id or 'N/A'}\n"
            f"NAME: {self.name or 'N/A'}\n"
            f"CLASS: {class_name}\n"
            f"DOB: {dob_str}\n"
            f"BLOOD: {blood}\n"
            f"EMERGENCY: {emergency}\n"
            f"STATUS: {status_label}\n"
            f"INSTITUTION: {school_name}"
        )

    @api.depends('student_id', 'name', 'class_id', 'date_of_birth', 'blood_group', 'parent_phone', 'phone', 'study_status')
    def _compute_id_card_qr_code(self):
        import base64
        import io
        for rec in self:
            try:
                import qrcode
                payload = rec._get_id_card_qr_payload()
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=4,
                    border=2,
                )
                qr.add_data(payload)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                rec.id_card_qr_code = base64.b64encode(buf.getvalue())
            except Exception:
                rec.id_card_qr_code = False

    def _compute_feedback_counts(self):
        for rec in self:
            rec.teacher_feedback_count = self.env['school.feedback'].search_count([
                ('student_id', '=', rec.id),
                ('report_type', '=', 'teacher_to_student'),
                ('state', '!=', 'draft'),
            ])
            rec.teaching_report_count = self.env['school.feedback'].search_count([
                ('student_id', '=', rec.id),
                ('report_type', '=', 'student_to_teacher'),
            ])

    def action_view_teacher_feedback(self):
        self.ensure_one()
        return {
            'name': _("Teacher Feedback for %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.feedback',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id), ('report_type', '=', 'teacher_to_student'), ('state', '!=', 'draft')],
            'context': {'default_student_id': self.id, 'default_report_type': 'teacher_to_student'},
        }

    def action_view_teaching_reports(self):
        self.ensure_one()
        return {
            'name': _("Teaching Quality Reports by %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.feedback',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id), ('report_type', '=', 'student_to_teacher')],
            'context': {'default_student_id': self.id, 'default_report_type': 'student_to_teacher'},
        }

    def action_print_id_card(self):
        """Generate and print the official Student ID Card (with QR Code) PDF."""
        if self.env['school.certificate']._is_restricted_student():
            raise UserError(_('Access Denied: Student ID cards are official identification credentials and must be printed and issued by the School Administrator.'))
        return self.env.ref('school_management.action_report_student_id_card').report_action(self)

    def action_export_xlsx(self):
        ids = self.ids or self.env.context.get('active_ids') or []
        ids_str = ','.join(str(x) for x in ids) if ids else ''
        return {
            'type': 'ir.actions.act_url',
            'url': f'/school_management/export_report_xlsx?report_type=student&ids={ids_str}',
            'target': 'self',
        }

    @api.depends(
        'study_subject_ids',
        'study_subject_ids.weekly_hours',
        'study_subject_ids.weekly_sessions',
        'study_subject_ids.scheduled_hours',
        'study_subject_ids.teacher_id',
        'study_subject_ids.subject_id',
        'study_subject_ids.study_status',
        'study_subject_ids.active',
    )
    def _compute_study_stats(self):
        for rec in self:
            active_studies = rec.study_subject_ids.filtered(lambda s: s.active and s.study_status == 'active')
            rec.study_subject_count = len(active_studies)
            rec.total_weekly_study_hours = sum(active_studies.mapped('weekly_hours'))
            rec.total_weekly_study_sessions = sum(active_studies.mapped('weekly_sessions'))
            rec.total_scheduled_study_hours = sum(active_studies.mapped('scheduled_hours'))
            teachers = active_studies.mapped('teacher_id')
            rec.study_teacher_ids = [(6, 0, teachers.ids)]
            rec.study_teacher_count = len(teachers)
            subjects = active_studies.mapped('subject_id')
            rec.study_subject_all_ids = [(6, 0, subjects.ids)]

    def action_view_study_subjects(self):
        self.ensure_one()
        return {
            'name': _('Weekly Study Subjects - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.subject',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {
                'default_student_id': self.id,
                'default_class_id': self.class_id.id if self.class_id else False,
            },
        }

    def action_view_study_teachers(self):
        self.ensure_one()
        teachers = self.study_teacher_ids
        return {
            'name': _('Instructing Teachers - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.teacher',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', teachers.ids)],
        }

    def action_view_student_timetable(self):
        self.ensure_one()
        return self.action_view_timetable()

    def action_view_class_timetable(self):
        self.ensure_one()
        if not self.class_id:
            raise UserError(_("This student is not assigned to any class."))
        return self.class_id.action_view_timetable()

    def action_view_master_timetable(self):
        self.ensure_one()
        return {
            'name': _('Master Timetable & Calendar'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'context': {
                'search_default_filter_mon_fri': 1,
                'create': False,
            },
        }

    def action_view_holidays(self):
        self.ensure_one()
        holiday_domain = [
            ('active', '=', True),
            ('is_holiday', '=', True),
            '|',
            ('class_id', '=', False),
            '|',
            ('student_id', '=', self.id),
            ('student_ids', 'in', [self.id]),
        ]
        if self.class_id:
            holiday_domain = [
                ('active', '=', True),
                ('is_holiday', '=', True),
                '|',
                ('class_id', '=', False),
                '|',
                '|',
                ('student_id', '=', self.id),
                ('student_ids', 'in', [self.id]),
                ('class_id', '=', self.class_id.id),
            ]
        return {
            'name': _('My Study Holidays & Days Off - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': holiday_domain,
            'context': {
                'default_is_holiday': True,
                'default_class_id': self.class_id.id if self.class_id else False,
                'search_default_filter_holidays': 1,
            },
        }

    def action_open_assign_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enroll %s in Weekly Subjects') % self.name,
            'res_model': 'school.assign.subject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mode': 'student_enroll',
                'default_student_ids': [(6, 0, [self.id])],
                'default_class_id': self.class_id.id if self.class_id else False,
            }
        }

    @api.depends('permission_ids.state', 'permission_ids.duration_days')
    def _compute_permission_count(self):
        for rec in self:
            perms = rec.permission_ids
            rec.permission_count = len(perms)
            approved = perms.filtered(lambda p: p.state == 'approved')
            rec.permission_approved_count = len(approved)
            rec.permission_pending_count = len(perms.filtered(lambda p: p.state == 'draft'))
            rec.permission_total_days = sum(approved.mapped('duration_days'))

    def action_request_permission(self):
        self.ensure_one()
        return {
            'name': _('New Permission / Leave Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.permission',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_applicant_type': 'student',
                'default_student_id': self.id,
                'default_class_id': self.class_id.id if self.class_id else False,
            },
        }

    def action_view_permissions(self):
        self.ensure_one()
        return {
            'name': _('Permission Requests - %s') % (self.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'school.permission',
            'view_mode': 'list,kanban,calendar,form',
            'domain': [('student_id', '=', self.id)],
            'context': {
                'default_applicant_type': 'student',
                'default_student_id': self.id,
                'search_default_student_id': self.id,
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
