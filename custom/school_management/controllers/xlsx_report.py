# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import http, _
from odoo.http import request, content_disposition
from ..report.school_xlsx_report import SchoolXlsxReport


class SchoolXlsxExportController(http.Controller):

    @http.route('/school_management/export_report_xlsx', type='http', auth='user', methods=['GET'])
    def export_report_xlsx(self, report_type='fee', ids=None, date_from=None, date_to=None,
                           class_id=None, student_id=None, status=None, **kw):
        env = request.env
        parsed_ids = [int(x) for x in ids.split(',') if x.strip().isdigit()] if ids else None
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        domain = []
        desc_parts = []

        if parsed_ids:
            domain = [('id', 'in', parsed_ids)]
            desc_parts.append(f"Selected {len(parsed_ids)} records")
        else:
            if date_from:
                date_field = 'date' if report_type == 'attendance' else 'due_date'
                domain.append((date_field, '>=', date_from))
                desc_parts.append(f"From {date_from}")
            if date_to:
                date_field = 'date' if report_type == 'attendance' else 'due_date'
                domain.append((date_field, '<=', date_to))
                desc_parts.append(f"To {date_to}")
            if class_id and class_id.isdigit():
                domain.append(('class_id', '=', int(class_id)))
                cls_rec = env['school.class'].browse(int(class_id))
                if cls_rec.exists():
                    desc_parts.append(f"Class: {cls_rec.name}")
            if student_id and student_id.isdigit():
                domain.append(('student_id', '=', int(student_id)))
                stu_rec = env['school.student'].browse(int(student_id))
                if stu_rec.exists():
                    desc_parts.append(f"Student: {stu_rec.name}")
            if status and status != 'all':
                domain.append(('status', '=', status))
                desc_parts.append(f"Status: {status.upper()}")

        filter_desc = " | ".join(desc_parts) if desc_parts else "All Records"

        if report_type == 'fee':
            content = SchoolXlsxReport.generate_fee_report(env, domain=domain, filter_desc=filter_desc)
            filename = f"Fee_Invoices_{timestamp}.xlsx"
        elif report_type == 'year_payment':
            content = SchoolXlsxReport.generate_year_payment_report(env, domain=domain, filter_desc=filter_desc)
            filename = f"Tuition_Payments_{timestamp}.xlsx"
        elif report_type == 'attendance':
            content = SchoolXlsxReport.generate_attendance_report(env, domain=domain, filter_desc=filter_desc)
            filename = f"Attendance_Log_{timestamp}.xlsx"
        elif report_type == 'grade':
            content = SchoolXlsxReport.generate_grade_report(env, domain=domain, filter_desc=filter_desc)
            filename = f"Grades_Results_{timestamp}.xlsx"
        elif report_type == 'student':
            content = SchoolXlsxReport.generate_student_report(env, domain=domain, filter_desc=filter_desc)
            filename = f"Students_Master_Directory_{timestamp}.xlsx"
        elif report_type == 'class':
            content = SchoolXlsxReport.generate_class_report(env, domain=domain, filter_desc=filter_desc)
            filename = f"Classes_Overview_{timestamp}.xlsx"
        else:
            return request.not_found()

        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(filename)),
        ]
        return request.make_response(content, headers)
