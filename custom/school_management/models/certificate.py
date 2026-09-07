from odoo import models, fields, api, _


class SchoolCertificate(models.Model):
    _name = 'school.certificate'
    _inherit = ['school.state.notification']
    _description = 'Student Certificate'
    _order = 'issue_date desc, id desc'

    name = fields.Char(string='Certificate Number', required=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('school.certificate') or 'CERT')
    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    student_code = fields.Char(string='Student ID', related='student_id.student_id', store=True)
    class_id = fields.Many2one(related='student_id.class_id', string='Class', store=True)
    study_start_date = fields.Date(related='student_id.study_start_date', string='Study Start Date', store=True)
    study_end_date = fields.Date(related='student_id.study_end_date', string='Study End Date', store=True)
    study_period = fields.Char(related='student_id.study_period', string='Student Study Period', store=True)
    certificate_type = fields.Selection([
        ('completion', 'Certificate of Completion'),
        ('achievement', 'Certificate of Achievement'),
        ('participation', 'Certificate of Participation'),
    ], string='Certificate Type', required=True, default='completion')
    academic_year = fields.Char(string='Academic Year', default='2025-2026')
    issue_date = fields.Date(string='Issue Date', required=True, default=fields.Date.today)
    reason = fields.Char(string='Reason / Purpose', default='successfully completing the academic year')
    template = fields.Selection([
        ('elegant', 'Elegant Gold'),
        ('classic', 'Classic Navy'),
        ('modern', 'Modern Teal'),
    ], string='Template Style', default='elegant')
    custom_title = fields.Char(
        string='Custom Title',
        help='Overrides the automatic title, e.g. "Certificate of Distinction". Leave empty to use the certificate type.',
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
    signatory_one_title = fields.Char(string='First Signatory Title', default='Principal')
    signatory_two_name = fields.Char(string='Second Signatory Name')
    signatory_two_title = fields.Char(string='Second Signatory Title', default='Director')
    show_avg = fields.Boolean(string='Show Academic Average', default=True)
    accent_color = fields.Char(
        string='Accent Color',
        help='Accent hex color used on the title, name, seal and lines. Leave empty to use the template theme.',
    )

    # ---- Derived from the linked student, so the certificate always reflects the real profile ----
    email = fields.Char(string='Email', related='student_id.email')
    phone = fields.Char(string='Phone', related='student_id.phone')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', related='student_id.gender')
    date_of_birth = fields.Date(string='Date of Birth', related='student_id.date_of_birth')
    age = fields.Integer(string='Age', related='student_id.age')
    parent_name = fields.Char(string='Parent/Guardian', related='student_id.parent_name')
    parent_phone = fields.Char(string='Parent Phone', related='student_id.parent_phone')
    address = fields.Text(string='Address', related='student_id.address')
    average_grade = fields.Float(
        string='Average Grade (%)',
        compute='_compute_average_grade',
        store=True,
        help='Average of the student\'s grade percentages.',
    )
    subject_count = fields.Integer(
        string='Number of Subjects',
        compute='_compute_average_grade',
        store=True,
    )

    @api.depends('student_id.grade_ids.percentage')
    def _compute_average_grade(self):
        for rec in self:
            grades = rec.student_id.grade_ids.mapped('percentage')
            rec.subject_count = len(grades)
            rec.average_grade = round(sum(grades) / len(grades), 1) if grades else 0.0

    @api.onchange('student_id')
    def _onchange_student_id_set_academic_year(self):
        for rec in self:
            if rec.student_id and rec.student_id.study_period:
                rec.academic_year = rec.student_id.study_period

    status = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
    ], string='Status', default='draft')
    notes = fields.Text(string='Notes')

    _unique_certificate_number = models.Constraint(
        'unique(name)',
        'This certificate number already exists!',
    )

    def _get_state_email_template(self):
        return 'school_management.email_template_certificate_issued'

    def _get_state_change_recipients(self):
        return self.email or self.student_id.parent_email

    @api.model
    def generate_certificates(self, students, **extra):
        """Generate certificate records for the given students (ids or records).
        Already-existing certificates for the same student/type/year are skipped.
        """
        if isinstance(students, list):
            students = self.env['school.student'].browse(students)
        students = students.filtered('active')
        if not students:
            return self.env['school.certificate']

        ctype = extra.get('certificate_type') or 'completion'
        generated = self.env['school.certificate']
        for stud in students:
            year = extra.get('academic_year') or stud.study_period or self.default_get(['academic_year']).get('academic_year')
            existing = self.search([
                ('student_id', '=', stud.id),
                ('certificate_type', '=', ctype),
                ('academic_year', '=', year),
            ], limit=1)
            if existing:
                generated |= existing
                continue
            generated |= self.create({
                'student_id': stud.id,
                'certificate_type': ctype,
                'academic_year': year,
                'issue_date': extra.get('issue_date') or fields.Date.today(),
                'status': 'issued',
                'notes': extra.get('notes'),
            })
        return generated

    @api.model
    def generate_certificates_for_all(self):
        """Generate certificates for every active student."""
        students = self.env['school.student'].search([('active', '=', True)])
        certs = self.generate_certificates(students)
        if not certs:
            return {
                'type': 'ir.actions.act_window_close',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Certificates'),
            'res_model': 'school.certificate',
            'view_mode': 'list,form',
            'domain': [('id', 'in', certs.ids)],
            'context': dict(self.env.context),
        }

    def action_print_certificate(self):
        if not self:
            return {
                'type': 'ir.actions.act_window_close',
            }
        return self.env.ref('school_management.action_report_school_certificate').report_action(
            self, data={'certificate_type': self.mapped('certificate_type')})
