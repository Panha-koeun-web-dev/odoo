import math
from datetime import datetime
from html import escape

from odoo import models, fields, api, _

# ---------------- Chart theme ----------------
T_TEAL = '#0f766e'
T_BLUE = '#2563eb'
T_CYAN = '#0891b2'
T_AMBER = '#d97706'
T_GREEN = '#10b981'
T_RED = '#ef4444'
T_VIOLET = '#7c3aed'
T_SLATE = '#64748b'

GENDER_COLORS = {'male': T_CYAN, 'female': T_BLUE, 'other': T_VIOLET}
ATTENDANCE_COLORS = {
    'present': T_GREEN, 'late': T_AMBER, 'excused': T_CYAN, 'absent': T_RED,
}
FEE_COLORS = {
    'paid': T_GREEN, 'pending': T_AMBER, 'overdue': T_RED, 'partial': T_BLUE,
}
BAND_LABELS = {
    'a+': 'A+', 'a': 'A', 'a-': 'A-', 'b+': 'B+', 'b': 'B', 'b-': 'B-',
    'c+': 'C+', 'c': 'C', 'c-': 'C-', 'd': 'D', 'f': 'F',
}
BAND_COLORS = {
    'a+': '#059669', 'a': '#10b981', 'a-': '#34d399',
    'b+': '#65a30d', 'b': '#84cc16', 'b-': '#a3e635',
    'c+': '#f59e0b', 'c': '#f97316', 'c-': '#fb923c',
    'd': '#f43f5e', 'f': '#ef4444',
}


class SchoolDashboard(models.TransientModel):
    _name = 'school.dashboard'
    _description = 'School Management Dashboard'

    # ---------------- Counters ----------------
    student_count = fields.Integer(string='Total Students')
    teacher_count = fields.Integer(string='Total Teachers')
    class_count = fields.Integer(string='Total Classes')
    subject_count = fields.Integer(string='Total Subjects')
    exam_count = fields.Integer(string='Total Exams')
    attendance_count = fields.Integer(string='Attendance Records')
    grade_count = fields.Integer(string='Grade Records')
    fee_count = fields.Integer(string='Fee Records')

    # ---------------- Students breakdown ----------------
    male_students = fields.Float(string='Male Students')
    female_students = fields.Float(string='Female Students')
    other_students = fields.Float(string='Other Students')

    # ---------------- Fees ----------------
    total_fee_amount = fields.Float(string='Total Fees Amount')
    total_paid_amount = fields.Float(string='Total Paid')
    total_balance = fields.Float(string='Total Balance')
    paid_fees = fields.Integer(string='Paid Fees')
    pending_fees = fields.Integer(string='Pending Fees')
    overdue_fees = fields.Integer(string='Overdue Fees')
    partial_fees = fields.Integer(string='Partial Fees')

    # ---------------- Attendance ----------------
    present_attendance = fields.Integer(string='Present')
    absent_attendance = fields.Integer(string='Absent')
    late_attendance = fields.Integer(string='Late')
    excused_attendance = fields.Integer(string='Excused')
    attendance_rate = fields.Float(string='Attendance Rate')

    # ---------------- Grades / Performance ----------------
    avg_percentage = fields.Float(string='Average Percentage')
    passed_grades = fields.Integer(string='Passed')
    failed_grades = fields.Integer(string='Failed')
    pass_rate = fields.Float(string='Pass Rate')

    # ---------------- Class enrollment ----------------
    active_students = fields.Integer(string='Active Students')

    dashboard_html = fields.Html(
        string='Dashboard', compute='_compute_dashboard_html', sanitize=False)

    # ============================================================
    #  SVG chart helpers
    # ============================================================
    def _collect_stats(self):
        students = self.env['school.student'].search([])
        teachers = self.env['school.teacher'].search([])
        classes = self.env['school.class'].search([])
        subjects = self.env['school.subject'].search([])
        exams = self.env['school.exam'].search([])
        attendances = self.env['school.attendance'].search([])
        grades = self.env['school.grade'].search([])
        fees = self.env['school.fee'].search([])

        stats = {
            'student_count': len(students),
            'teacher_count': len(teachers),
            'class_count': len(classes),
            'subject_count': len(subjects),
            'exam_count': len(exams),
            'attendance_count': len(attendances),
            'grade_count': len(grades),
            'fee_count': len(fees),
            'active_students': len(students.filtered(lambda s: s.active)),
        }

        total_gender = len(students) or 1
        stats['male_students'] = round(
            len(students.filtered(lambda s: s.gender == 'male')) / total_gender * 100, 1)
        stats['female_students'] = round(
            len(students.filtered(lambda s: s.gender == 'female')) / total_gender * 100, 1)
        stats['other_students'] = round(
            len(students.filtered(lambda s: s.gender == 'other')) / total_gender * 100, 1)

        stats['total_fee_amount'] = round(sum(fees.mapped('amount')), 2)
        stats['total_paid_amount'] = round(sum(fees.mapped('paid_amount')), 2)
        stats['total_balance'] = round(sum(fees.mapped('balance')), 2)
        stats['paid_fees'] = len(fees.filtered(lambda f: f.status == 'paid'))
        stats['pending_fees'] = len(fees.filtered(lambda f: f.status == 'pending'))
        stats['overdue_fees'] = len(fees.filtered(lambda f: f.status == 'overdue'))
        stats['partial_fees'] = len(fees.filtered(lambda f: f.status == 'partial'))

        stats['present_attendance'] = len(attendances.filtered(lambda a: a.status == 'present'))
        stats['absent_attendance'] = len(attendances.filtered(lambda a: a.status == 'absent'))
        stats['late_attendance'] = len(attendances.filtered(lambda a: a.status == 'late'))
        stats['excused_attendance'] = len(attendances.filtered(lambda a: a.status == 'excused'))
        s = stats['present_attendance'] + stats['late_attendance'] + stats['excused_attendance']
        stats['attendance_rate'] = round(s / len(attendances) * 100, 1) if attendances else 0

        counted = grades.filtered(lambda g: g.percentage)
        stats['avg_percentage'] = round(
            sum(counted.mapped('percentage')) / len(counted), 1) if counted else 0
        passed = len(grades.filtered(lambda g: g.result == 'pass'))
        stats['passed_grades'] = passed
        stats['failed_grades'] = len(grades) - passed
        stats['pass_rate'] = round(passed / len(grades) * 100, 1) if grades else 0

        capacity = sum(classes.mapped('capacity'))
        stats['capacity_rate'] = round(
            stats['student_count'] / capacity * 100, 1) if capacity else 0
        stats['avg_students_per_class'] = round(
            stats['student_count'] / len(classes), 1) if classes else 0
        top_class = max(classes, key=lambda cls: cls.student_count, default=False)
        stats['top_class_name'] = top_class.display_name if top_class else 'No class yet'
        stats['top_class_students'] = top_class.student_count if top_class else 0
        stats['fee_collection_rate'] = round(
            stats['total_paid_amount'] / stats['total_fee_amount'] * 100, 1
        ) if stats['total_fee_amount'] else 0
        stats['outstanding_rate'] = round(100 - stats['fee_collection_rate'], 1)
        stats['open_fee_count'] = stats['pending_fees'] + stats['partial_fees'] + stats['overdue_fees']
        stats['absence_rate'] = round(100 - stats['attendance_rate'], 1) if attendances else 0
        stats['male_count'] = len(students.filtered(lambda s: s.gender == 'male'))
        stats['female_count'] = len(students.filtered(lambda s: s.gender == 'female'))
        stats['other_count'] = len(students.filtered(lambda s: s.gender == 'other'))
        stats['class_rows'] = [
            {
                'name': school_class.display_name,
                'students': school_class.student_count,
                'capacity': school_class.capacity,
                'rate': round(school_class.student_count / school_class.capacity * 100, 1)
                if school_class.capacity else 0,
            }
            for school_class in classes.sorted(lambda cls: cls.student_count, reverse=True)[:6]
        ]
        stats['actions'] = {
            'students': self._action_url('school_management.action_student'),
            'teachers': self._action_url('school_management.action_teacher'),
            'classes': self._action_url('school_management.action_class'),
            'subjects': self._action_url('school_management.action_subject'),
            'attendance': self._action_url('school_management.action_attendance'),
            'grades': self._action_url('school_management.action_grade'),
            'fees': self._action_url('school_management.action_fee'),
            'exams': self._action_url('school_management.action_exam'),
        }

        # ---- grade distribution (A+ .. F) ----
        grade_bands = []
        for letter in ('a+', 'a', 'a-', 'b+', 'b', 'b-', 'c+', 'c', 'c-', 'd', 'f'):
            count = len(grades.filtered(
                lambda g, l=letter: (g.grade_letter or 'f') == l))
            if count:
                grade_bands.append((BAND_LABELS[letter], count, BAND_COLORS[letter]))
        stats['grade_bands'] = grade_bands

        # ---- fee amounts by type (billed vs collected) ----
        fee_types = [
            ('tuition', 'Tuition'), ('exam', 'Exam'), ('library', 'Library'),
            ('lab', 'Lab'), ('transport', 'Transport'), ('other', 'Other'),
        ]
        fee_type_rows = []
        for key, label in fee_types:
            subset = fees.filtered(lambda f, k=key: f.fee_type == k)
            billed = round(sum(subset.mapped('amount')), 2)
            paid = round(sum(subset.mapped('paid_amount')), 2)
            if billed or paid:
                fee_type_rows.append((label, billed, paid))
        stats['fee_type_rows'] = fee_type_rows

        # ---- attendance rate trend by month ----
        months = {}
        for a in attendances:
            key = a.date.strftime('%Y-%m') if a.date else ''
            if not key:
                continue
            bucket = months.setdefault(key, [0, 0])
            bucket[1] += 1
            if a.status in ('present', 'late', 'excused'):
                bucket[0] += 1
        trend = []
        for key in sorted(months):
            present, total = months[key]
            rate = round(present / total * 100, 1) if total else 0
            try:
                label = datetime.strptime(key, '%Y-%m').strftime("%b '%y")
            except ValueError:
                label = key
            trend.append((label, rate))
        stats['attendance_trend'] = trend

        return stats

    def _action_url(self, xmlid):
        action = self.env.ref(xmlid, raise_if_not_found=False)
        return f'/odoo/action-{action.id}' if action else '#'

    def _compute_dashboard_html(self):
        for rec in self:
            c = rec._collect_stats()
            rec.update({key: value for key, value in c.items() if key in rec._fields})
            rec.dashboard_html = rec._render_html(c)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = _('Dashboard')

    def action_open_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'display_name': 'Dashboard',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('school_management.view_school_dashboard_form').id,
            'context': {'no_breadcrumbs': True},
            'target': 'main',
        }

    # ============================================================
    #  Chart primitives
    # ============================================================

    @staticmethod
    def _fmt(v):
        av = abs(v)
        if av >= 1e6:
            return f'{v / 1e6:.1f}M'
        if av >= 1e4:
            return f'{av / 1e3:,.0f}k'
        return f'{v:,.0f}'

    @staticmethod
    def _trunc(s, n=11):
        s = str(s)
        return s if len(s) <= n else s[:n - 1] + '\u2026'

    @staticmethod
    def _nice_max(v):
        if v <= 0:
            return 10
        mag = 10 ** max(0, len(str(int(v))) - 1)
        base = v / mag
        if base <= 1:
            return mag
        if base <= 2:
            return 2 * mag
        if base <= 5:
            return 5 * mag
        return 10 * mag

    def _empty_chart(self, width, height, msg='No data available yet'):
        cx, cy = width / 2, height / 2
        return (
            f'<svg class="chart_svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
            f'<rect x="14" y="14" width="{width - 28}" height="{height - 28}" '
            f'rx="12" fill="#f8fafc" stroke="#e9eef5"/>'
            f'<text x="{cx}" y="{cy - 3}" text-anchor="middle" class="chart_empty">{msg}</text>'
            f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" '
            f'class="chart_empty_sub">Add records to see insights</text>'
            f'</svg>'
        )

    def _polar(self, cx, cy, r, angle):
        a = math.radians(angle)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    def _donut(self, segments, center_value, center_label, size=196, thickness=32):
        total = sum(s['value'] for s in segments)
        cx = cy = size / 2
        if total <= 0:
            outer = size / 2 - 6
            inner = outer - thickness
            return (
                f'<svg class="chart_svg" width="{size}" height="{size}" '
                f'viewBox="0 0 {size} {size}">'
                f'<circle cx="{cx}" cy="{cy}" r="{inner}" fill="#f8fafc" '
                f'stroke="#e9eef5" stroke-width="{thickness}"/>'
                f'<text x="{cx}" y="{cy}" text-anchor="middle" class="chart_center_value">0</text>'
                f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" '
                f'class="chart_center_label">No data</text>'
                f'</svg>'
            )
        outer = size / 2 - 6
        inner = outer - thickness
        angle = 0
        parts = []
        for s in segments:
            v = s['value']
            if v <= 0:
                continue
            a0 = -90 + angle
            a1 = a0 + (v / total) * 360
            angle = a1 + 90
            x0, y0 = self._polar(cx, cy, outer, a0)
            x1, y1 = self._polar(cx, cy, outer, a1)
            xi0, yi0 = self._polar(cx, cy, inner, a0)
            xi1, yi1 = self._polar(cx, cy, inner, a1)
            large = 1 if (a1 - a0) % 360 > 180 else 0
            pct = round(v / total * 100, 1)
            path = (
                f'M{x0:.2f} {y0:.2f} A{outer} {outer} 0 {large} 1 {x1:.2f} {y1:.2f} '
                f'L{xi1:.2f} {yi1:.2f} A{inner} {inner} 0 {large} 0 {xi0:.2f} {yi0:.2f} Z'
            )
            parts.append(
                f'<g class="chart_seg"><title>{escape(str(s["label"]))}: '
                f'{v:,.0f} ({pct}%)</title>'
                f'<path d="{path}" fill="{s["color"]}"/></g>'
            )
        return (
            f'<svg class="chart_svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<circle cx="{cx}" cy="{cy}" r="{inner}" fill="#f8fafc" '
            f'stroke="#e9eef5" stroke-width="1"/>'
            + ''.join(parts)
            + f'<text x="{cx}" y="{cy}" text-anchor="middle" pointer-events="none" '
            f'class="chart_center_value">{center_value}</text>'
            + f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" pointer-events="none" '
            f'class="chart_center_label">{escape(str(center_label))}</text>'
            + '</svg>'
        )

    def _legend(self, segments, total, show_pct=True):
        out = []
        for s in segments:
            pct = round(s['value'] / total * 100, 1) if total else 0
            num = f'{s["value"]:,.0f}'
            pct_html = f'<em class="legend_pct">{pct:.0f}%</em>' if show_pct and total else ''
            out.append(
                f'<div class="legend_item">'
                f'<span class="swatch" style="background:{s["color"]}"></span>'
                f'<span>{escape(str(s["label"]))}</span>'
                f'<b>{num}{pct_html}</b></div>'
            )
        return ''.join(out)

    def _y_grid(self, left, top, right, bottom, width, height, nice, pct=False):
        plotw = width - left - right
        ploth = height - top - bottom
        lines = []
        for f in (1.0, .75, .5, .25, 0.0):
            y = top + ploth * (1 - f)
            lines.append(
                f'<line class="chart_grid" x1="{left}" y1="{y:.1f}" '
                f'x2="{width - right}" y2="{y:.1f}"/>')
            lines.append(
                f'<line class="chart_grid_tick" x1="{left - 5}" y1="{y:.1f}" '
                f'x2="{left}" y2="{y:.1f}"/>')
            label = f'{nice * f:.0f}%' if pct else self._fmt(nice * f)
            lines.append(
                f'<text class="chart_axis" x="{left - 7}" y="{y + 3:.1f}" '
                f'text-anchor="end">{label}</text>')
        return ''.join(lines)

    def _bars(self, rows, unit='', width=470, height=235):
        rows = [(str(l), float(v), str(c)) for l, v, c in rows]
        if not rows or all(v <= 0 for _, v, _ in rows):
            return self._empty_chart(width, height)
        left, top, right, bottom = 40, 26, 10, 34
        plotw = width - left - right
        ploth = height - top - bottom
        nice = self._nice_max(max(v for _, v, _ in rows))
        grid = self._y_grid(left, top, right, bottom, width, height, nice)
        n = len(rows)
        slot = plotw / n
        bw = min(slot * .58, 46)
        bars = []
        for i, (label, value, color) in enumerate(rows):
            x = left + slot * i + (slot - bw) / 2
            h = ploth * (value / nice)
            y = top + ploth - h
            tip = f'{escape(label)}: {self._fmt(value)}'
            bar = f'<g class="chart_bar"><title>{tip}{(" " + unit) if unit else ""}</title>'
            bar += (
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bw:.2f}" '
                f'height="{h:.2f}" rx="5" fill="{color}"/>')
            if h > 14:
                bar += (
                    f'<text class="chart_bar_val" x="{x + bw / 2:.2f}" y="{y - 6:.2f}" '
                    f'text-anchor="middle">{self._fmt(value)}</text>')
            bar += (
                f'<text class="chart_axis" x="{x + bw / 2:.2f}" y="{height - 12}" '
                f'text-anchor="middle">{escape(self._trunc(label))}</text></g>')
            bars.append(bar)
        return (
            f'<svg class="chart_svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">' + grid + ''.join(bars) + '</svg>')

    def _grouped_bars(self, rows, series, colors, width=490, height=250):
        rows = [(str(l), [float(x) for x in vals]) for l, *vals in rows]
        if not rows or all(all(v <= 0 for v in vals) for _, vals in rows):
            return self._empty_chart(width, height)
        left, top, right, bottom = 42, 26, 10, 30
        plotw = width - left - right
        ploth = height - top - bottom
        maxv = max(max(vals) for _, vals in rows)
        nice = self._nice_max(maxv)
        grid = self._y_grid(left, top, right, bottom, width, height, nice)
        n = len(rows)
        k = len(series)
        slot = plotw / n
        bww = min(slot / (k + .4), 24)
        total_bw = bww * k
        bars = []
        for i, (label, vals) in enumerate(rows):
            x0 = left + slot * i + (slot - total_bw) / 2
            for j, v in enumerate(vals):
                if v <= 0:
                    continue
                x = x0 + j * bww
                h = ploth * (v / nice)
                y = top + ploth - h
                g = (
                    f'<g class="chart_bar">'
                    f'<title>{escape(label)} \u00b7 {escape(series[j])}: '
                    f'{self._fmt(v)}</title>'
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(bww - 3, 2):.2f}" '
                    f'height="{h:.2f}" rx="3" fill="{colors[j]}"/></g>')
                bars.append(g)
            bars.append(
                f'<text class="chart_axis" x="{x0 + total_bw / 2:.2f}" '
                f'y="{height - 12}" text-anchor="middle">'
                f'{escape(self._trunc(label))}</text>')
        return (
            f'<svg class="chart_svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">' + grid + ''.join(bars) + '</svg>')

    def _line(self, points, width=470, height=250):
        points = [(str(l), float(v)) for l, v in points]
        if not points:
            return self._empty_chart(width, height, 'No attendance records yet')
        left, top, right, bottom = 34, 38, 14, 34
        plotw = width - left - right
        ploth = height - top - bottom
        hi = max(100, ((int(max(v for _, v in points)) + 9) // 10) * 10)
        grid = self._y_grid(left, top, right, bottom, width, height, hi, pct=True)
        n = len(points)
        xs = [left + plotw * (i / (n - 1) if n > 1 else .5) for i in range(n)]
        ys = [top + ploth * (1 - v / hi) for _, v in points]
        pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in zip(xs, ys))
        area = (
            f'M{xs[0]:.1f} {top + ploth:.1f} L'
            + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in zip(xs, ys))
            + f' L{xs[-1]:.1f} {top + ploth:.1f} Z')
        dots = []
        step = max(1, n // 12)
        labels = ''
        for i, (x, y) in enumerate(zip(xs, ys)):
            lbl, v = points[i]
            dots.append(
                f'<circle class="chart_dot" cx="{x:.1f}" cy="{y:.1f}" r="4">'
                f'<title>{escape(lbl)}: {v:.1f}%</title></circle>')
            if i % step == 0:
                labels += (
                    f'<text class="chart_axis" x="{x:.1f}" y="{height - 10}" '
                    f'text-anchor="middle">{escape(lbl)}</text>')
        last_x, last_y = xs[-1], ys[-1]
        last_val = points[-1][1]
        return (
            f'<svg class="chart_svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">' + grid
            + f'<path d="{area}" fill="#0f766e" opacity=".07" stroke="none"/>'
            + f'<polyline points="{pts}" fill="none" stroke="#0f766e" '
            f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
            + ''.join(dots)
            + f'<text class="chart_line_val" x="{last_x:.1f}" y="{last_y - 9:.1f}" '
            f'text-anchor="middle">{last_val:.0f}%</text>'
            + labels + '</svg>')

    def _hbars(self, rows, label_w=110, width=500):
        rows = [tuple(r) for r in rows]
        if not rows:
            return self._empty_chart(width, 220, 'No class data yet')
        per = 38
        top = 22
        bottom = 26
        left = label_w
        right = 40
        n = len(rows)
        height = top + per * n + bottom
        plotw = width - left - right
        plot_h = per * n
        nice = self._nice_max(max(m for _, _, m, _ in rows))
        grid = []
        for f in (1.0, .75, .5, .25, 0.0):
            x = left + plotw * f
            grid.append(
                f'<line class="chart_grid" x1="{x:.1f}" y1="{top}" '
                f'x2="{x:.1f}" y2="{top + plot_h}"/>')
            grid.append(
                f'<text class="chart_axis" x="{x:.1f}" y="{top + plot_h + 16}" '
                f'text-anchor="middle">{self._fmt(nice * f)}</text>')
        bars = []
        for i, (label, value, cap, color) in enumerate(rows):
            y = top + per * i + per / 2
            w = plotw * (value / nice)
            capx = left + plotw * (cap / nice if cap else 0)
            pct = round(value / cap * 100, 1) if cap else 0
            tip = f'{escape(str(label))}: {value:,.0f} of {cap:,.0f} students ({pct}%)'
            bars.append(f'<g class="chart_bar"><title>{tip}</title>')
            bars.append(
                f'<text class="chart_axis" x="{left - 8}" y="{y + 4:.1f}" '
                f'text-anchor="end">{escape(self._trunc(str(label), 16))}</text>')
            if w >= 2:
                bars.append(
                    f'<rect x="{left}" y="{y - 9:.1f}" width="{w:.1f}" height="18" '
                    f'rx="5" fill="{color}"/>')
                inner = (
                    f'<text class="cap_lab" x="{left + 7}" y="{y + 3.5:.1f}">'
                    f'{value:,.0f}</text>')
                bars.append(inner if w > 34 else '')
            if cap:
                bars.append(
                    f'<line class="chart_cap" x1="{capx:.1f}" y1="{y - 12:.1f}" '
                    f'x2="{capx:.1f}" y2="{y + 12:.1f}"/>')
                bars.append(
                    f'<text class="chart_axis" x="{capx + 6}" y="{y + 3.5:.1f}">'
                    f'cap {cap:,.0f}</text>')
            bars.append('</g>')
        return (
            f'<svg class="chart_svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">' + ''.join(grid) + ''.join(bars) + '</svg>')

    @staticmethod
    def _occ_color(rate):
        return T_GREEN if rate < 70 else (T_AMBER if rate < 90 else T_RED)

    # ============================================================
    #  Dashboard renderer
    # ============================================================
    def _render_html(self, c):
        actions = c['actions']

        gend_segments = [
            {'label': 'Female', 'value': c['female_count'], 'color': T_BLUE},
            {'label': 'Male', 'value': c['male_count'], 'color': T_CYAN},
            {'label': 'Other', 'value': c['other_count'], 'color': T_VIOLET},
        ]
        att_segments = [
            {'label': 'Present', 'value': c['present_attendance'], 'color': ATTENDANCE_COLORS['present']},
            {'label': 'Late', 'value': c['late_attendance'], 'color': ATTENDANCE_COLORS['late']},
            {'label': 'Excused', 'value': c['excused_attendance'], 'color': ATTENDANCE_COLORS['excused']},
            {'label': 'Absent', 'value': c['absent_attendance'], 'color': ATTENDANCE_COLORS['absent']},
        ]
        fee_segments = [
            {'label': 'Paid', 'value': c['paid_fees'], 'color': FEE_COLORS['paid']},
            {'label': 'Partial', 'value': c['partial_fees'], 'color': FEE_COLORS['partial']},
            {'label': 'Pending', 'value': c['pending_fees'], 'color': FEE_COLORS['pending']},
            {'label': 'Overdue', 'value': c['overdue_fees'], 'color': FEE_COLORS['overdue']},
        ]
        passfail_segments = [
            {'label': 'Passed', 'value': c['passed_grades'], 'color': T_GREEN},
            {'label': 'Failed', 'value': c['failed_grades'], 'color': T_RED},
        ]

        gend_donut = self._donut(gend_segments, self._fmt(c['student_count']), 'Students')
        gend_legend = self._legend(gend_segments, c['student_count'])
        att_donut = self._donut(att_segments, f"{c['attendance_rate']:.0f}%", 'Attendance Rate')
        att_legend = self._legend(att_segments, c['attendance_count'])
        fee_donut = self._donut(fee_segments, f"{c['fee_collection_rate']:.0f}%", 'Fee Collection')
        fee_legend = self._legend(fee_segments, c['fee_count'])

        grade_bars = self._bars(c['grade_bands'], unit='records')
        pf_donut = self._donut(passfail_segments, f"{c['pass_rate']:.0f}%", 'Pass Rate', size=148, thickness=22)
        pf_legend = self._legend(passfail_segments, c['grade_count'])

        fee_rows = [(label, billed, paid) for label, billed, paid in c['fee_type_rows']]
        fee_bars = self._grouped_bars(fee_rows, ['Billed', 'Collected'], [T_SLATE, T_TEAL])
        trend_line = self._line(c['attendance_trend'])
        hbar_rows = [
            (r['name'], r['students'], r['capacity'] or 0, self._occ_color(r['rate']))
            for r in c['class_rows']
        ]
        occ_bars = self._hbars(hbar_rows)

        return f'''
        <style>
            .school_dashboard_form .o_form_renderer,
            .school_dashboard_form .o_form_sheet_bg,
            .school_dashboard_form .o_form_nosheet {{
                padding:0 !important;
                margin:0 !important;
                max-width:none !important;
                width:100% !important;
                background:#f5f7fa !important;
            }}
            .school_dashboard_form .o_field_html,
            .school_dashboard_form .o_readonly_modifier {{
                width:100% !important;
            }}
            body:has(.school_dash) .o_control_panel_breadcrumbs,
            body:has(.school_dash) .o_control_panel_navigation,
            body:has(.school_dash) .o_control_panel_main_buttons {{
                display:none !important;
            }}
            body:has(.school_dash) .o_control_panel {{
                min-height:0 !important;
                padding:0 !important;
                border-bottom:0 !important;
            }}
            body:has(.school_dash) {{
                --school-inline-sidebar-width:248px;
                --school-inline-navbar-height:46px;
            }}
            body:has(.school_dash) .o_main_navbar .o_menu_brand {{
                min-width:var(--school-inline-sidebar-width);
                padding-left:16px;
                font-weight:800;
            }}
            body:has(.school_dash) .o_main_navbar .o_menu_sections {{
                position:fixed !important;
                top:var(--school-inline-navbar-height);
                left:0;
                z-index:100;
                display:flex !important;
                flex-direction:column;
                align-items:stretch;
                gap:5px;
                width:var(--school-inline-sidebar-width);
                height:calc(100vh - var(--school-inline-navbar-height));
                padding:14px 12px;
                overflow-y:auto;
                background:#fff;
                border-right:1px solid #dfe6f0;
                box-shadow:8px 0 24px rgba(15,23,42,.04);
            }}
            body:has(.school_dash) .o_main_navbar .o_menu_sections > a,
            body:has(.school_dash) .o_main_navbar .o_menu_sections > button,
            body:has(.school_dash) .o_main_navbar .o_menu_sections .dropdown > button {{
                display:flex;
                align-items:center;
                width:100%;
                min-height:42px;
                padding:10px 12px;
                border:0;
                border-radius:8px;
                color:#344054 !important;
                background:transparent;
                font-size:14px;
                font-weight:700;
                text-align:left;
            }}
            body:has(.school_dash) .o_main_navbar .o_menu_sections > a:hover,
            body:has(.school_dash) .o_main_navbar .o_menu_sections > button:hover,
            body:has(.school_dash) .o_main_navbar .o_menu_sections .dropdown > button:hover {{
                color:#0f766e !important;
                background:#ecfdf5;
            }}
            body:has(.school_dash) .o_main_navbar .o_menu_sections .active,
            body:has(.school_dash) .o_main_navbar .o_menu_sections .show > button {{
                color:#fff !important;
                background:#0f766e !important;
            }}
            body:has(.school_dash) .o_action_manager {{
                margin-left:var(--school-inline-sidebar-width);
                width:calc(100% - var(--school-inline-sidebar-width));
            }}
            .school_dash {{
                width:100%;
                min-height:calc(100vh - 120px);
                background:#f5f7fa;
                color:#182230;
                font-family:Inter,'Segoe UI',system-ui,sans-serif;
                padding:22px 28px 34px;
                box-sizing:border-box;
            }}
            .school_dash * {{ box-sizing:border-box; }}
            .school_dash a {{ color:inherit; text-decoration:none; }}
            .dash_head {{
                display:grid;
                grid-template-columns:minmax(0,1fr) auto;
                gap:18px;
                align-items:end;
                padding:8px 0 22px;
                border-bottom:1px solid #d9e0ea;
                margin-bottom:22px;
            }}
            .dash_head h1 {{ font-size:30px; line-height:1.15; font-weight:800; margin:0; letter-spacing:0; }}
            .dash_head p {{ margin:7px 0 0; color:#667085; font-size:14px; }}
            .dash_live {{
                display:inline-flex;
                align-items:center;
                gap:8px;
                color:#0f766e;
                background:#ecfdf5;
                border:1px solid #bbf7d0;
                border-radius:8px;
                padding:9px 12px;
                font-size:13px;
                font-weight:700;
                white-space:nowrap;
            }}
            .quick_actions {{
                display:flex;
                gap:8px;
                flex-wrap:wrap;
                justify-content:flex-end;
            }}
            .quick_actions a {{
                display:inline-flex;
                align-items:center;
                gap:7px;
                min-height:38px;
                padding:9px 12px;
                border-radius:8px;
                background:#fff;
                border:1px solid #dfe6f0;
                color:#344054;
                font-weight:700;
                font-size:13px;
                box-shadow:0 1px 2px rgba(16,24,40,.04);
            }}
            .quick_actions a:hover {{ border-color:#94a3b8; transform:translateY(-1px); }}
            .metric_grid {{
                display:grid;
                grid-template-columns:repeat(4,minmax(180px,1fr));
                gap:14px;
                margin-bottom:18px;
            }}
            .metric_card {{
                min-height:112px;
                background:#fff;
                border:1px solid #dfe6f0;
                border-radius:8px;
                padding:18px;
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                box-shadow:0 1px 2px rgba(16,24,40,.04);
                transition:transform .15s ease, border-color .15s ease, box-shadow .15s ease;
            }}
            .metric_card:hover {{
                transform:translateY(-2px);
                border-color:#94a3b8;
                box-shadow:0 10px 24px rgba(16,24,40,.09);
            }}
            .metric_label {{ color:#667085; font-size:13px; font-weight:700; text-transform:uppercase; }}
            .metric_value {{ margin-top:12px; font-size:34px; line-height:1; font-weight:800; }}
            .metric_hint {{ margin-top:10px; color:#667085; font-size:12px; }}
            .metric_icon {{
                width:42px;
                height:42px;
                border-radius:8px;
                display:flex;
                align-items:center;
                justify-content:center;
                color:#fff;
                font-size:18px;
                box-shadow:inset 0 -6px 12px rgba(255,255,255,.14);
            }}
            .analysis_grid {{
                display:grid;
                grid-template-columns:repeat(4,minmax(180px,1fr));
                gap:14px;
                margin-bottom:18px;
            }}
            .analysis_card {{
                background:#fff;
                border:1px solid #dfe6f0;
                border-left:4px solid #0f766e;
                border-radius:8px;
                padding:16px;
                box-shadow:0 1px 2px rgba(16,24,40,.04);
            }}
            .analysis_top {{
                display:flex;
                align-items:center;
                justify-content:space-between;
                gap:10px;
                color:#667085;
                font-size:12px;
                font-weight:800;
                text-transform:uppercase;
            }}
            .analysis_value {{ margin-top:10px; font-size:28px; line-height:1; font-weight:800; }}
            .analysis_note {{ margin-top:8px; color:#667085; font-size:13px; line-height:1.35; }}
            .charts_head {{
                display:flex;
                align-items:baseline;
                gap:12px;
                flex-wrap:wrap;
                margin:26px 0 14px;
            }}
            .charts_head h2 {{ font-size:19px; font-weight:800; margin:0; }}
            .charts_head span {{ font-size:12px; color:#667085; font-weight:600; }}
            .row3 {{
                display:grid;
                grid-template-columns:repeat(3,minmax(0,1fr));
                gap:16px;
                margin-bottom:16px;
            }}
            .row2 {{
                display:grid;
                grid-template-columns:repeat(2,minmax(0,1fr));
                gap:16px;
                margin-bottom:16px;
            }}
            .panel {{
                background:#fff;
                border:1px solid #dfe6f0;
                border-radius:10px;
                padding:18px;
                box-shadow:0 1px 2px rgba(16,24,40,.05);
            }}
            .panel h3 {{
                font-size:15px;
                font-weight:800;
                margin:0 0 16px;
                color:#182230;
            }}
            .panel h3 i {{ margin-right:8px; color:#0f766e; }}
            .chart_panel {{
                background:#fff;
                border:1px solid #dfe6f0;
                border-radius:10px;
                padding:18px;
                box-shadow:0 1px 2px rgba(16,24,40,.05);
                min-width:0;
            }}
            .chart_panel h3 {{
                font-size:15px;
                line-height:1.2;
                font-weight:800;
                margin:0 0 16px;
                color:#182230;
                display:flex;
                align-items:center;
                justify-content:space-between;
                gap:8px;
            }}
            .chart_panel h3 i {{ margin-right:8px; color:#0f766e; }}
            .chart_panel h3 .cap_lab_live {{ font-size:11px; color:#98a2b3; font-weight:700; text-transform:uppercase; }}
            .chart_body {{
                display:flex;
                gap:18px;
                align-items:center;
                flex-wrap:wrap;
            }}
            .chart_figure {{ flex:0 0 auto; margin:0; }}
            .chart_legend {{ flex:1 1 150px; display:grid; gap:10px; min-width:150px; }}
            .legend_item {{ display:grid; grid-template-columns:auto 1fr auto; gap:10px; align-items:center; font-size:13px; }}
            .legend_item b {{ white-space:nowrap; }}
            .legend_pct {{
                font-style:normal;
                color:#98a2b3;
                font-size:11px;
                font-weight:600;
                margin-left:6px;
            }}
            .swatch {{ width:12px; height:12px; border-radius:3px; }}
            .mini_grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-bottom:14px; }}
            .mini_metric {{ background:#f8fafc; border:1px solid #e4eaf2; border-radius:8px; padding:12px; }}
            .mini_metric b {{ display:block; font-size:20px; line-height:1; }}
            .mini_metric span {{ display:block; color:#667085; font-size:11px; margin-top:7px; text-transform:uppercase; font-weight:700; letter-spacing:.3px; }}
            .split {{
                display:flex;
                gap:20px;
                align-items:center;
                flex-wrap:wrap;
            }}
            .split .grow {{ flex:1 1 230px; min-width:0; }}
            .legend_inline {{ display:flex; align-items:center; gap:16px; flex-wrap:wrap; font-size:12px; font-weight:700; color:#475467; margin-top:10px; }}
            .legend_inline span {{ display:inline-flex; align-items:center; gap:6px; }}
            .status_grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }}
            .status_item {{ border:1px solid #e4eaf2; border-radius:8px; padding:12px; display:flex; justify-content:space-between; gap:10px; }}
            .status_item span {{ color:#667085; font-size:13px; }}
            .status_item b {{ font-size:18px; }}
            .ops_grid {{ display:grid; grid-template-columns:repeat(5,minmax(130px,1fr)); gap:10px; }}
            .ops_item {{ background:#f8fafc; border:1px solid #e4eaf2; border-radius:8px; padding:14px; }}
            .ops_item span {{ display:block; color:#667085; font-size:12px; }}
            .ops_item b {{ display:block; margin-top:8px; font-size:24px; line-height:1; }}
            /* ---- SVG chart styling ---- */
            .chart_svg {{ display:block; max-width:100%; }}
            .chart_grid {{ stroke:#eef2f6; stroke-width:1; }}
            .chart_grid_tick {{ stroke:#cbd5e1; stroke-width:1; }}
            .chart_axis {{ font-size:10px; fill:#98a2b3; font-weight:600; }}
            .chart_bar_val {{ font-size:12px; font-weight:800; fill:#182230; }}
            .chart_line_val {{ font-size:12px; font-weight:800; fill:#0f766e; }}
            .chart_bar {{ cursor:pointer; }}
            .chart_bar rect {{ transition:opacity .15s ease; }}
            .chart_bar:hover rect {{ opacity:.82; }}
            .chart_seg {{ cursor:pointer; }}
            .chart_seg path {{ transition:opacity .15s ease; }}
            .chart_seg:hover path {{ opacity:.85; }}
            .chart_dot {{ fill:#0f766e; stroke:#fff; stroke-width:2; cursor:pointer; }}
            .chart_cap {{ stroke:#94a3b8; stroke-width:1.5; stroke-dasharray:4 3; }}
            .cap_lab {{ font-size:11px; font-weight:800; fill:#fff; }}
            .chart_center_value {{ font-size:30px; font-weight:800; fill:#182230; }}
            .chart_center_label {{ font-size:11px; font-weight:700; fill:#667085; }}
            .chart_empty {{ font-size:13px; font-weight:700; fill:#98a2b3; }}
            .chart_empty_sub {{ font-size:11px; fill:#c1c8d2; }}
            .note_chip {{
                display:inline-flex;
                align-items:center;
                gap:7px;
                border-radius:7px;
                padding:7px 10px;
                font-size:12px;
                font-weight:700;
                background:#f8fafc;
                border:1px solid #e4eaf2;
                color:#344054;
            }}
            /* ---- Attendance Trend ---- */
            .atrend {{ min-width:0; }}
            .atrend_head {{
                display:flex;
                align-items:baseline;
                gap:12px;
                flex-wrap:wrap;
                margin:-2px 0 2px;
            }}
            .atrend_head h3 {{
                font-size:16px;
                font-weight:800;
                margin:0;
                color:#182230;
                flex:none;
            }}
            .atrend_head i {{ margin-right:7px; color:#0f766e; }}
            .atrend_sub {{
                font-size:11px;
                font-weight:700;
                letter-spacing:.06em;
                text-transform:uppercase;
                color:#98a2b3;
            }}
            .atrend_fig {{ width:100%; margin:12px 0 18px; }}
            .atrend_fig svg {{ width:100% !important; height:auto; }}
            .atrend_stats {{
                display:grid;
                grid-template-columns:repeat(4,minmax(0,1fr));
                gap:10px;
            }}
            .atrend .stat {{
                background:#f9fafb;
                border:1px solid #eef2f6;
                border-radius:6px;
                padding:14px 16px;
                display:flex;
                flex-direction:column;
                gap:8px;
                min-width:0;
                overflow:visible;
            }}
            .atrend .stat span {{
                color:#667085;
                font-size:12px;
                font-weight:600;
                white-space:nowrap;
            }}
            .atrend .stat b {{
                font-size:22px;
                font-weight:800;
                line-height:1.25;
                letter-spacing:-.2px;
            }}
            .atrend .stat .t-teal {{ color:#0891b2; }}
            .atrend .stat .t-blue {{ color:#0891b2; }}
            .atrend .stat .t-red {{ color:#ef4444; }}
            .atrend .stat .t-orange {{ color:#d97706; }}
            .atrend_note {{
                display:flex;
                align-items:center;
                gap:7px;
                margin:14px 0 0;
                font-size:12px;
                font-weight:600;
                color:#667085;
            }}
            .atrend_note i {{ color:#98a2b3; }}
            @media (max-width:1200px) {{
                .metric_grid {{ grid-template-columns:repeat(2,minmax(180px,1fr)); }}
                .analysis_grid {{ grid-template-columns:repeat(2,minmax(180px,1fr)); }}
                .row3 {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
                .row2 {{ grid-template-columns:1fr; }}
                .ops_grid {{ grid-template-columns:repeat(3,minmax(130px,1fr)); }}
            }}
            @media (max-width:700px) {{
                body:has(.school_dash) .o_main_navbar .o_menu_brand {{
                    min-width:auto;
                }}
                body:has(.school_dash) .o_main_navbar .o_menu_sections {{
                    position:static !important;
                    flex-direction:row;
                    width:auto;
                    height:auto;
                    padding:0;
                    overflow:visible;
                    border-right:0;
                    box-shadow:none;
                }}
                body:has(.school_dash) .o_action_manager {{
                    margin-left:0;
                    width:100%;
                }}
                .school_dash {{ padding:16px; }}
                .dash_head {{ grid-template-columns:1fr; align-items:start; }}
                .quick_actions {{ justify-content:flex-start; }}
                .metric_grid,
                .analysis_grid,
                .row2,
                .row3,
                .mini_grid,
                .status_grid,
                .ops_grid {{ grid-template-columns:1fr; }}
                .atrend_stats {{ grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }}
            }}
        </style>
        <div class="school_dash">
            <div class="dash_head">
                <div>
                    <h1>School Dashboard</h1>
                    <p>Live overview of student activity, classes, attendance, performance, and fees.</p>
                </div>
                <div>
                    <span class="dash_live"><i class="fa fa-refresh" title="Updated"></i> Updated just now</span>
                    <div class="quick_actions" style="margin-top:10px">
                        <a href="{actions['students']}"><i class="fa fa-user-plus" title="Students"></i> Students</a>
                        <a href="{actions['attendance']}"><i class="fa fa-calendar-check-o" title="Attendance"></i> Attendance</a>
                        <a href="{actions['fees']}"><i class="fa fa-credit-card" title="Fees"></i> Fees</a>
                    </div>
                </div>
            </div>
            <div class="metric_grid">
                <a class="metric_card" href="{actions['students']}"><div><div class="metric_label">Students</div><div class="metric_value">{c['student_count']}</div><div class="metric_hint">{c['active_students']} active enrollment</div></div><div class="metric_icon" style="background:#2563eb"><i class="fa fa-graduation-cap" title="Students"></i></div></a>
                <a class="metric_card" href="{actions['teachers']}"><div><div class="metric_label">Teachers</div><div class="metric_value">{c['teacher_count']}</div><div class="metric_hint">Faculty records</div></div><div class="metric_icon" style="background:#0891b2"><i class="fa fa-users" title="Teachers"></i></div></a>
                <a class="metric_card" href="{actions['classes']}"><div><div class="metric_label">Classes</div><div class="metric_value">{c['class_count']}</div><div class="metric_hint">{c['avg_students_per_class']} average size</div></div><div class="metric_icon" style="background:#0f766e"><i class="fa fa-building" title="Classes"></i></div></a>
                <a class="metric_card" href="{actions['subjects']}"><div><div class="metric_label">Subjects</div><div class="metric_value">{c['subject_count']}</div><div class="metric_hint">Academic catalog</div></div><div class="metric_icon" style="background:#d97706"><i class="fa fa-book" title="Subjects"></i></div></a>
            </div>
            <div class="analysis_grid">
                <a class="analysis_card" href="{actions['grades']}" style="border-left-color:#2563eb">
                    <div class="analysis_top"><span>Academic Health</span><i class="fa fa-line-chart" title="Academic health"></i></div>
                    <div class="analysis_value" style="color:#2563eb">{c['pass_rate']}%</div>
                    <div class="analysis_note">{c['passed_grades']} passing grade records out of {c['grade_count']} total.</div>
                </a>
                <a class="analysis_card" href="{actions['attendance']}" style="border-left-color:#0891b2">
                    <div class="analysis_top"><span>Attendance Health</span><i class="fa fa-calendar" title="Attendance health"></i></div>
                    <div class="analysis_value" style="color:#0891b2">{c['attendance_rate']}%</div>
                    <div class="analysis_note">{c['absence_rate']}% absence impact across attendance records.</div>
                </a>
                <a class="analysis_card" href="{actions['fees']}" style="border-left-color:#0f766e">
                    <div class="analysis_top"><span>Fee Collection</span><i class="fa fa-money" title="Fee collection"></i></div>
                    <div class="analysis_value" style="color:#0f766e">{c['fee_collection_rate']}%</div>
                    <div class="analysis_note">{c['open_fee_count']} fee records still pending, partial, or overdue.</div>
                </a>
                <a class="analysis_card" href="{actions['classes']}" style="border-left-color:#d97706">
                    <div class="analysis_top"><span>Capacity Use</span><i class="fa fa-sitemap" title="Capacity use"></i></div>
                    <div class="analysis_value" style="color:#d97706">{c['capacity_rate']}%</div>
                    <div class="analysis_note">Top class: {escape(str(c['top_class_name']))} with {c['top_class_students']} students.</div>
                </a>
            </div>
            <div class="charts_head">
                <h2><i class="fa fa-bar-chart" title="Analytics"></i> Visual Analytics</h2>
                <span>Charts rendered live from the current school records</span>
            </div>
            <div class="row3">
                <div class="chart_panel">
                    <h3><i class="fa fa-pie-chart" title="Demographics"></i> Student Demographics<span class="cap_lab_live">By gender</span></h3>
                    <div class="chart_body">
                        <figure class="chart_figure">{gend_donut}</figure>
                        <div class="chart_legend">{gend_legend}</div>
                    </div>
                </div>
                <div class="chart_panel">
                    <h3><i class="fa fa-calendar-check-o" title="Attendance"></i> Attendance Distribution<span class="cap_lab_live">By status</span></h3>
                    <div class="chart_body">
                        <figure class="chart_figure">{att_donut}</figure>
                        <div class="chart_legend">{att_legend}</div>
                    </div>
                </div>
                <div class="chart_panel">
                    <h3><i class="fa fa-credit-card" title="Fees"></i> Fee Collection Status<span class="cap_lab_live">By status</span></h3>
                    <div class="chart_body">
                        <figure class="chart_figure">{fee_donut}</figure>
                        <div class="chart_legend">{fee_legend}</div>
                    </div>
                </div>
            </div>
            <div class="row2">
                <div class="chart_panel">
                    <h3><i class="fa fa-graduation-cap" title="Results"></i> Academic Performance<span class="cap_lab_live">Score bands</span></h3>
                    <div class="chart_body">
                        <figure class="chart_figure">{grade_bars}</figure>
                        <div class="split grow">
                            <figure class="chart_figure">{pf_donut}</figure>
                            <div class="chart_legend">{pf_legend}</div>
                        </div>
                    </div>
                    <div class="status_grid" style="margin-top:14px">
                        <div class="status_item"><span>Average Score</span><b style="color:#10b981">{c['avg_percentage']}%</b></div>
                        <div class="status_item"><span>Grade Records</span><b>{c['grade_count']}</b></div>
                    </div>
                </div>
                <div class="chart_panel">
                    <h3><i class="fa fa-money" title="Revenue"></i> Fee Revenue by Type<span class="cap_lab_live">Billed vs collected</span></h3>
                    <div class="chart_body">
                        <figure class="chart_figure">{fee_bars}</figure>
                        <div class="chart_legend">
                            <div class="legend_inline">
                                <span><span class="swatch" style="background:{T_SLATE}"></span>Billed</span>
                                <span><span class="swatch" style="background:{T_TEAL}"></span>Collected</span>
                            </div>
                            <div class="mini_grid">
                                <div class="mini_metric"><b>{self._fmt(c['total_fee_amount'])}</b><span>Total Billed</span></div>
                                <div class="mini_metric"><b style="color:#0f766e">{self._fmt(c['total_paid_amount'])}</b><span>Collected</span></div>
                                <div class="mini_metric"><b style="color:#dc2626">{self._fmt(c['total_balance'])}</b><span>Outstanding</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row2">
                <div class="chart_panel atrend">
                    <div class="atrend_head">
                        <h3><i class="fa fa-line-chart" title="Trend"></i> Attendance Trend</h3>
                        <span class="atrend_sub">Monthly Rate</span>
                    </div>
                    <figure class="chart_figure atrend_fig">{trend_line}</figure>
                    <div class="atrend_stats">
                        <div class="stat"><span>Overall Rate</span><b class="t-teal">{c['attendance_rate']}%</b></div>
                        <div class="stat"><span>Absent</span><b class="t-red">{c['absent_attendance']}</b></div>
                        <div class="stat"><span>Late</span><b class="t-orange">{c['late_attendance']}</b></div>
                        <div class="stat"><span>Excused</span><b class="t-blue">{c['excused_attendance']}</b></div>
                    </div>
                    <p class="atrend_note"><i class="fa fa-info-circle" title="Info"></i> Present, late and excused count toward the rate.</p>
                </div>
                <div class="chart_panel">
                    <h3><i class="fa fa-building-o" title="Occupancy"></i> Class Occupancy<span class="cap_lab_live">Students vs capacity</span></h3>
                    <div class="chart_body">
                        <figure class="chart_figure">{occ_bars}</figure>
                        <div class="chart_legend">
                            <div class="status_grid">
                                <div class="status_item"><span>Capacity Use</span><b style="color:#d97706">{c['capacity_rate']}%</b></div>
                                <div class="status_item"><span>Top Class</span><b style="color:#0f766e">{escape(str(c['top_class_name']))}</b></div>
                            </div>
                            <span class="note_chip"><i class="fa fa-info-circle" title="Info"></i> Dashed markers show each class capacity.</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="panel" style="margin-top:6px">
                <h3><i class="fa fa-clipboard-list"></i> Operational Activity</h3>
                <div class="ops_grid">
                    <div class="ops_item"><span>Active Students</span><b>{c['active_students']}</b></div>
                    <div class="ops_item"><span>Exams Scheduled</span><b>{c['exam_count']}</b></div>
                    <div class="ops_item"><span>Grade Records</span><b>{c['grade_count']}</b></div>
                    <div class="ops_item"><span>Attendance Records</span><b>{c['attendance_count']}</b></div>
                    <div class="ops_item"><span>Fee Records</span><b>{c['fee_count']}</b></div>
                </div>
            </div>
        </div>
        '''