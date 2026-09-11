from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolStudentAccount(models.Model):
    _inherit = 'school.student'

    grade_ids = fields.One2many('school.grade', 'student_id', string='Grades')
    grade_count = fields.Integer(string='Total Exams', compute='_compute_grade_stats')
    average_score = fields.Float(string='Average Score (%)', compute='_compute_grade_stats', digits=(5, 1))
    passed_exam_count = fields.Integer(string='Passed Exams', compute='_compute_grade_stats')
    failed_exam_count = fields.Integer(string='Failed Exams', compute='_compute_grade_stats')
    academic_performance = fields.Char(string='Overall Grade', compute='_compute_grade_stats')

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

    def open_grades(self):
        return self._open_records('grade', [('student_id', '=', self.id)])

    def open_enrollments(self):
        return self._open_records('enrollment', [('student_id', '=', self.id)])

    def open_major_enrollments(self):
        return self._open_records('major_enrollment', [('student_id', '=', self.id)])

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
        return self.env.ref('school_management.action_report_school_certificate').report_action(certs)

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
