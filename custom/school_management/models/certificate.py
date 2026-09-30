from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolCertificate(models.Model):
    _name = 'school.certificate'
    _inherit = ['school.state.notification']
    _description = 'Academic Transcript & Certificate'
    _order = 'issue_date desc, id desc'

    name = fields.Char(string='Document Number', required=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('school.certificate') or 'TR/2026/0001')
    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    student_code = fields.Char(string='Student ID', related='student_id.student_id', store=True)
    class_id = fields.Many2one(related='student_id.class_id', string='Class', store=True)
    study_start_date = fields.Date(related='student_id.study_start_date', string='Study Start Date', store=True)
    study_end_date = fields.Date(related='student_id.study_end_date', string='Study End Date', store=True)
    study_period = fields.Char(related='student_id.study_period', string='Student Study Period', store=True)

    certificate_type = fields.Selection([
        ('transcript', 'Academic Transcript / Term Report Card'),
        ('completion', 'Certificate of Completion'),
        ('achievement', 'Certificate of Achievement'),
        ('participation', 'Certificate of Participation'),
    ], string='Credential Type', required=True, default='transcript')

    term_id = fields.Many2one(
        'school.term',
        string='Academic Term',
        help="Linked academic term record",
    )

    term = fields.Selection([
        ('semester_1', 'Semester 1'),
        ('semester_2', 'Semester 2'),
        ('term_1', 'Term 1'),
        ('term_2', 'Term 2'),
        ('term_3', 'Term 3'),
        ('final', 'Full Academic Year / Final'),
    ], string='Term / Semester', default='term_1', required=True)

    academic_year = fields.Char(string='Academic Year', default='2025-2026')
    issue_date = fields.Date(string='Issue Date', required=True, default=fields.Date.today)

    # ------------------ ACADEMIC METRICS (REPORT CARD & TRANSCRIPT) ------------------
    gpa = fields.Float(
        string='Term GPA (4.0 Scale)',
        compute='_compute_academic_metrics',
        store=True,
        digits=(3, 2),
        help='Grade Point Average calculated on standard 4.0 scale (90% Exam + 10% Attendance).',
    )
    cumulative_gpa = fields.Float(
        string='Cumulative GPA',
        compute='_compute_academic_metrics',
        store=True,
        digits=(3, 2),
        help='Overall cumulative GPA across all completed coursework.',
    )
    class_rank = fields.Char(
        string='Class Rank',
        compute='_compute_academic_metrics',
        store=True,
        help='Student rank position among active classmates (e.g. Rank 1 of 24).',
    )
    class_rank_number = fields.Integer(
        string='Rank Position',
        compute='_compute_academic_metrics',
        store=True,
    )
    total_students_in_class = fields.Integer(
        string='Cohort Size',
        compute='_compute_academic_metrics',
        store=True,
    )
    total_credits = fields.Integer(
        string='Attempted Credits',
        compute='_compute_academic_metrics',
        store=True,
        help='Total credit hours attempted during this period.',
    )
    earned_credits = fields.Integer(
        string='Earned Credits',
        compute='_compute_academic_metrics',
        store=True,
        help='Total credit hours successfully passed.',
    )
    academic_standing = fields.Selection([
        ('distinction', "President's Honors / Distinction (GPA >= 3.80)"),
        ('honors', "Dean's Honors (GPA 3.50 - 3.79)"),
        ('good', 'Good Academic Standing (GPA 3.00 - 3.49)'),
        ('satisfactory', 'Satisfactory (GPA 2.00 - 2.99)'),
        ('probation', 'Academic Warning / Probation (GPA < 2.00)'),
        ('pending', 'Pending Evaluation / No Grades Recorded'),
    ], string='Academic Standing', compute='_compute_academic_metrics', store=True)

    # ------------------ ATTENDANCE METRICS ------------------
    attendance_rate = fields.Float(
        string='Attendance Rate (%)',
        compute='_compute_academic_metrics',
        store=True,
        digits=(5, 1),
    )
    present_days = fields.Integer(
        string='Present Days',
        compute='_compute_academic_metrics',
        store=True,
    )
    absent_days = fields.Integer(
        string='Absent Days',
        compute='_compute_academic_metrics',
        store=True,
    )
    late_days = fields.Integer(
        string='Late Days',
        compute='_compute_academic_metrics',
        store=True,
    )

    # ------------------ SIGNATURES & EVALUATION ------------------
    homeroom_teacher_id = fields.Many2one(
        'school.teacher',
        string='Homeroom Teacher / Advisor',
        compute='_compute_teachers',
        store=True,
        readonly=False,
    )
    principal_name = fields.Char(
        string='Principal / Academic Dean',
        default='Dr. Robert Sterling, Academic Dean',
    )
    general_remarks = fields.Text(
        string='Faculty / Evaluator Remarks',
        default='Demonstrates commendable commitment to academic excellence, active classroom engagement, and continuous improvement.',
    )

    # ------------------ CLASSICAL CERTIFICATE FIELDS ------------------
    reason = fields.Char(string='Reason / Purpose', default='successfully completing the academic curriculum')
    template = fields.Selection([
        ('elegant', 'Elegant Gold'),
        ('classic', 'Classic Navy'),
        ('modern', 'Modern Teal'),
    ], string='Template Style', default='elegant')
    custom_title = fields.Char(
        string='Custom Title',
        help='Overrides the automatic title, e.g. "Certificate of Distinction". Leave empty to use default.',
    )
    custom_prelude = fields.Char(
        string='Prelude Text',
        help='Opening line, e.g. "This is to proudly certify that". Leave empty for the default.',
    )
    custom_statement = fields.Char(
        string='Statement Text',
        help='Line after the student name, e.g. "having successfully completed the requirements of".',
    )
    signatory_one_name = fields.Char(string='First Signatory Name')
    signatory_one_title = fields.Char(string='First Signatory Title', default='Homeroom Teacher')
    signatory_two_name = fields.Char(string='Second Signatory Name')
    signatory_two_title = fields.Char(string='Second Signatory Title', default='Principal / Director')
    show_avg = fields.Boolean(string='Show Academic Average', default=True)
    accent_color = fields.Char(
        string='Accent Color',
        help='Accent hex color used on the title, name, seal and lines. Leave empty to use the template theme.',
    )

    # ------------------ DERIVED STUDENT PROFILE ------------------
    email = fields.Char(string='Email', related='student_id.email')
    phone = fields.Char(string='Phone', related='student_id.phone')
    gender = fields.Selection(string='Gender', related='student_id.gender')
    date_of_birth = fields.Date(string='Date of Birth', related='student_id.date_of_birth')
    age = fields.Integer(string='Age', related='student_id.age')
    parent_name = fields.Char(string='Parent/Guardian', related='student_id.parent_name')
    parent_phone = fields.Char(string='Parent Phone', related='student_id.parent_phone')
    address = fields.Text(string='Address', related='student_id.address')
    average_grade = fields.Float(
        string='Average Grade (%)',
        compute='_compute_average_grade',
        store=True,
        help="Overall weighted academic average (90% Exam + 10% Attendance).",
    )
    subject_count = fields.Integer(
        string='Number of Subjects',
        compute='_compute_average_grade',
        store=True,
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
    ], string='Status', default='draft')
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

    @api.onchange('term_id')
    def _onchange_term_id(self):
        if self.term_id:
            if self.term_id.term_number in ('term_1', 'term_2', 'term_3'):
                self.term = self.term_id.term_number
            if self.term_id.academic_year:
                self.academic_year = self.term_id.academic_year

    @api.depends('student_id.average_score', 'student_id.grade_ids.percentage')
    def _compute_average_grade(self):
        for rec in self.sudo():
            rec.subject_count = len(rec.student_id.grade_ids)
            rec.average_grade = rec.student_id.average_score

    @api.depends('student_id', 'student_id.class_id', 'student_id.class_id.teacher_id')
    def _compute_teachers(self):
        for rec in self.sudo():
            if rec.student_id and rec.student_id.class_id and rec.student_id.class_id.teacher_id:
                rec.homeroom_teacher_id = rec.student_id.class_id.teacher_id
            elif not rec.homeroom_teacher_id:
                rec.homeroom_teacher_id = False

    @api.depends(
        'student_id',
        'student_id.grade_ids',
        'student_id.grade_ids.marks_obtained',
        'student_id.grade_ids.total_marks',
        'student_id.grade_ids.grade_letter',
        'student_id.grade_ids.result',
        'student_id.grade_ids.percentage',
        'student_id.grade_ids.subject_id.credits',
        'student_id.class_id',
        'student_id.class_id.student_ids',
        'student_id.attendance_ids.status',
        'student_id.attendance_rate',
        'student_id.attendance_count',
        'student_id.present_count',
        'student_id.absent_count',
        'student_id.late_count',
        'term_id',
    )
    def _compute_academic_metrics(self):
        grade_pts_map = {
            'a+': 4.0, 'a': 4.0, 'a-': 3.7,
            'b+': 3.3, 'b': 3.0, 'b-': 2.7,
            'c+': 2.3, 'c': 2.0, 'c-': 1.7,
            'd': 1.0, 'f': 0.0,
        }

        for rec in self.sudo():
            stu = rec.student_id
            if not stu:
                rec.gpa = 0.0
                rec.cumulative_gpa = 0.0
                rec.class_rank = 'N/A'
                rec.class_rank_number = 0
                rec.total_students_in_class = 0
                rec.total_credits = 0
                rec.earned_credits = 0
                rec.academic_standing = 'pending'
                rec.attendance_rate = 0.0
                rec.present_days = 0
                rec.absent_days = 0
                rec.late_days = 0
                continue

            all_grades = stu.grade_ids
            term_grades = all_grades
            if rec.term_id:
                tg = all_grades.filtered(lambda g: g.exam_id.term_id == rec.term_id)
                if tg:
                    term_grades = tg

            # 1. Term GPA & Credits Calculation
            term_creds = 0
            term_earned_creds = 0
            term_pts = 0.0
            if term_grades:
                for g in term_grades:
                    creds = g.subject_id.credits or 3
                    gp = grade_pts_map.get(g.grade_letter)
                    if gp is None:
                        pct = g.percentage or (g.marks_obtained / g.total_marks * 100 if g.total_marks else 0.0)
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
                    term_creds += creds
                    if gp > 0.0 and g.result != 'fail':
                        term_earned_creds += creds
                    term_pts += (gp * creds)

                term_exam_gpa = (term_pts / term_creds) if term_creds else 0.0
                if stu.attendance_count > 0:
                    att_gpa = (stu.attendance_rate / 100.0) * 4.0
                else:
                    att_gpa = term_exam_gpa
                rec.gpa = round((term_exam_gpa * 0.90) + (att_gpa * 0.10), 2)
                rec.total_credits = term_creds
                rec.earned_credits = term_earned_creds
            else:
                rec.gpa = 0.0
                rec.total_credits = 0
                rec.earned_credits = 0

            # 2. Cumulative GPA (across all completed coursework)
            cum_creds = 0
            cum_pts = 0.0
            if all_grades:
                for g in all_grades:
                    creds = g.subject_id.credits or 3
                    gp = grade_pts_map.get(g.grade_letter)
                    if gp is None:
                        pct = g.percentage or (g.marks_obtained / g.total_marks * 100 if g.total_marks else 0.0)
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
                    cum_creds += creds
                    cum_pts += (gp * creds)

                cum_exam_gpa = (cum_pts / cum_creds) if cum_creds else 0.0
                if stu.attendance_count > 0:
                    att_gpa = (stu.attendance_rate / 100.0) * 4.0
                else:
                    att_gpa = cum_exam_gpa
                rec.cumulative_gpa = round((cum_exam_gpa * 0.90) + (att_gpa * 0.10), 2)
            else:
                rec.cumulative_gpa = 0.0

            # 3. Academic Standing
            if not term_grades and not all_grades:
                rec.academic_standing = 'pending'
            elif rec.gpa >= 3.80:
                rec.academic_standing = 'distinction'
            elif rec.gpa >= 3.50:
                rec.academic_standing = 'honors'
            elif rec.gpa >= 3.00:
                rec.academic_standing = 'good'
            elif rec.gpa >= 2.00:
                rec.academic_standing = 'satisfactory'
            else:
                rec.academic_standing = 'probation'

            # 4. Class Rank Calculation
            if stu.class_id:
                classmates = stu.class_id.student_ids.filtered(lambda s: s.active and s.study_status == 'studying')
                rec.total_students_in_class = len(classmates) or 1
                sorted_peers = sorted(classmates, key=lambda s: (s.gpa, s.average_score), reverse=True)
                try:
                    rank_idx = sorted_peers.index(stu) + 1
                except ValueError:
                    rank_idx = 1
                rec.class_rank_number = rank_idx
                rec.class_rank = f"Rank {rank_idx} of {rec.total_students_in_class}"
            else:
                rec.total_students_in_class = 0
                rec.class_rank_number = 0
                rec.class_rank = "N/A"

            # 5. Attendance Statistics
            attendances = stu.attendance_ids
            if attendances:
                total_att = len(attendances)
                present = sum(1 for a in attendances if a.status in ('present', 'late', 'excused'))
                absent = sum(1 for a in attendances if a.status == 'absent')
                late = sum(1 for a in attendances if a.status == 'late')
                rec.present_days = present
                rec.absent_days = absent
                rec.late_days = late
                rec.attendance_rate = round((present / total_att * 100), 1) if total_att else 0.0
            else:
                rec.present_days = stu.present_count
                rec.absent_days = stu.absent_count
                rec.late_days = stu.late_count
                rec.attendance_rate = round(stu.attendance_rate, 1) if stu.attendance_count > 0 else 0.0

    @api.onchange('student_id')
    def _onchange_student_id_set_academic_year(self):
        for rec in self:
            if rec.student_id and rec.student_id.study_period:
                rec.academic_year = rec.student_id.study_period
            if rec.student_id and rec.student_id.class_id and rec.student_id.class_id.teacher_id:
                rec.homeroom_teacher_id = rec.student_id.class_id.teacher_id

    def _get_state_email_template(self):
        return 'school_management.email_template_certificate_issued'

    def _get_state_change_recipients(self):
        return self.email or self.student_id.parent_email

    def _get_transcript_courses(self):
        """Extract all real course lines with grades, marks, and remarks for this student."""
        self.ensure_one()
        stu = self.student_id
        courses = []
        grade_pts_map = {
            'a+': 4.0, 'a': 4.0, 'a-': 3.7,
            'b+': 3.3, 'b': 3.0, 'b-': 2.7,
            'c+': 2.3, 'c': 2.0, 'c-': 1.7,
            'd': 1.0, 'f': 0.0,
        }

        # Filter grades by term if a specific term is selected
        all_grades = stu.grade_ids
        if self.term_id:
            tg = all_grades.filtered(lambda g: g.exam_id.term_id == self.term_id)
            if tg:
                all_grades = tg

        for idx, g in enumerate(all_grades):
            subj = g.subject_id
            if not subj:
                continue
            creds = subj.credits or 3
            pct = g.percentage or (g.marks_obtained / g.total_marks * 100 if g.total_marks else 0.0)
            gp = grade_pts_map.get(g.grade_letter)
            if gp is None:
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

            let = (g.grade_letter or 'a').upper()
            res = g.result or ('pass' if pct >= 40 else 'fail')

            # Build clear subject and exam display title
            course_name = subj.name
            if g.exam_id and g.exam_id.name and g.exam_id.name != subj.name:
                course_name = f"{subj.name} ({g.exam_id.name})"

            courses.append({
                'index': idx + 1,
                'code': subj.code or f"SUB-{subj.id:03d}",
                'name': course_name,
                'department': dict(subj._fields['department'].selection).get(subj.department, 'Core') if subj.department else 'Core',
                'course_type': dict(subj._fields['course_type'].selection).get(subj.course_type, 'Core') if subj.course_type else 'Core',
                'credits': creds,
                'marks_obtained': f"{g.marks_obtained:.1f}" if g.marks_obtained else f"{pct:.1f}",
                'total_marks': int(g.total_marks or 100),
                'percentage': f"{pct:.1f}",
                'grade_letter': let,
                'grade_point': f"{gp:.2f}",
                'quality_points': f"{gp * creds:.2f}",
                'result': res,
                'result_label': 'PASS' if res == 'pass' else 'FAIL',
                'remarks': g.remarks or ('Exemplary mastery' if pct >= 85 else 'Satisfactory completion' if res == 'pass' else 'Needs improvement'),
            })

        return courses

    @api.model_create_multi
    def create(self, vals_list):
        if self._is_restricted_student():
            raise UserError(_('Access Denied: Students are not permitted to create transcripts or certificates.'))
        return super().create(vals_list)

    def write(self, vals):
        if self._is_restricted_student():
            raise UserError(_('Access Denied: Students are not permitted to edit transcripts or certificates.'))
        return super().write(vals)

    def unlink(self):
        if self._is_restricted_student():
            raise UserError(_('Access Denied: Students are not permitted to delete transcripts or certificates.'))
        return super().unlink()

    def action_recompute_metrics(self):
        """Action button to manually trigger metric recalculation."""
        if self._is_restricted_student():
            return self.action_print_transcript()
        self.sudo()._compute_academic_metrics()
        self.sudo()._compute_average_grade()
        self.sudo()._compute_teachers()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Metrics Recalculated'),
                'message': _('GPA, Class Rank, and Attendance have been refreshed successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def generate_certificates(self, students, **extra):
        """Generate certificate or transcript records for the given students."""
        if isinstance(students, list):
            students = self.env['school.student'].browse(students)
        students = students.filtered('active')
        if not students:
            return self.env['school.certificate']

        ctype = extra.get('certificate_type') or 'transcript'
        term = extra.get('term') or 'term_1'
        generated = self.env['school.certificate']
        for stud in students:
            year = extra.get('academic_year') or stud.study_period or '2025-2026'
            existing = self.sudo().search([
                ('student_id', '=', stud.id),
                ('certificate_type', '=', ctype),
                ('academic_year', '=', year),
                ('term', '=', term),
            ], limit=1)
            if existing:
                existing.sudo()._compute_academic_metrics()
                existing.sudo()._compute_average_grade()
                existing.sudo()._compute_teachers()
                generated |= existing
                continue
            new_cert = self.sudo().create({
                'student_id': stud.id,
                'certificate_type': ctype,
                'term': term,
                'academic_year': year,
                'issue_date': extra.get('issue_date') or fields.Date.today(),
                'status': 'issued',
                'notes': extra.get('notes'),
            })
            new_cert.sudo()._compute_academic_metrics()
            new_cert.sudo()._compute_average_grade()
            new_cert.sudo()._compute_teachers()
            generated |= new_cert
        return generated

    @api.model
    def generate_certificates_for_all(self):
        """Generate Academic Transcripts / Report Cards for every active student."""
        students = self.env['school.student'].search([('active', '=', True)])
        certs = self.generate_certificates(students, certificate_type='transcript')
        if not certs:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _('Generated Student Transcripts & Certificates'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.certificate',
            'view_mode': 'list,form',
            'domain': [('id', 'in', certs.ids)],
            'target': 'current',
        }

    def action_print_transcript(self):
        """Print the official A4 portrait Academic Transcript & Term Report Card."""
        if not self:
            return {'type': 'ir.actions.act_window_close'}
        return self.env.ref('school_management.action_report_school_transcript').report_action(self)

    def action_print_certificate(self):
        """Print the classical landscape ornamental certificate."""
        if not self:
            return {'type': 'ir.actions.act_window_close'}
        return self.env.ref('school_management.action_report_school_certificate').report_action(
            self, data={'certificate_type': self.mapped('certificate_type')})

    def action_smart_print(self):
        """Smart print according to credential type."""
        self.ensure_one()
        if self.certificate_type == 'transcript':
            return self.action_print_transcript()
        return self.action_print_certificate()

    def action_issue(self):
        """Mark the transcript or certificate as issued."""
        if self._is_restricted_student():
            raise UserError(_('Access Denied: Students cannot modify official document status.'))
        for rec in self:
            rec.status = 'issued'
            if not rec.issue_date:
                rec.issue_date = fields.Date.today()
        return True

    def action_draft(self):
        """Revert the transcript or certificate back to draft."""
        if self._is_restricted_student():
            raise UserError(_('Access Denied: Students cannot modify official document status.'))
        for rec in self:
            rec.status = 'draft'
        return True
