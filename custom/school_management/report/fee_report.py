from odoo import models
from .report_common import _fmt_number


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
