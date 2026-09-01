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
