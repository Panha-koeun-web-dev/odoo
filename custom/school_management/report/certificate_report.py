import re
from odoo import models
from odoo.tools import format_date
from odoo.tools.image import image_data_uri


class SchoolCertificateReport(models.AbstractModel):
    _name = 'report.school_management.certificate_report'
    _description = 'School Certificate Report'

    TYPE_TITLE = {
        'completion': 'Certificate of Completion',
        'achievement': 'Certificate of Achievement',
        'participation': 'Certificate of Participation',
    }

    def _accent_styles(self, hex_color):
        """Return per-element inline style strings for a custom accent color.
        Empty result means 'use the template theme'.
        """
        if not hex_color or not re.fullmatch(r'#[0-9a-fA-F]{6}', hex_color):
            return {}
        return {
            'school_name': 'color: %s;' % hex_color,
            'subtitle': 'color: %s;' % hex_color,
            'title': 'color: %s;' % hex_color,
            'student_name': 'color: %s;' % hex_color,
            'sep': 'color: %s;' % hex_color,
            'statement': 'color: %s;' % hex_color,
            'corners': 'border-color: %s;' % hex_color,
            'seal_ring': 'color: %s; border-color: %s;' % (hex_color, hex_color),
            'seal_star': 'border-color: %s;' % hex_color,
            'divider': 'border-color: %s;' % hex_color,
            'avg_chip': 'border-color: %s;' % hex_color,
        }

    def _get_certificate_docs(self, docids, data=None):
        data = data or {}
        cert_model = self.env['school.certificate']
        student_model = self.env['school.student']

        candidate_ids = docids or data.get('docids') or data.get('ids') or data.get('active_ids')
        active_model = data.get('active_model') or self.env.context.get('active_model')
        context_ids = self.env.context.get('active_ids') or self.env.context.get('active_id')

        if not candidate_ids and context_ids:
            candidate_ids = context_ids

        if isinstance(candidate_ids, int):
            candidate_ids = [candidate_ids]

        if candidate_ids and active_model == 'school.student':
            students = student_model.browse(candidate_ids).exists()
            return cert_model.generate_certificates(students)

        docs = cert_model.browse(candidate_ids or []).exists()
        if docs:
            return docs

        if active_model == 'school.student' and context_ids:
            if isinstance(context_ids, int):
                context_ids = [context_ids]
            students = student_model.browse(context_ids).exists()
            return cert_model.generate_certificates(students)

        return cert_model

    def _get_report_values(self, docids, data=None):
        common = self.env['school.report.common']
        docs = self._get_certificate_docs(docids, data=data)
        docids = docs.ids
        company = self.env.company.sudo()
        rows = []
        for rec in docs:
            stu = rec.student_id
            gender_label = dict(stu._fields['gender'].selection).get(stu.gender, stu.gender) if stu.gender else ''
            dob = ''
            if stu.date_of_birth:
                dob = format_date(self.env, stu.date_of_birth)
            study_start_date = format_date(self.env, stu.study_start_date) if stu.study_start_date else ''
            study_end_date = format_date(self.env, stu.study_end_date) if stu.study_end_date else ''
            study_period = stu.study_period or rec.academic_year or ''
            rows.append({
                'cert': rec,
                'cert_name': rec.name,
                'type_label': self.TYPE_TITLE.get(rec.certificate_type, rec.certificate_type),
                'student_name': stu.name,
                'student_code': stu.student_id,
                'class_name': stu.class_id.name or '',
                'majors': ', '.join(stu.major_enrollment_ids.filtered(
                    lambda e: e.status == 'enrolled').mapped('major_id.name')) or
                          ', '.join(stu.major_ids.mapped('name')),
                'academic_year': rec.academic_year,
                'study_start_date': study_start_date,
                'study_end_date': study_end_date,
                'study_period': study_period,
                'issue_date': format_date(self.env, rec.issue_date) if rec.issue_date else '',
                'reason': rec.reason or 'successfully completing the academic year',
                'template': rec.template,
                'avg_percentage': f'{rec.average_grade:g}%' if rec.average_grade else '',
                'has_avg': bool(rec.average_grade),
                'gender': gender_label,
                'dob': dob,
                'age': stu.age or '',
                'email': stu.email or '',
                'phone': stu.phone or '',
                'parent_name': stu.parent_name or '',
                'address': stu.address or '',
                'subject_count': rec.subject_count,
                'has_photo': bool(stu.photo),
                'photo_uri': image_data_uri(stu.photo) if stu.photo else '',
                'custom_title': rec.custom_title or '',
                'custom_prelude': rec.custom_prelude or '',
                'custom_statement': rec.custom_statement or '',
                'sign_one_name': rec.signatory_one_name or '',
                'sign_one_title': rec.signatory_one_title or '',
                'sign_two_name': rec.signatory_two_name or '',
                'sign_two_title': rec.signatory_two_title or '',
                'show_avg': rec.show_avg,
                'styles': self._accent_styles(rec.accent_color),
            })
        company_logo = common._company_logo_uri(company)
        return {
            'doc_ids': docids,
            'doc_model': 'school.certificate',
            'docs': docs,
            'company': company,
            'company_logo': company_logo,
            'has_company_logo': bool(company_logo),
            'generated_on': common._generated_on(),
            'rows': rows,
            'user_name': self.env.user.name,
        }
