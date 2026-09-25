from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError
from markupsafe import Markup, escape


class SchoolFeedback(models.Model):
    _name = 'school.feedback'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'School Feedback & Academic Report'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )

    report_type = fields.Selection([
        ('student_to_teacher', 'Teaching Quality Report (Student → Admin)'),
        ('teacher_to_student', 'Student Feedback & Progress (Teacher → Student & Admin)'),
    ], string='Report Type', required=True, default='student_to_teacher', tracking=True)

    title = fields.Char(
        string='Report Title / Subject',
        required=True,
        tracking=True,
    )

    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        required=True,
        tracking=True,
    )

    # -------------------------------------------------------------
    # Participants
    # -------------------------------------------------------------
    @api.model
    def _default_student_id(self):
        if self.env.context.get('default_student_id'):
            return self.env.context.get('default_student_id')
        student = self.env['school.student'].search([('user_id', '=', self.env.uid)], limit=1)
        return student.id if student else False

    @api.model
    def _default_teacher_id(self):
        if self.env.context.get('default_teacher_id'):
            return self.env.context.get('default_teacher_id')
        teacher = self.env['school.teacher'].search([('user_id', '=', self.env.uid)], limit=1)
        return teacher.id if teacher else False

    student_id = fields.Many2one(
        'school.student',
        string='Student',
        required=True,
        default=_default_student_id,
        tracking=True,
        ondelete='cascade',
    )
    student_name = fields.Char(related='student_id.name', string='Student Name', readonly=True)
    student_code = fields.Char(related='student_id.student_id', string='Student ID', readonly=True)

    teacher_id = fields.Many2one(
        'school.teacher',
        string='Teacher',
        required=True,
        default=_default_teacher_id,
        tracking=True,
        ondelete='cascade',
    )
    teacher_name = fields.Char(related='teacher_id.name', string='Teacher Name', readonly=True)

    class_id = fields.Many2one(
        'school.class',
        string='Class',
        tracking=True,
    )
    subject_id = fields.Many2one(
        'school.subject',
        string='Subject / Course',
        tracking=True,
    )
    academic_year = fields.Char(
        string='Academic Period',
        compute='_compute_academic_year',
        store=True,
        readonly=False,
    )

    # -------------------------------------------------------------
    # Direction 1: Student -> Teacher Evaluation Ratings
    # -------------------------------------------------------------
    rating_teaching = fields.Selection([
        ('1', '⭐ 1 - Needs Significant Improvement'),
        ('2', '⭐⭐ 2 - Below Average'),
        ('3', '⭐⭐⭐ 3 - Satisfactory / Good'),
        ('4', '⭐⭐⭐⭐ 4 - Very Good'),
        ('5', '⭐⭐⭐⭐⭐ 5 - Excellent & Clear'),
    ], string='Teaching Clarity & Explanation', tracking=True)

    rating_punctuality = fields.Selection([
        ('1', '⭐ 1 - Frequently Late / Absent'),
        ('2', '⭐⭐ 2 - Sometimes Late'),
        ('3', '⭐⭐⭐ 3 - Usually On Time'),
        ('4', '⭐⭐⭐⭐ 4 - Highly Punctual'),
        ('5', '⭐⭐⭐⭐⭐ 5 - Always Punctual & Prepared'),
    ], string='Teacher Punctuality & Readiness', tracking=True)

    rating_support = fields.Selection([
        ('1', '⭐ 1 - Unresponsive / Dismissive'),
        ('2', '⭐⭐ 2 - Limited Support'),
        ('3', '⭐⭐⭐ 3 - Helpful when Asked'),
        ('4', '⭐⭐⭐⭐ 4 - Highly Supportive & Engaging'),
        ('5', '⭐⭐⭐⭐⭐ 5 - Exceptional Mentorship'),
    ], string='Engagement & Student Support', tracking=True)

    # -------------------------------------------------------------
    # Direction 2: Teacher -> Student Feedback Ratings
    # -------------------------------------------------------------
    academic_performance = fields.Selection([
        ('excellent', 'A - Outstanding Academic Mastery'),
        ('good', 'B - Consistent & Good Grasp of Material'),
        ('satisfactory', 'C - Meets Minimum Standards'),
        ('needs_improvement', 'D/F - Struggling / Requires Tutoring'),
    ], string='Academic Progress & Comprehension', tracking=True)

    behavior_conduct = fields.Selection([
        ('exemplary', 'Exemplary - Role Model'),
        ('good', 'Good - Respectful & Cooperative'),
        ('fair', 'Fair - Occasional Disruptions / Distractions'),
        ('needs_attention', 'Needs Attention - Persistent Disciplinary Issues'),
    ], string='Class Conduct & Attitude', tracking=True)

    assignment_completion = fields.Selection([
        ('always', 'Always Submits Quality Homework On Time'),
        ('mostly', 'Mostly Submits On Time with Good Effort'),
        ('inconsistent', 'Inconsistent / Incomplete Homework'),
        ('rarely', 'Rarely Submits Assignments'),
    ], string='Homework & Assignment Discipline', tracking=True)

    # -------------------------------------------------------------
    # Overall Assessment & Narrative
    # -------------------------------------------------------------
    rating_overall = fields.Selection([
        ('1', '⭐ 1 - Poor / Serious Concern'),
        ('2', '⭐⭐ 2 - Fair / Room for Growth'),
        ('3', '⭐⭐⭐ 3 - Good / Satisfactory'),
        ('4', '⭐⭐⭐⭐ 4 - Very Good / Commendable'),
        ('5', '⭐⭐⭐⭐⭐ 5 - Exceptional / Top Performance'),
    ], string='Overall Assessment', tracking=True)

    strengths = fields.Text(
        string='Strengths & Commendations',
    )
    areas_for_improvement = fields.Text(
        string='Areas for Improvement / Growth Opportunities',
    )
    content = fields.Text(
        string='Detailed Observations & Remarks',
    )
    action_plan = fields.Text(
        string='Recommended Action Plan / Guidance',
    )

    # -------------------------------------------------------------
    # Administration Oversight & Decision
    # -------------------------------------------------------------
    is_confidential = fields.Boolean(
        string='Confidential to Administration',
        default=True,
        help="If enabled on student reports, the teacher will not see the student's identity or evaluation, ensuring unbiased reporting to school leadership.",
    )
    admin_notes = fields.Text(
        string='Administrative Internal Notes',
        help="Internal remarks, follow-up meetings, or decisions taken by School Administration.",
    )
    admin_response = fields.Text(
        string='Official Administration Response',
        help="Formal reply or acknowledgment from the Administration communicated to the author.",
    )
    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        readonly=True,
        tracking=True,
    )
    reviewed_date = fields.Datetime(
        string='Review Date',
        readonly=True,
    )

    # -------------------------------------------------------------
    # Workflow State
    # -------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to Administration'),
        ('under_review', 'Under Administrative Review'),
        ('reviewed', 'Reviewed & Actioned'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    # -------------------------------------------------------------
    # UI Helpers
    # -------------------------------------------------------------
    is_student_user = fields.Boolean(compute='_compute_user_role')
    is_teacher_user = fields.Boolean(compute='_compute_user_role')
    is_admin_user = fields.Boolean(compute='_compute_user_role')

    def _compute_user_role(self):
        is_admin = self.env.user.has_group('school_management.group_school_admin')
        is_teacher = self.env.user.has_group('school_management.group_school_teacher') and not is_admin
        is_student = self.env.user.has_group('school_management.group_school_student') and not is_teacher and not is_admin
        for rec in self:
            rec.is_admin_user = is_admin
            rec.is_teacher_user = is_teacher
            rec.is_student_user = is_student

    @api.depends('student_id', 'class_id')
    def _compute_academic_year(self):
        for rec in self:
            if rec.student_id and rec.student_id.study_period:
                rec.academic_year = rec.student_id.study_period
            elif rec.class_id and hasattr(rec.class_id, 'payment_year') and rec.class_id.payment_year:
                rec.academic_year = rec.class_id.payment_year
            else:
                rec.academic_year = f"{fields.Date.today().year}-{fields.Date.today().year + 1}"

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            if self.student_id.class_id:
                self.class_id = self.student_id.class_id
            if self.student_id.study_period:
                self.academic_year = self.student_id.study_period

    @api.onchange('teacher_id')
    def _onchange_teacher_id(self):
        if self.teacher_id and self.teacher_id.subject_ids:
            if not self.subject_id or self.subject_id not in self.teacher_id.subject_ids:
                self.subject_id = self.teacher_id.subject_ids[:1].id

    # -------------------------------------------------------------
    # Sequence & CRUD
    # -------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('school.feedback') or 'REP/2026/0001'
                vals['name'] = seq
        return super().create(vals_list)

    def write(self, vals):
        user = self.env.user
        if user.has_group('school_management.group_school_student') and not user.has_group('school_management.group_school_admin'):
            allowed_system_keys = {'message_follower_ids', 'activity_ids', 'message_ids'}
            user_keys = set(vals.keys()) - allowed_system_keys
            if user_keys:
                for rec in self:
                    if rec.report_type == 'teacher_to_student':
                        raise AccessError(_("Students cannot modify feedback provided by teachers."))
                    if rec.state != 'draft':
                        raise AccessError(_("You cannot modify a teaching report once it has been submitted to Administration."))
        return super().write(vals)

    # -------------------------------------------------------------
    # Workflow Actions
    # -------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if not rec.title:
                raise UserError(_("Please provide a title/subject for this report before submitting."))
            if not rec.content and not rec.strengths and not rec.areas_for_improvement:
                raise UserError(_("Please fill in the report observations, strengths, or areas for improvement."))

            rec.write({'state': 'submitted'})
            
            # Post notification in chatter
            author_role = _("Student") if rec.report_type == 'student_to_teacher' else _("Teacher")
            author_name = rec.student_id.name if rec.report_type == 'student_to_teacher' else rec.teacher_id.name
            type_label = dict(rec._fields['report_type'].selection).get(rec.report_type) or ""
            msg = Markup("<strong>%s Report Submitted</strong> by %s (%s).<br/>Title: %s") % (
                escape(type_label),
                escape(author_name or ""),
                escape(author_role),
                escape(rec.title or ""),
            )
            rec.message_post(body=msg, subtype_xmlid='mail.mt_note')

    def action_start_review(self):
        for rec in self:
            rec.write({
                'state': 'under_review',
                'reviewed_by': self.env.user.id,
            })
            rec.message_post(
                body=_("Report is now under administrative review by %s.") % self.env.user.name,
                subtype_xmlid='mail.mt_note'
            )

    def action_mark_reviewed(self):
        for rec in self:
            rec.write({
                'state': 'reviewed',
                'reviewed_by': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })
            if rec.admin_response:
                response_note = Markup("<br/><strong>Admin Remarks:</strong> %s") % escape(rec.admin_response)
            else:
                response_note = Markup("")
            msg = Markup("Report has been officially reviewed and resolved by Administration.%s") % response_note
            rec.message_post(
                body=msg,
                subtype_xmlid='mail.mt_comment'
            )

    def action_reset_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})
            rec.message_post(body=_("Report reset to Draft status."), subtype_xmlid='mail.mt_note')

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancelled'})
            rec.message_post(body=_("Report cancelled."), subtype_xmlid='mail.mt_note')
