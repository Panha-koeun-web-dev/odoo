import base64
from pathlib import Path

from odoo import models, fields
from odoo.tools import format_date, format_datetime
from odoo.tools.image import image_data_uri


def _fmt_number(value):
    return '{:,.2f}'.format(value or 0.0)


class SchoolReportCommon(models.AbstractModel):
    _name = 'school.report.common'
    _description = 'Common helpers for School Reports'

    def _format_date(self, value):
        return format_date(self.env, value) if value else ''

    def _format_datetime(self, value):
        return format_datetime(self.env, value) if value else ''

    def _format_number(self, value):
        return _fmt_number(value)

    def _generated_on(self):
        return format_datetime(self.env, fields.Datetime.now())

    def _company_logo_uri(self, company):
        # Return a data URI for a real company logo only. Odoo ships a default
        # "Your logo" placeholder inside `company.logo`; `uses_default_logo`
        # tells us whether a real logo has been configured, so we never print
        # the placeholder.
        if company.logo and not company.uses_default_logo:
            return image_data_uri(company.logo)
        return False

    def _static_image_uri(self, rel_path):
        # Build an absolute data URI for a static image bundled with the module
        # so it renders reliably in offline PDF rendering (wkhtmltopdf).
        module_root = Path(__file__).resolve().parent.parent
        img_path = module_root / rel_path
        if img_path.exists():
            return image_data_uri(base64.b64encode(img_path.read_bytes()))
        return False

    def _selection_label(self, model_name, field_name, value):
        field = self.env[model_name]._fields.get(field_name)
        if field and field.selection and value:
            return dict(field.selection).get(value, value)
        return value


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
        import re
        if not hex_color or not re.fullmatch('#[0-9a-fA-F]{6}', hex_color):
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
        from odoo.tools import format_date
        from odoo.tools.image import image_data_uri as _our_idu
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
                'photo_uri': _our_idu(stu.photo) if stu.photo else '',
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


class SchoolFeeReport(models.AbstractModel):
    _name = 'report.school_management.fee_report'
    _description = 'School Fee Report'

    def _get_report_values(self, docids, data=None):
        common = self.env['school.report.common']
        docs = self.env['school.fee'].browse(docids)
        company = self.env.company.sudo()
        fee_rows = [{
            'fee_id': rec.id,
            'student_name': rec.student_id.name,
            'student_id': rec.student_id.student_id,
            'class_name': rec.class_id.name,
            'fee_type': common._selection_label('school.fee', 'fee_type', rec.fee_type),
            'amount': rec.amount,
            'paid_amount': rec.paid_amount,
            'balance': rec.balance,
            'status': common._selection_label('school.fee', 'status', rec.status),
            'status_value': rec.status,
            'due_date': common._format_date(rec.due_date),
            'paid_date': common._format_date(rec.paid_date),
            'payment_method': common._selection_label('school.fee', 'payment_method', rec.payment_method),
            'receipt_number': rec.receipt_number,
            'notes': rec.notes,
        } for rec in docs]
        company_logo = common._company_logo_uri(company)
        return {
            'doc_ids': docids,
            'doc_model': 'school.fee',
            'docs': docs,
            'company': company,
            'company_logo': company_logo,
            'has_company_logo': bool(company_logo),
            'background_image': common._static_image_uri('static/src/img/image.png'),
            'address': company.partner_id,
            'generated_on': common._generated_on(),
            'fee_rows': fee_rows,
            'format_number': common._format_number,
            'format_datetime': common._format_datetime,
            'total_amount': _fmt_number(sum(docs.mapped('amount'))),
            'total_paid': _fmt_number(sum(docs.mapped('paid_amount'))),
            'total_balance': _fmt_number(sum(docs.mapped('balance'))),
            'total_fees': len(docs),
        }


class SchoolAttendanceReport(models.AbstractModel):
    _name = 'report.school_management.attendance_report'
    _description = 'School Attendance Report'

    def _get_report_values(self, docids, data=None):
        common = self.env['school.report.common']
        docs = self.env['school.attendance'].browse(docids)
        attendance_rows = [{
            'student_name': rec.student_id.name,
            'student_id': rec.student_id.student_id,
            'class_name': rec.class_id.name,
            'date': common._format_date(rec.date),
            'status': common._selection_label('school.attendance', 'status', rec.status),
            'status_value': rec.status,
            'notes': rec.notes,
        } for rec in docs]
        status_counts = {}
        for status, _label in docs._fields['status'].selection:
            status_counts[status] = len(docs.filtered(lambda d: d.status == status))
        return {
            'doc_ids': docids,
            'doc_model': 'school.attendance',
            'docs': docs,
            'company': self.env.company.sudo(),
            'generated_on': common._generated_on(),
            'attendance_rows': attendance_rows,
            'format_number': common._format_number,
            'format_datetime': common._format_datetime,
            'status_counts': status_counts,
            'total_records': len(docs),
        }
