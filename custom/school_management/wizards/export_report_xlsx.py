# -*- coding: utf-8 -*-
import base64
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..report.school_xlsx_report import SchoolXlsxReport


class SchoolReportExportXlsxWizard(models.TransientModel):
    _name = 'school.report.export.xlsx.wizard'
    _description = 'Export School Reports to Excel (XLSX)'

    report_type = fields.Selection([
        ('fee', 'Student Fee & Financial Invoices'),
        ('year_payment', 'Annual Student Tuition & Payments'),
        ('attendance', 'Student Attendance Log & Performance'),
        ('grade', 'Examination Grades & Academic Results'),
        ('student', 'Student Master Directory & Profiles'),
        ('class', 'Class Directory & Enrollment Capacity'),
    ], string='Report Type', required=True, default='fee')

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    class_id = fields.Many2one('school.class', string='Class Filter')
    student_id = fields.Many2one('school.student', string='Student Filter')
    academic_year = fields.Char(string='Academic Year')

    fee_status = fields.Selection([
        ('all', 'All Statuses'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('partial', 'Partial'),
    ], string='Fee Status', default='all')

    payment_status = fields.Selection([
        ('all', 'All Statuses'),
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='all')

    attendance_status = fields.Selection([
        ('all', 'All Statuses'),
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ], string='Attendance Status', default='all')

    grade_result = fields.Selection([
        ('all', 'All Results'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Exam Result', default='all')

    student_status = fields.Selection([
        ('all', 'All Statuses'),
        ('enrolled', 'Enrolled'),
        ('graduated', 'Graduated'),
        ('stopped', 'Stopped'),
    ], string='Enrollment Status', default='all')

    state = fields.Selection([
        ('choose', 'Choose Filters'),
        ('get', 'File Ready'),
    ], default='choose', string='Wizard State')

    file_data = fields.Binary(string='Generated Spreadsheet', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)
    record_count = fields.Integer(string='Matching Records', compute='_compute_record_count')

    @api.depends('report_type', 'date_from', 'date_to', 'class_id', 'student_id',
                 'academic_year', 'fee_status', 'payment_status', 'attendance_status',
                 'grade_result', 'student_status')
    def _compute_record_count(self):
        for rec in self:
            domain, _desc = rec._build_domain_and_desc()
            model_map = {
                'fee': 'school.fee',
                'year_payment': 'school.student.year.payment',
                'attendance': 'school.attendance',
                'grade': 'school.grade',
                'student': 'school.student',
                'class': 'school.class',
            }
            model_name = model_map.get(rec.report_type)
            if model_name:
                rec.record_count = self.env[model_name].search_count(domain)
            else:
                rec.record_count = 0

    def _build_domain_and_desc(self):
        self.ensure_one()
        domain = []
        desc_parts = []

        if self.report_type == 'fee':
            if self.date_from:
                domain.append(('due_date', '>=', self.date_from))
                desc_parts.append(f"From {self.date_from}")
            if self.date_to:
                domain.append(('due_date', '<=', self.date_to))
                desc_parts.append(f"To {self.date_to}")
            if self.class_id:
                domain.append(('class_id', '=', self.class_id.id))
                desc_parts.append(f"Class: {self.class_id.name}")
            if self.student_id:
                domain.append(('student_id', '=', self.student_id.id))
                desc_parts.append(f"Student: {self.student_id.name}")
            if self.fee_status and self.fee_status != 'all':
                domain.append(('status', '=', self.fee_status))
                desc_parts.append(f"Status: {self.fee_status.upper()}")

        elif self.report_type == 'year_payment':
            if self.class_id:
                domain.append(('class_id', '=', self.class_id.id))
                desc_parts.append(f"Class: {self.class_id.name}")
            if self.student_id:
                domain.append(('student_id', '=', self.student_id.id))
                desc_parts.append(f"Student: {self.student_id.name}")
            if self.academic_year:
                domain.append(('year', 'ilike', self.academic_year.strip()))
                desc_parts.append(f"Year: {self.academic_year.strip()}")
            if self.payment_status and self.payment_status != 'all':
                domain.append(('overall_status', '=', self.payment_status))
                desc_parts.append(f"Status: {self.payment_status.upper()}")

        elif self.report_type == 'attendance':
            if self.date_from:
                domain.append(('date', '>=', self.date_from))
                desc_parts.append(f"From {self.date_from}")
            if self.date_to:
                domain.append(('date', '<=', self.date_to))
                desc_parts.append(f"To {self.date_to}")
            if self.class_id:
                domain.append(('class_id', '=', self.class_id.id))
                desc_parts.append(f"Class: {self.class_id.name}")
            if self.student_id:
                domain.append(('student_id', '=', self.student_id.id))
                desc_parts.append(f"Student: {self.student_id.name}")
            if self.attendance_status and self.attendance_status != 'all':
                domain.append(('status', '=', self.attendance_status))
                desc_parts.append(f"Status: {self.attendance_status.upper()}")

        elif self.report_type == 'grade':
            if self.class_id:
                domain.append(('class_id', '=', self.class_id.id))
                desc_parts.append(f"Class: {self.class_id.name}")
            if self.student_id:
                domain.append(('student_id', '=', self.student_id.id))
                desc_parts.append(f"Student: {self.student_id.name}")
            if self.grade_result and self.grade_result != 'all':
                domain.append(('result', '=', self.grade_result))
                desc_parts.append(f"Result: {self.grade_result.upper()}")

        elif self.report_type == 'student':
            if self.class_id:
                domain.append(('class_id', '=', self.class_id.id))
                desc_parts.append(f"Class: {self.class_id.name}")
            if self.student_status and self.student_status != 'all':
                domain.append(('study_status', '=', self.student_status))
                desc_parts.append(f"Status: {self.student_status.upper()}")

        elif self.report_type == 'class':
            if self.academic_year:
                domain.append(('payment_year', 'ilike', self.academic_year.strip()))
                desc_parts.append(f"Year: {self.academic_year.strip()}")

        filter_desc = " | ".join(desc_parts) if desc_parts else "All Records"
        return domain, filter_desc

    def action_export_xlsx(self):
        self.ensure_one()
        domain, filter_desc = self._build_domain_and_desc()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if self.report_type == 'fee':
            content = SchoolXlsxReport.generate_fee_report(self.env, domain=domain, filter_desc=filter_desc)
            filename = f"Fee_Invoices_Report_{timestamp}.xlsx"
        elif self.report_type == 'year_payment':
            content = SchoolXlsxReport.generate_year_payment_report(self.env, domain=domain, filter_desc=filter_desc)
            filename = f"Tuition_Payments_Report_{timestamp}.xlsx"
        elif self.report_type == 'attendance':
            content = SchoolXlsxReport.generate_attendance_report(self.env, domain=domain, filter_desc=filter_desc)
            filename = f"Attendance_Report_{timestamp}.xlsx"
        elif self.report_type == 'grade':
            content = SchoolXlsxReport.generate_grade_report(self.env, domain=domain, filter_desc=filter_desc)
            filename = f"Grades_Results_Report_{timestamp}.xlsx"
        elif self.report_type == 'student':
            content = SchoolXlsxReport.generate_student_report(self.env, domain=domain, filter_desc=filter_desc)
            filename = f"Students_Master_Directory_{timestamp}.xlsx"
        elif self.report_type == 'class':
            content = SchoolXlsxReport.generate_class_report(self.env, domain=domain, filter_desc=filter_desc)
            filename = f"Classes_Directory_Report_{timestamp}.xlsx"
        else:
            raise UserError(_("Invalid report type selected."))

        self.write({
            'state': 'get',
            'file_data': base64.b64encode(content),
            'file_name': filename,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content?model={self._name}&id={self.id}&field=file_data&filename={filename}&download=true",
            'target': 'self',
        }

    def action_download_again(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("No report has been generated yet."))
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content?model={self._name}&id={self.id}&field=file_data&filename={self.file_name}&download=true",
            'target': 'self',
        }

    def action_reset(self):
        self.ensure_one()
        self.write({'state': 'choose'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
