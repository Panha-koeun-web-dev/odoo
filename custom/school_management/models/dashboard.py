# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import AccessError


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _filter_visible_menus(self):
        """Filter visible menus and completely hide all dashboard apps and menus from students."""
        menus = super()._filter_visible_menus()
        user = self.env.user
        is_restricted_student = (
            user.has_group('school_management.group_school_student')
            and not user.has_group('school_management.group_school_teacher')
            and not user.has_group('school_management.group_school_admin')
            and not self.env.is_admin()
            and not self.env.su
        )
        if is_restricted_student:
            dash_menus = menus.sudo().filtered(
                lambda m: 'dashboard' in (m.name or '').lower()
                or (m.action and 'dashboard' in (m.action.name or '').lower())
            )
            if dash_menus:
                dash_ids = set(dash_menus.ids)
                return menus.filtered(
                    lambda m: m.id not in dash_ids
                    and not (m.parent_id and m.parent_id.id in dash_ids)
                )
        return menus


class SchoolDashboard(models.AbstractModel):
    _name = 'school.dashboard'
    _description = 'School Management Dashboard Service'

    @api.model
    def get_dashboard_data(self):
        """Aggregate statistical data for the OWL School Dashboard.
        Restricted to Teachers and Administrators only.
        """
        user = self.env.user
        is_restricted_student = (
            user.has_group('school_management.group_school_student')
            and not user.has_group('school_management.group_school_teacher')
            and not user.has_group('school_management.group_school_admin')
            and not self.env.is_admin()
            and not self.env.su
        )
        if is_restricted_student:
            raise AccessError(_('Access Denied: Students are not permitted to view the school dashboard.'))

        student_model = self.env['school.student']
        teacher_model = self.env['school.teacher']
        class_model = self.env['school.class']
        subject_model = self.env['school.subject']
        exam_model = self.env['school.exam']
        attendance_model = self.env['school.attendance']
        grade_model = self.env['school.grade']
        fee_model = self.env['school.fee']

        # ---------------- 1. Top-Level Summary Counts ----------------
        student_count = student_model.search_count([])
        active_students = student_model.search_count([('active', '=', True)])
        studying_students = student_model.search_count([('active', '=', True), ('study_status', '=', 'studying')])
        stopped_students = student_model.search_count([('study_status', '=', 'stopped')])
        teacher_count = teacher_model.search_count([])
        class_count = class_model.search_count([])
        subject_count = subject_model.search_count([])
        exam_count = exam_model.search_count([])
        attendance_count = attendance_model.search_count([])
        grade_count = grade_model.search_count([])
        fee_count = fee_model.search_count([])

        avg_students_per_class = round(studying_students / class_count, 1) if class_count else 0.0

        # ---------------- 2. Student Demographics ----------------
        gender_counts = {'male': 0, 'female': 0, 'other': 0}
        for gender, count in student_model._read_group(domain=[], groupby=['gender'], aggregates=['__count']):
            if gender in gender_counts:
                gender_counts[gender] = count

        total_gender = student_count or 1
        male_pct = round(gender_counts['male'] / total_gender * 100, 1)
        female_pct = round(gender_counts['female'] / total_gender * 100, 1)
        other_pct = round(gender_counts['other'] / total_gender * 100, 1)

        # ---------------- 3. Attendance Analytics ----------------
        att_counts = {'present': 0, 'late': 0, 'excused': 0, 'absent': 0}
        for status, count in attendance_model._read_group(domain=[], groupby=['status'], aggregates=['__count']):
            if status in att_counts:
                att_counts[status] = count

        attended = att_counts['present'] + att_counts['late'] + att_counts['excused']
        attendance_rate = round(attended / attendance_count * 100, 1) if attendance_count else 0.0
        absence_rate = round(att_counts['absent'] / attendance_count * 100, 1) if attendance_count else 0.0

        # Monthly Trend
        monthly_trend = []
        try:
            months = {}
            for month_val, status, count in attendance_model._read_group(
                domain=[],
                groupby=['date:month', 'status'],
                aggregates=['__count'],
                order='date:month asc'
            ):
                if not month_val:
                    continue
                if hasattr(month_val, 'strftime'):
                    key = month_val.strftime('%Y-%m')
                    label = month_val.strftime("%b '%y")
                else:
                    key = str(month_val)
                    label = str(month_val)

                bucket = months.setdefault(key, {'label': label, 'present': 0, 'total': 0})
                bucket['total'] += count
                if status in ('present', 'late', 'excused'):
                    bucket['present'] += count

            for key in sorted(months.keys()):
                item = months[key]
                rate = round(item['present'] / item['total'] * 100, 1) if item['total'] else 0.0
                monthly_trend.append({
                    'key': key,
                    'label': item['label'],
                    'rate': rate,
                    'present': item['present'],
                    'total': item['total'],
                })
        except Exception:
            monthly_trend = []

        # ---------------- 4. Fee & Financial Analytics ----------------
        fee_status_counts = {'paid': 0, 'pending': 0, 'overdue': 0, 'partial': 0}
        fee_totals = {'amount': 0.0, 'paid_amount': 0.0, 'balance': 0.0}

        for status, total_amount, paid_amount, balance_amount, count in fee_model._read_group(
            domain=[],
            groupby=['status'],
            aggregates=['amount:sum', 'paid_amount:sum', 'balance:sum', '__count']
        ):
            if status in fee_status_counts:
                fee_status_counts[status] = count
            fee_totals['amount'] += (total_amount or 0.0)
            fee_totals['paid_amount'] += (paid_amount or 0.0)
            fee_totals['balance'] += (balance_amount or 0.0)

        fee_totals['amount'] = round(fee_totals['amount'], 2)
        fee_totals['paid_amount'] = round(fee_totals['paid_amount'], 2)
        fee_totals['balance'] = round(fee_totals['balance'], 2)

        fee_collection_rate = round(
            fee_totals['paid_amount'] / fee_totals['amount'] * 100, 1
        ) if fee_totals['amount'] else 0.0

        # Fee by Type Breakdown
        fee_type_labels = {
            'tuition': _('Tuition'),
            'exam': _('Exam'),
            'library': _('Library'),
            'lab': _('Lab'),
            'transport': _('Transport'),
            'other': _('Other'),
        }
        fee_type_rows = []
        for ftype, billed, collected in fee_model._read_group(
            domain=[],
            groupby=['fee_type'],
            aggregates=['amount:sum', 'paid_amount:sum']
        ):
            billed = round(billed or 0.0, 2)
            collected = round(collected or 0.0, 2)
            if billed or collected:
                fee_type_rows.append({
                    'key': ftype,
                    'label': fee_type_labels.get(ftype, ftype.title() if ftype else 'Unknown'),
                    'billed': billed,
                    'collected': collected,
                    'balance': round(billed - collected, 2),
                })

        # ---------------- 5. Academic Performance Analytics ----------------
        passed_count = 0
        failed_count = 0
        total_graded = 0
        avg_percentage = 0.0

        for result, count, avg_pct in grade_model._read_group(
            domain=[],
            groupby=['result'],
            aggregates=['__count', 'percentage:avg']
        ):
            if result == 'pass':
                passed_count = count
            elif result == 'fail':
                failed_count = count
            total_graded += count
            if avg_pct:
                avg_percentage = round(avg_pct, 1)

        pass_rate = round(passed_count / total_graded * 100, 1) if total_graded else 0.0

        # Grade Bands Distribution
        band_colors = {
            'a+': '#059669', 'a': '#10b981', 'a-': '#34d399',
            'b+': '#65a30d', 'b': '#84cc16', 'b-': '#a3e635',
            'c+': '#f59e0b', 'c': '#f97316', 'c-': '#fb923c',
            'd': '#f43f5e', 'f': '#ef4444',
        }
        band_labels = {
            'a+': 'A+', 'a': 'A', 'a-': 'A-', 'b+': 'B+', 'b': 'B', 'b-': 'B-',
            'c+': 'C+', 'c': 'C', 'c-': 'C-', 'd': 'D', 'f': 'F',
        }
        band_counts = {}
        for letter, count in grade_model._read_group(domain=[], groupby=['grade_letter'], aggregates=['__count']):
            if letter:
                band_counts[letter] = count

        grade_bands = []
        for key in ('a+', 'a', 'a-', 'b+', 'b', 'b-', 'c+', 'c', 'c-', 'd', 'f'):
            c = band_counts.get(key, 0)
            if c > 0:
                grade_bands.append({
                    'letter': band_labels[key],
                    'count': c,
                    'color': band_colors[key],
                })

        # ---------------- 6. Class Capacity & Occupancy ----------------
        classes = class_model.search([])
        total_capacity = sum(classes.mapped('capacity'))
        capacity_rate = round(studying_students / total_capacity * 100, 1) if total_capacity else 0.0

        top_classes = []
        for cls in classes.sorted(lambda c: c.student_count, reverse=True)[:6]:
            rate = round(cls.student_count / cls.capacity * 100, 1) if cls.capacity else 0.0
            top_classes.append({
                'id': cls.id,
                'name': cls.display_name,
                'students': cls.student_count,
                'capacity': cls.capacity,
                'rate': rate,
            })

        top_class = top_classes[0] if top_classes else None

        # ---------------- 7. Return Final Payload ----------------
        return {
            'summary': {
                'student_count': student_count,
                'active_students': active_students,
                'studying_students': studying_students,
                'stopped_students': stopped_students,
                'teacher_count': teacher_count,
                'class_count': class_count,
                'subject_count': subject_count,
                'exam_count': exam_count,
                'attendance_count': attendance_count,
                'grade_count': grade_count,
                'fee_count': fee_count,
                'avg_students_per_class': avg_students_per_class,
            },
            'demographics': {
                'male': gender_counts['male'],
                'female': gender_counts['female'],
                'other': gender_counts['other'],
                'male_pct': male_pct,
                'female_pct': female_pct,
                'other_pct': other_pct,
            },
            'attendance': {
                'attendance_rate': attendance_rate,
                'absence_rate': absence_rate,
                'present': att_counts['present'],
                'late': att_counts['late'],
                'excused': att_counts['excused'],
                'absent': att_counts['absent'],
                'trend': monthly_trend,
            },
            'fees': {
                'total_amount': fee_totals['amount'],
                'total_paid': fee_totals['paid_amount'],
                'total_balance': fee_totals['balance'],
                'collection_rate': fee_collection_rate,
                'outstanding_rate': round(100 - fee_collection_rate, 1),
                'paid_count': fee_status_counts['paid'],
                'pending_count': fee_status_counts['pending'],
                'overdue_count': fee_status_counts['overdue'],
                'partial_count': fee_status_counts['partial'],
                'open_count': fee_status_counts['pending'] + fee_status_counts['overdue'] + fee_status_counts['partial'],
                'types': fee_type_rows,
            },
            'academics': {
                'pass_rate': pass_rate,
                'passed_count': passed_count,
                'failed_count': failed_count,
                'avg_percentage': avg_percentage,
                'grade_bands': grade_bands,
            },
            'classes': {
                'capacity_rate': capacity_rate,
                'top_class_name': top_class['name'] if top_class else _('No class recorded'),
                'top_class_students': top_class['students'] if top_class else 0,
                'top_classes': top_classes,
            },
        }
