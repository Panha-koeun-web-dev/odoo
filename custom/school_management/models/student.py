from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

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
    notes = fields.Text(string='Notes')

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

    def open_attendance(self):
        return _open_records(self, 'attendance', [('student_id', '=', self.id)])

    def open_grades(self):
        return _open_records(self, 'grade', [('student_id', '=', self.id)])

    def open_fees(self):
        return _open_records(self, 'fee', [('student_id', '=', self.id)])

    def open_enrollments(self):
        return _open_records(self, 'enrollment', [('student_id', '=', self.id)])

    def open_major_enrollments(self):
        return _open_records(self, 'major_enrollment', [('student_id', '=', self.id)])

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
