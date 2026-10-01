from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import datetime


class SchoolCertificate(models.Model):
    _name = 'school.certificate'
    _description = 'Academic Transcript & Certificate Generator'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc, id desc'

    name = fields.Char(
        string='Document Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    certificate_type = fields.Selection([
        ('transcript', 'Official Academic Transcript & Report Card'),
        ('completion', 'Certificate of Completion'),
        ('appreciation', 'Certificate of Appreciation'),
        ('achievement', 'Certificate of Achievement'),
        ('excellence', 'Certificate of Academic Excellence'),
        ('attendance', 'Perfect Attendance Award'),
        ('custom', 'Custom Certificate'),
    ], string='Document Category', default='transcript', required=True)

    student_id = fields.Many2one('school.student', string='Student', required=True, tracking=True)
    student_code = fields.Char(string='Student ID', related='student_id.student_id', store=True, readonly=True)
    class_id = fields.Many2one('school.class', string='Class / Cohort', related='student_id.class_id', store=True, readonly=True)
    term_id = fields.Many2one('school.term', string='Term Reference', tracking=True)
    term = fields.Selection([
        ('term_1', 'Term 1 / Semester 1'),
        ('term_2', 'Term 2 / Semester 2'),
        ('term_3', 'Term 3 / Final Year'),
        ('semester_1', 'Semester 1'),
        ('semester_2', 'Semester 2'),
        ('final', 'Full Academic Year / Final'),
    ], string='Grading Period', default='final', required=True)

    academic_year = fields.Char(string='Academic Year', default=lambda self: f"{fields.Date.today().year}-{fields.Date.today().year + 1}")
    issue_date = fields.Date(string='Issue Date', default=fields.Date.today, required=True)

    template = fields.Selection([
        ('classic', 'Classic Crest (Traditional Gold / Navy)'),
        ('modern', 'Modern Clean (Minimalist Blue / Slate)'),
        ('ornate', 'Prestigious Honors (Ornate Borders / Bronze)'),
        ('minimal', 'Executive Report Format'),
    ], string='Visual Style', default='classic', required=True)

    # Content Options
    custom_title = fields.Char(string='Custom Title')
    custom_prelude = fields.Char(string='Prelude Text')
    custom_statement = fields.Char(string='Conferral Statement')
    reason = fields.Text(string='Reason / Achievement Details')
    accent_color = fields.Char(string='Theme Accent Color', default='#1a56db')
    show_avg = fields.Boolean(string='Display Overall Grade / GPA', default=True)

    # Signatories
    signatory_one_name = fields.Char(string='First Signatory', default='Academic Director')
    signatory_one_title = fields.Char(string='First Signatory Title', default='Director of Academic Affairs')
    signatory_two_name = fields.Char(string='Second Signatory', default='School Principal')
    signatory_two_title = fields.Char(string='Second Signatory Title', default='Head of Institution')

    # Academic & Transcript Metrics
    average_score = fields.Float(string='Final Percentage', compute='_compute_academic_performance', store=True, compute_sudo=True)
    gpa = fields.Float(string='Cumulative Term GPA', compute='_compute_academic_performance', store=True, compute_sudo=True)
    cumulative_gpa = fields.Float(string='Overall Career GPA', compute='_compute_academic_performance', store=True, compute_sudo=True)
    academic_standing = fields.Selection([
        ('distinction', 'Distinction (GPA >= 3.8)'),
        ('honors', 'High Honors (GPA >= 3.5)'),
        ('good', 'Good Academic Standing (GPA >= 3.0)'),
        ('satisfactory', 'Satisfactory (GPA >= 2.0)'),
        ('probation', 'Academic Warning / Probation (GPA < 2.0)'),
    ], string='Academic Honor', compute='_compute_academic_performance', store=True, compute_sudo=True)

    class_rank = fields.Integer(string='Class Standing / Rank', compute='_compute_cohort_rank', store=True, compute_sudo=True)
    total_class_students = fields.Integer(string='Total Students in Class', compute='_compute_cohort_rank', store=True, compute_sudo=True)

    # Attendance & Conduct
    attendance_rate = fields.Float(string='Term Attendance Rate (%)', compute='_compute_attendance_metrics', store=True, compute_sudo=True)
    present_days = fields.Integer(string='Days Present', compute='_compute_attendance_metrics', store=True, compute_sudo=True)
    absent_days = fields.Integer(string='Days Absent', compute='_compute_attendance_metrics', store=True, compute_sudo=True)
    late_days = fields.Integer(string='Days Late', compute='_compute_attendance_metrics', store=True, compute_sudo=True)

    # Credit Calculations
    total_credits = fields.Integer(string='Total Program Credits', default=30)
    earned_credits = fields.Integer(string='Earned Credits', compute='_compute_credit_units', store=True, compute_sudo=True)

    # Administrative & Faculty Details
    homeroom_teacher_id = fields.Many2one(
        'school.teacher',
        string='Homeroom Teacher / Advisor',
        compute='_compute_teachers',
        store=True,
        readonly=True,
    )
    principal_name = fields.Char(string='Principal / Head of School', default='Dr. Robert Sterling')
    general_remarks = fields.Text(string='Advisor & Board Remarks')

    # Student Profile Snapshot (Read-only for convenience)
    gender = fields.Selection(related='student_id.gender', string='Gender', readonly=True)
    date_of_birth = fields.Date(related='student_id.date_of_birth', string='Date of Birth', readonly=True)
    age = fields.Integer(related='student_id.age', string='Age', readonly=True)
    email = fields.Char(related='student_id.email', string='Email', readonly=True)
    phone = fields.Char(related='student_id.phone', string='Phone', readonly=True)
    parent_name = fields.Char(related='student_id.parent_name', string='Parent / Guardian', readonly=True)
    parent_phone = fields.Char(related='student_id.parent_phone', string='Parent Contact', readonly=True)
    address = fields.Text(related='student_id.address', string='Home Address', readonly=True)

    status = fields.Selection([
        ('draft', 'Draft / Unofficial'),
        ('issued', 'Official / Issued'),
    ], string='Status', default='draft')

    # ------------------ PRINT APPROVAL WORKFLOW ------------------
    print_state = fields.Selection([
        ('not_requested', 'Not Requested'),
        ('pending', 'Pending Admin Approval'),
        ('approved', 'Approved to Print'),
        ('rejected', 'Request Declined'),
    ], string='Print Approval Status', default='not_requested', copy=False)
    print_requested_date = fields.Date(string='Print Requested Date', readonly=True, copy=False)
    print_approved_by = fields.Many2one('res.users', string='Reviewed By', readonly=True, copy=False)
    print_approval_date = fields.Datetime(string='Approval Date', readonly=True, copy=False)
    print_rejection_reason = fields.Text(string='Rejection Reason', readonly=True, copy=False)

    can_request_print = fields.Boolean(
        string='Can Request Print',
        compute='_compute_print_permissions',
    )
    can_approve_print = fields.Boolean(
        string='Can Approve Print',
        compute='_compute_print_permissions',
    )
    can_print = fields.Boolean(
        string='Can Print Document',
        compute='_compute_print_permissions',
    )

    notes = fields.Text(string='Notes')

    _unique_certificate_number = models.Constraint(
        'unique(name)',
        'This document number already exists!',
    )

    def _is_restricted_student(self):
        """Return True if the current user is an authenticated student without administrative or teacher rights."""
        return (
            self.env.user.has_group('school_management.group_school_student')
            and not self.env.user.has_group('school_management.group_school_teacher')
            and not self.env.user.has_group('school_management.group_school_admin')
            and not self.env.is_admin()
            and not self.env.su
        )

    def _can_review_print_requests(self):
        """Return True if current user is an admin or teacher capable of reviewing print requests."""
        return (
            self.env.user.has_group('school_management.group_school_teacher')
            or self.env.user.has_group('school_management.group_school_admin')
            or self.env.is_admin()
            or self.env.su
        )

    @api.depends('print_state')
    def _compute_print_permissions(self):
        is_student = self._is_restricted_student()
        is_reviewer = self._can_review_print_requests()
        for rec in self:
            rec.can_request_print = is_student and (rec.print_state in ('not_requested', 'rejected'))
            rec.can_approve_print = is_reviewer and (rec.print_state == 'pending')
            rec.can_print = (not is_student) or (rec.print_state == 'approved')

    @api.onchange('term_id')
    def _onchange_term_id(self):
        if self.term_id:
            if self.term_id.term_number in ('term_1', 'term_2', 'term_3'):
                self.term = self.term_id.term_number
            if self.term_id.academic_year:
                self.academic_year = self.term_id.academic_year

    @api.depends('student_id.average_score', 'student_id.grade_ids.percentage')
    def _compute_academic_performance(self):
        for rec in self:
            if not rec.student_id:
                rec.average_score = 0.0
                rec.gpa = 0.0
                rec.cumulative_gpa = 0.0
                rec.academic_standing = 'probation'
                continue

            student = rec.student_id
            rec.average_score = student.average_score or 0.0

            # Compute scale 4.0 GPA
            scores = student.grade_ids.mapped('percentage')
            if scores:
                gpa_points = []
                for s in scores:
                    if s >= 90:
                        gpa_points.append(4.0)
                    elif s >= 80:
                        gpa_points.append(3.0 + (s - 80) * 0.1)
                    elif s >= 70:
                        gpa_points.append(2.0 + (s - 70) * 0.1)
                    elif s >= 60:
                        gpa_points.append(1.0 + (s - 60) * 0.1)
                    else:
                        gpa_points.append(0.0)
                rec.gpa = round(sum(gpa_points) / len(gpa_points), 2)
            else:
                rec.gpa = student.gpa or 0.0

            rec.cumulative_gpa = rec.gpa

            # Determine academic honor designation
            if rec.gpa >= 3.8:
                rec.academic_standing = 'distinction'
            elif rec.gpa >= 3.5:
                rec.academic_standing = 'honors'
            elif rec.gpa >= 3.0:
                rec.academic_standing = 'good'
            elif rec.gpa >= 2.0:
                rec.academic_standing = 'satisfactory'
            else:
                rec.academic_standing = 'probation'

    @api.depends('student_id', 'student_id.class_id')
    def _compute_cohort_rank(self):
        for rec in self:
            if rec.student_id and rec.student_id.class_id:
                cohort_students = self.env['school.student'].search([
                    ('class_id', '=', rec.student_id.class_id.id),
                    ('active', '=', True),
                ], order='average_score desc, id asc')
                rec.total_class_students = len(cohort_students)
                ids = cohort_students.ids
                if rec.student_id.id in ids:
                    rec.class_rank = ids.index(rec.student_id.id) + 1
                else:
                    rec.class_rank = 1
            else:
                rec.class_rank = 1
                rec.total_class_students = 1

    @api.depends('student_id.attendance_rate', 'student_id.present_count', 'student_id.absent_count', 'student_id.late_count')
    def _compute_attendance_metrics(self):
        for rec in self:
            if rec.student_id:
                rec.attendance_rate = rec.student_id.attendance_rate or 0.0
                rec.present_days = rec.student_id.present_count or 0
                rec.absent_days = rec.student_id.absent_count or 0
                rec.late_days = rec.student_id.late_count or 0
            else:
                rec.attendance_rate = 100.0
                rec.present_days = 0
                rec.absent_days = 0
                rec.late_days = 0

    @api.depends('student_id.grade_ids.result', 'student_id.study_subject_ids')
    def _compute_credit_units(self):
        for rec in self:
            if not rec.student_id:
                rec.earned_credits = 0
                continue
            passed_subjects = rec.student_id.grade_ids.filtered(lambda g: g.result == 'pass').mapped('subject_id')
            # Each subject carries credits (default 3 if undefined)
            credits = sum(s.credits if hasattr(s, 'credits') and s.credits else 3 for s in passed_subjects)
            rec.earned_credits = min(credits, rec.total_credits) if rec.total_credits else credits

    @api.depends('student_id', 'student_id.class_id', 'student_id.class_id.teacher_id')
    def _compute_teachers(self):
        for rec in self:
            if rec.student_id and rec.student_id.class_id and rec.student_id.class_id.teacher_id:
                rec.homeroom_teacher_id = rec.student_id.class_id.teacher_id
            elif not rec.homeroom_teacher_id:
                rec.homeroom_teacher_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                cert_type = vals.get('certificate_type', 'transcript')
                code = vals.get('student_code')
                if not code and vals.get('student_id'):
                    st = self.env['school.student'].browse(vals['student_id'])
                    code = st.student_id or 'STU'
                year = fields.Date.today().year

                seq_code = 'school.transcript' if cert_type == 'transcript' else 'school.certificate'
                seq_val = self.env['ir.sequence'].next_by_code(seq_code)
                if not seq_val:
                    prefix = 'TR' if cert_type == 'transcript' else 'CERT'
                    existing_count = self.search_count([('certificate_type', '=', cert_type)])
                    seq_val = f"{prefix}-{year}-{existing_count + 1:04d}"
                vals['name'] = seq_val

            # Auto-populate design metadata based on certificate type
            t = vals.get('certificate_type', 'transcript')
            if t == 'excellence' and not vals.get('custom_title'):
                vals['custom_title'] = 'Certificate of Academic Excellence'
                vals['custom_prelude'] = 'This is to proudly certify that'
                vals['custom_statement'] = 'has demonstrated exceptional academic distinction and scholarly excellence'
                vals['accent_color'] = '#b45309'  # Warm gold
            elif t == 'achievement' and not vals.get('custom_title'):
                vals['custom_title'] = 'Certificate of Outstanding Achievement'
                vals['custom_prelude'] = 'In recognition of superior academic dedication'
                vals['custom_statement'] = 'has attained an outstanding record of scholastic achievement'
                vals['accent_color'] = '#15803d'  # Emerald green
            elif t == 'appreciation' and not vals.get('custom_title'):
                vals['custom_title'] = 'Certificate of Appreciation'
                vals['custom_prelude'] = 'With heartfelt gratitude and sincere honor'
                vals['custom_statement'] = 'for exemplary engagement, leadership, and community contribution'
                vals['accent_color'] = '#6d28d9'  # Regal purple
            elif t == 'attendance' and not vals.get('custom_title'):
                vals['custom_title'] = 'Honor Roll: Perfect Attendance'
                vals['custom_prelude'] = 'Presented to'
                vals['custom_statement'] = 'for maintaining an impeccable 100% attendance record throughout the academic term'
                vals['accent_color'] = '#0284c7'  # Sky cyan
            elif t == 'completion' and not vals.get('custom_title'):
                vals['custom_title'] = 'Certificate of Program Completion'
                vals['custom_prelude'] = 'This official document certifies that'
                vals['custom_statement'] = 'has fulfilled all required curriculum hours, coursework, and examinations'
                vals['accent_color'] = '#1e40af'  # Institutional navy

        records = super().create(vals_list)
        for rec in records:
            if rec.student_id and rec.student_id.class_id and rec.student_id.class_id.teacher_id:
                rec.homeroom_teacher_id = rec.student_id.class_id.teacher_id
        return records

    def write(self, vals):
        if self._is_restricted_student():
            # Allow students to only initiate a print request via action_request_print
            allowed_fields = {'print_state', 'print_requested_date', 'print_rejection_reason'}
            if not set(vals.keys()).issubset(allowed_fields):
                raise UserError(_('Access Denied: Students are not permitted to modify certificate records.'))
        return super().write(vals)

    def unlink(self):
        if self._is_restricted_student():
            raise UserError(_('Access Denied: Students are not permitted to delete transcripts or certificates.'))
        return super().unlink()

    def action_request_print(self):
        """Student submits a request to the admin/teacher to print the transcript or certificate."""
        self.ensure_one()
        if self.print_state == 'pending':
            raise UserError(_('A print approval request is already pending review.'))
        if self.print_state == 'approved':
            raise UserError(_('Your print request has already been approved! You can print your document now.'))

        self.sudo().write({
            'print_state': 'pending',
            'print_requested_date': fields.Date.today(),
            'print_rejection_reason': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Print Request Submitted'),
                'message': _('Your request to print this document has been sent to admin for approval. You will be able to print once approved.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_approve_print(self):
        """Administrator or Teacher approves the student's request to print."""
        if not self._can_review_print_requests():
            raise UserError(_('Access Denied: Only administrators or teachers can approve print requests.'))
        for rec in self:
            rec.sudo().write({
                'print_state': 'approved',
                'print_approved_by': self.env.user.id,
                'print_approval_date': fields.Datetime.now(),
                'print_rejection_reason': False,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Print Request Approved'),
                'message': _('The document print request has been approved. The student can now print the document.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reject_print(self, reason=None):
        """Open the reject wizard or decline the print request directly with reason."""
        if not self._can_review_print_requests():
            raise UserError(_('Access Denied: Only administrators or teachers can decline print requests.'))
        self.ensure_one()
        if not reason:
            return {
                'name': _('Decline Print Request'),
                'type': 'ir.actions.act_window',
                'res_model': 'school.certificate.reject.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_certificate_id': self.id},
            }
        self.sudo().write({
            'print_state': 'rejected',
            'print_approved_by': self.env.user.id,
            'print_approval_date': fields.Datetime.now(),
            'print_rejection_reason': reason,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Print Request Declined'),
                'message': _('The document print request was declined.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_reset_print_request(self):
        """Reset print approval state back to not_requested (Teacher/Admin only)."""
        if not self._can_review_print_requests():
            raise UserError(_('Access Denied: Only administrators or teachers can reset print requests.'))
        for rec in self:
            rec.sudo().write({
                'print_state': 'not_requested',
                'print_requested_date': False,
                'print_approved_by': False,
                'print_approval_date': False,
                'print_rejection_reason': False,
            })
        return True

    def action_recompute_metrics(self):
        self._compute_academic_performance()
        self._compute_cohort_rank()
        self._compute_attendance_metrics()
        self._compute_credit_units()
        self.sudo()._compute_teachers()
        return True

    def action_draft(self):
        self.status = 'draft'

    @api.model
    def generate_certificates(self, students, certificate_type='transcript', term='final', academic_year=None):
        """Bulk generator factory for class-level or student-level certificates."""
        if not academic_year:
            academic_year = f"{fields.Date.today().year}-{fields.Date.today().year + 1}"
        created = self.env['school.certificate']
        for student in students:
            # Check existing to prevent duplicates
            existing = self.search([
                ('student_id', '=', student.id),
                ('certificate_type', '=', certificate_type),
                ('term', '=', term),
                ('academic_year', '=', academic_year),
            ], limit=1)
            if existing:
                existing.action_recompute_metrics()
                existing.sudo()._compute_teachers()
                created |= existing
                continue

            vals = {
                'student_id': student.id,
                'certificate_type': certificate_type,
                'term': term,
                'academic_year': academic_year,
                'issue_date': fields.Date.today(),
                'status': 'draft',
            }
            new_cert = self.create(vals)
            new_cert.action_recompute_metrics()
            new_cert.sudo()._compute_teachers()
            created |= new_cert
        return created

    def action_view_student_certificates(self):
        """Open all certificates/transcripts for the current context."""
        certs = self
        if not certs and self.env.context.get('active_ids'):
            certs = self.browse(self.env.context.get('active_ids'))
        return {
            'name': _('Academic Credentials & Certificates'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.certificate',
            'view_mode': 'list,form',
            'domain': [('id', 'in', certs.ids)],
            'target': 'current',
        }

    def _check_student_print_allowed(self):
        """Ensure students cannot print unless their request has been approved by admin."""
        if not self._is_restricted_student():
            return
        for rec in self:
            if rec.print_state != 'approved':
                raise UserError(_(
                    'You cannot print this document yet. '
                    'You must first submit a request to the admin and wait for approval.'
                ))

    def action_print_transcript(self):
        """Print the official A4 portrait Academic Transcript & Term Report Card."""
        if not self:
            return {'type': 'ir.actions.act_window_close'}
        self._check_student_print_allowed()
        return self.env.ref('school_management.action_report_school_transcript').report_action(self)

    def action_print_certificate(self):
        """Print the classical landscape ornamental certificate."""
        if not self:
            return {'type': 'ir.actions.act_window_close'}
        self._check_student_print_allowed()
        return self.env.ref('school_management.action_report_school_certificate').report_action(
            self, data={'certificate_type': self.mapped('certificate_type')})

    def action_smart_print(self):
        """Smart print according to credential type."""
        self.ensure_one()
        self._check_student_print_allowed()
        if self.certificate_type == 'transcript':
            return self.action_print_transcript()
        return self.action_print_certificate()

    def action_issue(self):
        """Mark the transcript or certificate as issued."""
        if self._is_restricted_student():
            raise UserError(_('Access Denied: Students cannot modify official document status.'))
        for rec in self:
            rec.status = 'issued'
