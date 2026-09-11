from odoo import models


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
