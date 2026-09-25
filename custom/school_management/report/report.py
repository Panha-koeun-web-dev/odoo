import base64
from pathlib import Path

from odoo import models, fields, _
from odoo.exceptions import UserError
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
        if company.logo and not company.uses_default_logo:
            return image_data_uri(company.logo)
        return False

    def _static_image_uri(self, rel_path):
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


class SchoolTranscriptReport(models.AbstractModel):
    _name = 'report.school_management.report_academic_transcript'
    _description = 'Academic Transcript & Term Report Card Report Parser'

    def _get_transcript_docs(self, docids, data=None):
        data = data or {}
        cert_model = self.env['school.certificate']
        student_model = self.env['school.student']

        candidate_ids = docids or data.get('docids') or data.get('ids') or data.get('active_ids')
        active_model = data.get('active_model') or self.env.context.get('active_model') or self.env.context.get('params', {}).get('model') or self.env.context.get('default_model')
        context_ids = self.env.context.get('active_ids') or self.env.context.get('active_id')

        if not candidate_ids and context_ids:
            candidate_ids = context_ids

        if isinstance(candidate_ids, int):
            candidate_ids = [candidate_ids]
        elif candidate_ids and not isinstance(candidate_ids, list):
            candidate_ids = list(candidate_ids)

        # 1. If explicit active_model is student
        if candidate_ids and (active_model == 'school.student' or self.env.context.get('active_model') == 'school.student'):
            students = student_model.sudo().browse(candidate_ids).exists()
            if students:
                return cert_model.generate_certificates(students, certificate_type='transcript')

        # 2. Check if candidate_ids are certificates
        if candidate_ids:
            docs = cert_model.sudo().browse(candidate_ids).exists()
            if docs:
                return docs

            # 3. If not certificates, candidate_ids may be student IDs
            students = student_model.sudo().browse(candidate_ids).exists()
            if students:
                return cert_model.generate_certificates(students, certificate_type='transcript')

        # 4. If logged-in user is a student, automatically find or generate their transcript
        if (
            self.env.user.has_group('school_management.group_school_student')
            and not self.env.user.has_group('school_management.group_school_teacher')
            and not self.env.user.has_group('school_management.group_school_admin')
            and not self.env.is_admin()
        ):
            my_student = student_model.sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            if my_student:
                return cert_model.generate_certificates(my_student, certificate_type='transcript')

        # 5. If active_model is student in context
        if active_model == 'school.student' and context_ids:
            if isinstance(context_ids, int):
                context_ids = [context_ids]
            students = student_model.sudo().browse(context_ids).exists()
            if students:
                return cert_model.generate_certificates(students, certificate_type='transcript')

        return cert_model

    def _get_report_values(self, docids, data=None):
        common = self.env['school.report.common']
        docs = self._get_transcript_docs(docids, data=data).sudo()
        for rec in docs:
            rec.sudo()._compute_academic_metrics()
            rec.sudo()._compute_average_grade()
            rec.sudo()._compute_teachers()
        docids = docs.ids
        company = self.env.company.sudo()
        from odoo.tools import format_date
        from odoo.tools.image import image_data_uri as _our_idu

        transcripts = []
        for rec in docs:
            stu = rec.student_id
            courses = rec._get_transcript_courses()
            gender_label = dict(stu._fields['gender'].selection).get(stu.gender, stu.gender) if stu.gender else 'N/A'
            dob = format_date(self.env, stu.date_of_birth) if stu.date_of_birth else 'N/A'
            issue_date = format_date(self.env, rec.issue_date) if rec.issue_date else format_date(self.env, fields.Date.today())
            term_label = dict(rec._fields['term'].selection).get(rec.term, rec.term or 'Semester 1')
            standing_label = dict(rec._fields['academic_standing'].selection).get(rec.academic_standing, "Good Academic Standing")

            # Total credits, earned credits, GPA
            total_credits = sum(c['credits'] for c in courses) or rec.total_credits or 1
            earned_credits = sum(c['credits'] for c in courses if c['result'] == 'pass') or rec.earned_credits
            total_qp = sum(float(c['grade_point']) * c['credits'] for c in courses)
            gpa = round(total_qp / total_credits, 2) if total_credits else rec.gpa or 3.85

            teacher_name = (
                rec.homeroom_teacher_id.name if rec.homeroom_teacher_id
                else (stu.class_id.teacher_id.name if stu.class_id and stu.class_id.teacher_id else 'Prof. David Vance, Advisor')
            )

            transcripts.append({
                'cert': rec,
                'doc_number': rec.name,
                'student_name': stu.name,
                'student_code': stu.student_id,
                'class_name': stu.class_id.name or 'General Section',
                'term_label': term_label,
                'academic_year': rec.academic_year or stu.study_period or '2025-2026',
                'issue_date': issue_date,
                'dob': dob,
                'gender': gender_label,
                'email': stu.email or 'N/A',
                'phone': stu.phone or 'N/A',
                'majors': ', '.join(stu.major_enrollment_ids.filtered(lambda e: e.status == 'enrolled').mapped('major_id.name')) or ', '.join(stu.major_ids.mapped('name')) or 'Software Development',
                'has_photo': bool(stu.photo),
                'photo_uri': _our_idu(stu.photo) if stu.photo else '',
                'courses': courses,
                'total_credits': total_credits,
                'earned_credits': earned_credits,
                'gpa': f"{gpa:.2f}",
                'cumulative_gpa': f"{rec.cumulative_gpa or gpa:.2f}",
                'class_rank': rec.class_rank or 'Rank 1 of 24',
                'class_rank_number': rec.class_rank_number or 1,
                'total_students_in_class': rec.total_students_in_class or 24,
                'academic_standing': standing_label,
                'attendance_rate': f"{rec.attendance_rate:.1f}%",
                'present_days': rec.present_days,
                'absent_days': rec.absent_days,
                'late_days': rec.late_days,
                'homeroom_teacher': teacher_name,
                'principal_name': rec.principal_name or 'Dr. Robert Sterling, Academic Dean',
                'general_remarks': rec.general_remarks or 'Demonstrates outstanding analytical competence, active classroom engagement, and commendable academic dedication throughout the term.',
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
            'transcripts': transcripts,
            'user_name': self.env.user.name,
        }


class SchoolCertificateReport(models.AbstractModel):
    _name = 'report.school_management.certificate_report'
    _description = 'School Certificate Report'

    TYPE_TITLE = {
        'transcript': 'Academic Transcript & Report Card',
        'completion': 'Certificate of Completion',
        'achievement': 'Certificate of Achievement',
        'participation': 'Certificate of Participation',
    }

    def _accent_styles(self, hex_color):
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
        ctype = data.get('certificate_type')
        if isinstance(ctype, list) and ctype:
            ctype = ctype[0]
        if not ctype or ctype == 'transcript':
            ctype = 'completion'

        candidate_ids = docids or data.get('docids') or data.get('ids') or data.get('active_ids')
        active_model = data.get('active_model') or self.env.context.get('active_model')
        context_ids = self.env.context.get('active_ids') or self.env.context.get('active_id')

        if not candidate_ids and context_ids:
            candidate_ids = context_ids

        if isinstance(candidate_ids, int):
            candidate_ids = [candidate_ids]
        elif candidate_ids and not isinstance(candidate_ids, list):
            candidate_ids = list(candidate_ids)

        # 1. If explicit active_model is student
        if candidate_ids and (active_model == 'school.student' or self.env.context.get('active_model') == 'school.student'):
            students = student_model.sudo().browse(candidate_ids).exists()
            if students:
                return cert_model.generate_certificates(students, certificate_type=ctype)

        # 2. Check if candidate_ids are certificates
        if candidate_ids:
            docs = cert_model.sudo().browse(candidate_ids).exists()
            if docs:
                return docs

            # 3. If not certificates, candidate_ids may be student IDs
            students = student_model.sudo().browse(candidate_ids).exists()
            if students:
                return cert_model.generate_certificates(students, certificate_type=ctype)

        # 4. If logged-in user is a student, automatically find or generate their certificate
        if (
            self.env.user.has_group('school_management.group_school_student')
            and not self.env.user.has_group('school_management.group_school_teacher')
            and not self.env.user.has_group('school_management.group_school_admin')
            and not self.env.is_admin()
        ):
            my_student = student_model.sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            if my_student:
                return cert_model.generate_certificates(my_student, certificate_type=ctype)

        # 5. If active_model is student in context
        if active_model == 'school.student' and context_ids:
            if isinstance(context_ids, int):
                context_ids = [context_ids]
            students = student_model.sudo().browse(context_ids).exists()
            if students:
                return cert_model.generate_certificates(students, certificate_type=ctype)

        return cert_model

    def _get_report_values(self, docids, data=None):
        common = self.env['school.report.common']
        docs = self._get_certificate_docs(docids, data=data).sudo()
        for rec in docs:
            rec.sudo()._compute_academic_metrics()
            rec.sudo()._compute_average_grade()
            rec.sudo()._compute_teachers()
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
            'user_name': self.env.user.name,
        }


class SchoolReceiptReport(models.AbstractModel):
    _name = 'report.school_management.report_payment_receipt'
    _description = 'Student Payment Receipt Report Parser'

    def _company_receipt_logo_uri(self, company, max_width=240, max_height=80):
        if not company.logo or company.uses_default_logo:
            return False
        try:
            from PIL import Image
            import io
            raw_bytes = base64.b64decode(company.logo)
            im = Image.open(io.BytesIO(raw_bytes))
            im.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            fmt = 'PNG' if im.mode in ('RGBA', 'LA') else 'JPEG'
            im.save(buf, format=fmt, quality=95)
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')
            mime = 'image/png' if fmt == 'PNG' else 'image/jpeg'
            return f'data:{mime};base64,{b64}'
        except Exception:
            return self.env['school.report.common']._company_logo_uri(company)

    def _get_barcode_uri(self, code):
        if not code:
            return False
        try:
            from reportlab.graphics.barcode import createBarcodeDrawing
            from reportlab.graphics import renderSVG
            drawing = createBarcodeDrawing('Code128', value=str(code), width=210, height=28, humanReadable=False)
            svg = renderSVG.drawToString(drawing)
            b64 = base64.b64encode(svg.encode('utf-8')).decode('ascii')
            return f'data:image/svg+xml;base64,{b64}'
        except Exception:
            return False

    def _get_receipt_docs(self, docids, data=None):
        data = data or {}
        candidate_ids = docids or data.get('docids') or data.get('ids') or data.get('active_ids')
        active_model = data.get('active_model') or self.env.context.get('active_model')
        context_ids = self.env.context.get('active_ids') or self.env.context.get('active_id')

        if not candidate_ids and context_ids:
            candidate_ids = context_ids

        if isinstance(candidate_ids, int):
            candidate_ids = [candidate_ids]
        elif candidate_ids and not isinstance(candidate_ids, list):
            candidate_ids = list(candidate_ids)

        if not candidate_ids:
            return []

        if active_model == 'school.student' or self.env.context.get('active_model') == 'school.student':
            students = self.env['school.student'].sudo().browse(candidate_ids).exists()
            records = []
            for s in students:
                yp = s.year_payment_ids.filtered(lambda p: p.overall_status in ('paid', 'partial'))[:1]
                if yp:
                    records.append(yp)
                else:
                    fee = s.fee_ids.filtered(lambda f: f.status in ('paid', 'partial'))[:1]
                    if fee:
                        records.append(fee)
                    elif s.year_payment_ids:
                        records.append(s.year_payment_ids[0])
                    elif s.fee_ids:
                        records.append(s.fee_ids[0])
            return records

        if active_model == 'school.student.year.payment' or self.env.context.get('active_model') == 'school.student.year.payment':
            return self.env['school.student.year.payment'].sudo().browse(candidate_ids).exists()

        if active_model == 'school.fee' or self.env.context.get('active_model') == 'school.fee':
            return self.env['school.fee'].sudo().browse(candidate_ids).exists()

        fee_matches = self.env['school.fee'].sudo().search([('id', 'in', candidate_ids), ('receipt_number', 'like', 'REC-FEE-%')])
        if fee_matches:
            return fee_matches
        yp_matches = self.env['school.student.year.payment'].sudo().search([('id', 'in', candidate_ids), ('receipt_number', 'like', 'REC-YPAY-%')])
        if yp_matches:
            return yp_matches

        docs = self.env['school.student.year.payment'].sudo().browse(candidate_ids).exists()
        if docs:
            return docs
        docs = self.env['school.fee'].sudo().browse(candidate_ids).exists()
        if docs:
            return docs
        docs = self.env['school.student'].sudo().browse(candidate_ids).exists()
        if docs:
            records = []
            for s in docs:
                yp = s.year_payment_ids.filtered(lambda p: p.overall_status in ('paid', 'partial'))[:1] or s.year_payment_ids[:1]
                if yp:
                    records.append(yp)
            return records
        return []

    def _get_report_values(self, docids, data=None):
        common = self.env['school.report.common']
        docs = self._get_receipt_docs(docids, data=data)
        company = self.env.company.sudo()
        user = self.env.user

        inst_name = company.name if (company.name and company.name != 'My Company') else 'Passerelles Numériques Cambodia'
        inst_addr = (f"{company.street or ''}, {company.city or ''}").strip(', ')
        if not inst_addr:
            inst_addr = 'BP 511, Phum Tropeang Chhouk, Sangkat Teuk Thla, Khan Sen Sok, Phnom Penh'
        inst_phone = company.phone or '+855 (0) 23 99 55 00'
        inst_email = company.email or 'cambodia@passerellesnumeriques.org'
        inst_web = company.website or 'www.passerellesnumeriques.org'

        company_logo = self._company_receipt_logo_uri(company, max_width=240, max_height=80)
        if not company_logo:
            company_logo = common._static_image_uri('static/description/icon.png')

        receipts = []
        for rec in docs:
            model_name = rec._name
            if model_name == 'school.student.year.payment':
                if not rec.receipt_number:
                    rec.sudo().write({'receipt_number': rec._generate_receipt_number()})
                stu = rec.student_id
                line_items = []
                currency_sym = rec.currency_id.symbol or '$'
                if rec.installment_1_amount > 0:
                    status_text = 'Paid' if rec.installment_1_status == 'paid' else ('Partially Paid' if rec.installment_1_status == 'partial' else 'Pending')
                    if rec.installment_1_paid_date and rec.installment_1_status in ('paid', 'partial'):
                        status_text += ' on ' + common._format_date(rec.installment_1_paid_date)
                    fmt_amt = common._format_number(rec.installment_1_amount)
                    line_items.append({
                        'index': 1,
                        'name': f"Tuition ({rec.year}) — Installment 1",
                        'period': rec.year or 'Academic Year',
                        'sub_text': status_text,
                        'status': rec.installment_1_status,
                        'status_label': 'Paid' if rec.installment_1_status == 'paid' else ('Partial' if rec.installment_1_status == 'partial' else 'Pending'),
                        'amount': fmt_amt,
                        'amount_display': f"{currency_sym} {fmt_amt}",
                    })
                if rec.installment_2_amount > 0:
                    status_text = 'Paid' if rec.installment_2_status == 'paid' else ('Partially Paid' if rec.installment_2_status == 'partial' else 'Pending')
                    if rec.installment_2_paid_date and rec.installment_2_status in ('paid', 'partial'):
                        status_text += ' on ' + common._format_date(rec.installment_2_paid_date)
                    fmt_amt = common._format_number(rec.installment_2_amount)
                    line_items.append({
                        'index': 2,
                        'name': f"Tuition ({rec.year}) — Installment 2",
                        'period': rec.year or 'Academic Year',
                        'sub_text': status_text,
                        'status': rec.installment_2_status,
                        'status_label': 'Paid' if rec.installment_2_status == 'paid' else ('Partial' if rec.installment_2_status == 'partial' else 'Pending'),
                        'amount': fmt_amt,
                        'amount_display': f"{currency_sym} {fmt_amt}",
                    })
                if not line_items:
                    fmt_amt = common._format_number(rec.total_amount)
                    line_items.append({
                        'index': 1,
                        'name': f"Academic Tuition Fee ({rec.year})",
                        'period': rec.year or 'Academic Year',
                        'sub_text': 'Annual Full Tuition',
                        'status': rec.overall_status,
                        'status_label': 'Paid' if rec.overall_status == 'paid' else ('Partial' if rec.overall_status == 'partial' else 'Pending'),
                        'amount': fmt_amt,
                        'amount_display': f"{currency_sym} {fmt_amt}",
                    })

                pay_method_label = common._selection_label('school.student.year.payment', 'payment_method', rec.payment_method) or 'Cash'
                paid_dt = rec.installment_2_paid_date or rec.installment_1_paid_date
                receipt_date = common._format_date(paid_dt) if paid_dt else common._format_datetime(fields.Datetime.now())

                subtot_fmt = common._format_number(rec.total_amount)
                paid_fmt = common._format_number(rec.total_paid)
                bal_fmt = common._format_number(rec.total_balance)
                is_zero_balance = (rec.total_balance <= 0)

                status_label = 'PAID IN FULL' if rec.overall_status == 'paid' else ('PARTIALLY PAID' if rec.overall_status == 'partial' else 'PENDING')
                status_color = '#047857' if rec.overall_status == 'paid' else ('#b45309' if rec.overall_status == 'partial' else '#475569')
                status_bg = '#ecfdf5' if rec.overall_status == 'paid' else ('#fffbeb' if rec.overall_status == 'partial' else '#f8fafc')
                status_border = '#10b981' if rec.overall_status == 'paid' else ('#f59e0b' if rec.overall_status == 'partial' else '#cbd5e1')
                status_badge_icon = '✔' if rec.overall_status == 'paid' else ('⏳' if rec.overall_status == 'partial' else '●')
                cashier_disp = user.name if (user.name and user.name not in ('OdooBot', 'System')) else 'Administrator'

                receipts.append({
                    'doc_id': rec.id,
                    'model_name': model_name,
                    'logo_uri': company_logo,
                    'receipt_number': rec.receipt_number,
                    'receipt_date': receipt_date,
                    'receipt_type_label': 'Annual Tuition Payment',
                    'student_name': stu.name,
                    'student_code': stu.student_id or f"STU-{stu.id:04d}",
                    'student_email': stu.email or '',
                    'student_phone': stu.phone or '',
                    'parent_name': stu.parent_name or '',
                    'class_name': rec.class_id.name or stu.class_id.name or 'QA Test Class',
                    'academic_year': rec.year or stu.study_period or '2026',
                    'has_photo': bool(stu.photo),
                    'photo_uri': image_data_uri(stu.photo) if stu.photo else '',
                    'line_items': line_items,
                    'subtotal': subtot_fmt,
                    'adjustment': '0.00',
                    'discount': '0.00',
                    'tax': '0.00',
                    'total': subtot_fmt,
                    'paid_amount': paid_fmt,
                    'balance': bal_fmt,
                    'is_zero_balance': is_zero_balance,
                    'subtotal_display': f"{currency_sym} {subtot_fmt}",
                    'adjustment_display': f"{currency_sym} 0.00",
                    'discount_display': f"{currency_sym} 0.00",
                    'tax_display': f"{currency_sym} 0.00",
                    'total_display': f"{currency_sym} {subtot_fmt}",
                    'paid_amount_display': f"{currency_sym} {paid_fmt}",
                    'balance_display': f"{currency_sym} {bal_fmt}",
                    'payment_method': pay_method_label,
                    'status': rec.overall_status,
                    'status_label': status_label,
                    'status_color': status_color,
                    'status_bg': status_bg,
                    'status_border': status_border,
                    'status_badge_icon': status_badge_icon,
                    'cashier': cashier_disp,
                    'currency_symbol': currency_sym,
                    'barcode_uri': self._get_barcode_uri(rec.receipt_number),
                    'barcode_text': rec.receipt_number,
                    'inst_name': inst_name,
                    'inst_addr': inst_addr,
                    'inst_phone': inst_phone,
                    'inst_email': inst_email,
                    'inst_web': inst_web,
                })
            elif model_name == 'school.fee':
                if not rec.receipt_number:
                    rec.sudo().write({'receipt_number': rec._generate_receipt_number()})
                stu = rec.student_id
                fee_type_label = common._selection_label('school.fee', 'fee_type', rec.fee_type)
                sub_text = 'Paid' if rec.status == 'paid' else ('Partially Paid' if rec.status == 'partial' else 'Pending')
                if rec.paid_date and rec.status in ('paid', 'partial'):
                    sub_text += ' on ' + common._format_date(rec.paid_date)
                elif rec.due_date:
                    sub_text += ' (Due: ' + common._format_date(rec.due_date) + ')'

                currency_sym = '$'
                fmt_amt = common._format_number(rec.amount)
                line_items = [{
                    'index': 1,
                    'name': f"{fee_type_label} Invoice",
                    'period': stu.study_period or '2026',
                    'sub_text': sub_text,
                    'status': rec.status,
                    'status_label': 'Paid' if rec.status == 'paid' else ('Partial' if rec.status == 'partial' else 'Pending'),
                    'amount': fmt_amt,
                    'amount_display': f"{currency_sym} {fmt_amt}",
                }]
                pay_method_label = common._selection_label('school.fee', 'payment_method', rec.payment_method) or 'Cash'
                receipt_date = common._format_date(rec.paid_date) if rec.paid_date else common._format_datetime(fields.Datetime.now())

                subtot_fmt = fmt_amt
                paid_fmt = common._format_number(rec.paid_amount)
                bal_fmt = common._format_number(rec.balance)
                is_zero_balance = (rec.balance <= 0)

                status_label = 'PAID IN FULL' if rec.status == 'paid' else ('PARTIALLY PAID' if rec.status == 'partial' else 'PENDING')
                status_color = '#047857' if rec.status == 'paid' else ('#b45309' if rec.status == 'partial' else '#475569')
                status_bg = '#ecfdf5' if rec.status == 'paid' else ('#fffbeb' if rec.status == 'partial' else '#f8fafc')
                status_border = '#10b981' if rec.status == 'paid' else ('#f59e0b' if rec.status == 'partial' else '#cbd5e1')
                status_badge_icon = '✔' if rec.status == 'paid' else ('⏳' if rec.status == 'partial' else '●')
                cashier_disp = user.name if (user.name and user.name not in ('OdooBot', 'System')) else 'Administrator'

                receipts.append({
                    'doc_id': rec.id,
                    'model_name': model_name,
                    'logo_uri': company_logo,
                    'receipt_number': rec.receipt_number,
                    'receipt_date': receipt_date,
                    'receipt_type_label': f'{fee_type_label} Settlement',
                    'student_name': stu.name,
                    'student_code': stu.student_id or f"STU-{stu.id:04d}",
                    'student_email': stu.email or '',
                    'student_phone': stu.phone or '',
                    'parent_name': stu.parent_name or '',
                    'class_name': rec.class_id.name or stu.class_id.name or 'QA Test Class',
                    'academic_year': stu.study_period or '2026',
                    'has_photo': bool(stu.photo),
                    'photo_uri': image_data_uri(stu.photo) if stu.photo else '',
                    'line_items': line_items,
                    'subtotal': subtot_fmt,
                    'adjustment': '0.00',
                    'discount': '0.00',
                    'tax': '0.00',
                    'total': subtot_fmt,
                    'paid_amount': paid_fmt,
                    'balance': bal_fmt,
                    'is_zero_balance': is_zero_balance,
                    'subtotal_display': f"{currency_sym} {subtot_fmt}",
                    'adjustment_display': f"{currency_sym} 0.00",
                    'discount_display': f"{currency_sym} 0.00",
                    'tax_display': f"{currency_sym} 0.00",
                    'total_display': f"{currency_sym} {subtot_fmt}",
                    'paid_amount_display': f"{currency_sym} {paid_fmt}",
                    'balance_display': f"{currency_sym} {bal_fmt}",
                    'payment_method': pay_method_label,
                    'status': rec.status,
                    'status_label': status_label,
                    'status_color': status_color,
                    'status_bg': status_bg,
                    'status_border': status_border,
                    'status_badge_icon': status_badge_icon,
                    'cashier': cashier_disp,
                    'currency_symbol': currency_sym,
                    'barcode_uri': self._get_barcode_uri(rec.receipt_number),
                    'barcode_text': rec.receipt_number,
                    'inst_name': inst_name,
                    'inst_addr': inst_addr,
                    'inst_phone': inst_phone,
                    'inst_email': inst_email,
                    'inst_web': inst_web,
                })

        return {
            'doc_ids': [r['doc_id'] for r in receipts],
            'doc_model': receipts[0]['model_name'] if receipts else 'school.fee',
            'docs': docs,
            'company': company,
            'inst_name': inst_name,
            'inst_addr': inst_addr,
            'inst_phone': inst_phone,
            'inst_email': inst_email,
            'inst_web': inst_web,
            'company_logo': company_logo,
            'has_company_logo': bool(company_logo),
            'receipts': receipts,
            'user_name': user.name,
        }


class SchoolAttendanceReport(models.AbstractModel):
    _name = 'report.school_management.attendance_report'
    _description = 'School Attendance Report Parser'

    def _get_report_values(self, docids, data=None):
        common = self.env['school.report.common']
        docs = self.env['school.attendance'].browse(docids) if docids else self.env['school.attendance'].search([])
        company = self.env.company.sudo()
        status_dict = dict(self.env['school.attendance']._fields['status'].selection)
        attendance_rows = [{
            'student_name': rec.student_id.name or '',
            'student_id': rec.student_id.student_id or '',
            'class_name': rec.class_id.name or '',
            'date': common._format_date(rec.date),
            'status': status_dict.get(rec.status, rec.status or ''),
            'status_value': rec.status,
            'notes': rec.notes or '',
        } for rec in docs]
        status_counts = {
            'present': len(docs.filtered(lambda a: a.status == 'present')),
            'absent': len(docs.filtered(lambda a: a.status == 'absent')),
            'late': len(docs.filtered(lambda a: a.status == 'late')),
            'excused': len(docs.filtered(lambda a: a.status == 'excused')),
        }
        return {
            'doc_ids': docids,
            'doc_model': 'school.attendance',
            'docs': docs,
            'company': company,
            'total_records': len(docs),
            'attendance_rows': attendance_rows,
            'status_counts': status_counts,
            'generated_on': common._generated_on(),
            'user': self.env.user,
        }


class SchoolStudentIdCardReport(models.AbstractModel):
    _name = 'report.school_management.report_student_id_card'
    _description = 'Student ID Card with QR Report Parser'

    def _company_card_logo_uri(self, company, max_width=180, max_height=60):
        if not company.logo or company.uses_default_logo:
            return False
        try:
            from PIL import Image
            import io
            raw_bytes = base64.b64decode(company.logo)
            im = Image.open(io.BytesIO(raw_bytes))
            im.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            fmt = 'PNG' if im.mode in ('RGBA', 'LA') else 'JPEG'
            im.save(buf, format=fmt, quality=95)
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')
            mime = 'image/png' if fmt == 'PNG' else 'image/jpeg'
            return f'data:{mime};base64,{b64}'
        except Exception:
            return self.env['school.report.common']._company_logo_uri(company)

    def _get_qr_code_uri(self, student):
        try:
            import qrcode
            import io
            payload = student._get_id_card_qr_payload()
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=4,
                border=2,
            )
            qr.add_data(payload)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')
            return f'data:image/png;base64,{b64}'
        except Exception:
            return False

    def _get_barcode_uri(self, code):
        if not code:
            return False
        try:
            from reportlab.graphics.barcode import createBarcodeDrawing
            from reportlab.graphics import renderSVG
            drawing = createBarcodeDrawing('Code128', value=str(code), width=180, height=22, humanReadable=False)
            svg = renderSVG.drawToString(drawing)
            b64 = base64.b64encode(svg.encode('utf-8')).decode('ascii')
            return f'data:image/svg+xml;base64,{b64}'
        except Exception:
            return False

    def _get_student_docs(self, docids, data=None):
        data = data or {}
        candidate_ids = docids or data.get('docids') or data.get('ids') or data.get('active_ids')
        active_model = data.get('active_model') or self.env.context.get('active_model')
        context_ids = self.env.context.get('active_ids') or self.env.context.get('active_id')

        if not candidate_ids and context_ids:
            candidate_ids = context_ids

        if isinstance(candidate_ids, int):
            candidate_ids = [candidate_ids]
        elif candidate_ids and not isinstance(candidate_ids, list):
            candidate_ids = list(candidate_ids)

        if candidate_ids:
            return self.env['school.student'].sudo().browse(candidate_ids).exists()

        if self.env.user.has_group('school_management.group_school_student'):
            stu = self.env['school.student'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            if stu:
                return stu

        return self.env['school.student'].sudo().search([], limit=10)

    def _get_report_values(self, docids, data=None):
        common = self.env['school.report.common']
        students = self._get_student_docs(docids, data)
        company = self.env.company.sudo()
        company_logo = self._company_card_logo_uri(company)

        inst_name = company.name or 'Grand Royal Academy'
        inst_addr = ', '.join(filter(None, [company.street, company.city, company.country_id.name])) or '123 Campus Boulevard'
        inst_phone = company.phone or '+1 (555) 019-2834'
        inst_email = company.email or 'admin@school.edu'
        inst_web = company.website or 'www.school.edu'

        blood_dict = dict(self.env['school.student']._fields['blood_group'].selection)
        gender_dict = dict(self.env['school.student']._fields['gender'].selection)

        cards = []
        for stu in students:
            dob_str = common._format_date(stu.date_of_birth) if stu.date_of_birth else 'N/A'
            issue_date = common._format_date(fields.Date.today())
            expiry_date = common._format_date(stu.study_end_date) if stu.study_end_date else 'Academic Year End'

            blood_label = blood_dict.get(stu.blood_group, 'N/A') if stu.blood_group and stu.blood_group != 'unknown' else 'N/A'
            gender_label = gender_dict.get(stu.gender, stu.gender or 'N/A')

            qr_uri = self._get_qr_code_uri(stu)
            barcode_code = stu.student_id or f"STU-{stu.id:04d}"
            barcode_uri = self._get_barcode_uri(barcode_code)

            photo_uri = False
            if stu.photo:
                try:
                    photo_uri = image_data_uri(stu.photo)
                except Exception:
                    photo_uri = False

            name_parts = (stu.name or 'Student').strip().split()
            initials = (name_parts[0][0] + (name_parts[-1][0] if len(name_parts) > 1 else '')).upper()

            academic_year = stu.study_period or (stu.class_id.payment_year if stu.class_id and hasattr(stu.class_id, 'payment_year') else '2024-2025')
            if not academic_year or academic_year == 'False':
                academic_year = f"{fields.Date.today().year}-{fields.Date.today().year + 1}"

            cards.append({
                'student': stu,
                'student_id': stu.id,
                'name': stu.name or 'Student Name',
                'student_code': barcode_code,
                'class_name': stu.class_id.name if stu.class_id else 'General Studies',
                'academic_year': academic_year,
                'gender': gender_label,
                'dob': dob_str,
                'blood_group': blood_label,
                'has_blood_group': blood_label != 'N/A',
                'status': stu.study_status,
                'status_label': 'STUDYING' if stu.study_status == 'studying' else 'STOPPED',
                'phone': stu.phone or 'N/A',
                'emergency_phone': stu.parent_phone or stu.phone or inst_phone,
                'parent_name': stu.parent_name or 'Parent/Guardian',
                'parent_email': stu.parent_email or '',
                'address': stu.address or inst_addr,
                'issue_date': issue_date,
                'expiry_date': expiry_date,
                'photo_uri': photo_uri,
                'has_photo': bool(photo_uri),
                'initials': initials,
                'qr_code_uri': qr_uri,
                'barcode_uri': barcode_uri,
                'barcode_code': barcode_code,
            })

        return {
            'doc_ids': students.ids,
            'doc_model': 'school.student',
            'docs': students,
            'company': company,
            'company_logo': company_logo,
            'has_company_logo': bool(company_logo),
            'inst_name': inst_name,
            'inst_addr': inst_addr,
            'inst_phone': inst_phone,
            'inst_email': inst_email,
            'inst_web': inst_web,
            'cards': cards,
            'generated_on': common._generated_on(),
            'user_name': self.env.user.name,
        }
