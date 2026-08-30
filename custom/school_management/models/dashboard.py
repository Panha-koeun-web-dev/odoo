from html import escape

from odoo import models, fields, api, _


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
            for school_class in classes.sorted(lambda cls: cls.student_count, reverse=True)[:5]
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

    def _render_html(self, c):
        actions = c['actions']
        class_rows = ''.join(
            f'''
            <div class="class_row">
                <div>
                    <b>{escape(str(row['name']))}</b>
                    <span>{row['students']} / {row['capacity'] or 0} students</span>
                </div>
                <div class="class_meter">
                    <div style="width:{min(row['rate'], 100)}%;"></div>
                </div>
                <strong>{row['rate']}%</strong>
            </div>
            '''
            for row in c['class_rows']
        ) or '<div class="empty_state">No class enrollment data yet.</div>'

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
            .main_grid {{
                display:grid;
                grid-template-columns:minmax(420px,1.2fr) minmax(360px,.8fr);
                gap:18px;
                margin-bottom:18px;
            }}
            .panel {{
                background:#fff;
                border:1px solid #dfe6f0;
                border-radius:8px;
                padding:20px;
                box-shadow:0 1px 2px rgba(16,24,40,.04);
            }}
            .panel h3 {{
                font-size:16px;
                line-height:1.2;
                font-weight:800;
                margin:0 0 18px;
                color:#182230;
            }}
            .panel h3 i {{ margin-right:8px; color:#0f766e; }}
            .score_row {{
                display:grid;
                grid-template-columns:repeat(2,minmax(0,1fr));
                gap:14px;
                margin-bottom:18px;
            }}
            .score_value {{ font-size:36px; line-height:1; font-weight:800; }}
            .score_label {{ margin-top:6px; color:#667085; font-size:13px; }}
            .dash_line {{ display:flex; align-items:center; justify-content:space-between; gap:14px; padding:10px 0; font-size:14px; }}
            .dash_line + .dash_line {{ border-top:1px solid #eef2f6; }}
            .muted {{ color:#667085; }}
            .strong {{ font-weight:800; color:#182230; }}
            .progress_track {{ height:9px; background:#e9eef5; border-radius:999px; overflow:hidden; margin-bottom:14px; }}
            .progress_fill {{ height:100%; border-radius:999px; }}
            .legend {{ display:grid; gap:12px; }}
            .legend_item {{ display:grid; grid-template-columns:auto 1fr auto; gap:10px; align-items:center; font-size:14px; }}
            .swatch {{ width:12px; height:12px; border-radius:3px; }}
            .mini_grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-bottom:14px; }}
            .mini_metric {{ background:#f8fafc; border:1px solid #e4eaf2; border-radius:8px; padding:12px; }}
            .mini_metric b {{ display:block; font-size:20px; line-height:1; }}
            .mini_metric span {{ display:block; color:#667085; font-size:12px; margin-top:7px; }}
            .status_grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }}
            .status_item {{ border:1px solid #e4eaf2; border-radius:8px; padding:12px; display:flex; justify-content:space-between; gap:10px; }}
            .status_item span {{ color:#667085; font-size:13px; }}
            .status_item b {{ font-size:18px; }}
            .ops_grid {{ display:grid; grid-template-columns:repeat(5,minmax(130px,1fr)); gap:10px; }}
            .ops_item {{ background:#f8fafc; border:1px solid #e4eaf2; border-radius:8px; padding:14px; }}
            .ops_item span {{ display:block; color:#667085; font-size:12px; }}
            .ops_item b {{ display:block; margin-top:8px; font-size:24px; line-height:1; }}
            .class_list {{ display:grid; gap:10px; }}
            .class_row {{
                display:grid;
                grid-template-columns:minmax(150px,1fr) minmax(160px,1fr) auto;
                gap:14px;
                align-items:center;
                padding:12px;
                border:1px solid #e4eaf2;
                border-radius:8px;
                background:#f8fafc;
            }}
            .class_row b {{ display:block; font-size:14px; }}
            .class_row span {{ display:block; color:#667085; font-size:12px; margin-top:3px; }}
            .class_meter {{ height:8px; background:#e9eef5; border-radius:999px; overflow:hidden; }}
            .class_meter div {{ height:100%; border-radius:999px; background:#0f766e; }}
            .empty_state {{ color:#667085; font-size:13px; padding:14px; border:1px dashed #cbd5e1; border-radius:8px; }}
            @media (max-width:1200px) {{
                .metric_grid {{ grid-template-columns:repeat(2,minmax(180px,1fr)); }}
                .analysis_grid {{ grid-template-columns:repeat(2,minmax(180px,1fr)); }}
                .main_grid {{ grid-template-columns:1fr; }}
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
                .score_row,
                .mini_grid,
                .status_grid,
                .ops_grid {{ grid-template-columns:1fr; }}
                .class_row {{ grid-template-columns:1fr; }}
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
            <div class="main_grid">
                <div class="panel">
                    <h3><i class="fa fa-bar-chart"></i>Academic Performance</h3>
                    <div class="score_row">
                        <div><div class="score_value" style="color:#0f766e">{c['avg_percentage']}%</div><div class="score_label">Average Score</div></div>
                        <div><div class="score_value" style="color:#2563eb">{c['pass_rate']}%</div><div class="score_label">Pass Rate</div></div>
                    </div>
                    <div class="dash_line"><span class="muted">Passed</span><span class="strong">{c['passed_grades']} / {c['grade_count']}</span></div>
                    <div class="progress_track"><div class="progress_fill" style="width:{c['pass_rate']}%;background:#10b981"></div></div>
                    <div class="dash_line"><span class="muted">Failed</span><span class="strong">{c['failed_grades']}</span></div>
                    <div class="progress_track"><div class="progress_fill" style="width:{100 - c['pass_rate']}%;background:#ef4444"></div></div>
                </div>
                <div class="panel">
                    <h3><i class="fa fa-pie-chart"></i>Student Demographics</h3>
                    <div class="legend">
                        <div class="legend_item"><span class="swatch" style="background:#2563eb"></span><span>Female ({c['female_count']})</span><b>{c['female_students']}%</b></div>
                        <div class="legend_item"><span class="swatch" style="background:#d97706"></span><span>Male ({c['male_count']})</span><b>{c['male_students']}%</b></div>
                        <div class="legend_item"><span class="swatch" style="background:#7c3aed"></span><span>Other ({c['other_count']})</span><b>{c['other_students']}%</b></div>
                    </div>
                </div>
            </div>
            <div class="main_grid">
                <div class="panel">
                    <h3><i class="fa fa-money"></i>Fee Management</h3>
                    <div class="mini_grid">
                        <div class="mini_metric"><b>{c['total_fee_amount']:.0f}</b><span>Total Billed</span></div>
                        <div class="mini_metric"><b style="color:#0f766e">{c['total_paid_amount']:.0f}</b><span>Collected</span></div>
                        <div class="mini_metric"><b style="color:#dc2626">{c['total_balance']:.0f}</b><span>Outstanding</span></div>
                    </div>
                    <div class="status_grid">
                        <div class="status_item"><span>Paid</span><b style="color:#0f766e">{c['paid_fees']}</b></div>
                        <div class="status_item"><span>Pending</span><b style="color:#d97706">{c['pending_fees']}</b></div>
                        <div class="status_item"><span>Overdue</span><b style="color:#dc2626">{c['overdue_fees']}</b></div>
                        <div class="status_item"><span>Partial</span><b style="color:#2563eb">{c['partial_fees']}</b></div>
                    </div>
                </div>
                <div class="panel">
                    <h3><i class="fa fa-calendar-check-o"></i>Attendance Overview</h3>
                    <div class="score_value" style="color:#0891b2">{c['attendance_rate']}%</div>
                    <div class="score_label">Overall Attendance</div>
                    <div class="dash_line"><span class="muted">Present</span><span class="strong">{c['present_attendance']}</span></div>
                    <div class="dash_line"><span class="muted">Late</span><span class="strong">{c['late_attendance']}</span></div>
                    <div class="dash_line"><span class="muted">Excused</span><span class="strong">{c['excused_attendance']}</span></div>
                    <div class="dash_line"><span class="muted">Absent</span><span class="strong" style="color:#dc2626">{c['absent_attendance']}</span></div>
                </div>
            </div>
            <div class="panel">
                <h3><i class="fa fa-clipboard-list"></i>Operational Activity</h3>
                <div class="ops_grid">
                    <div class="ops_item"><span>Active Students</span><b>{c['active_students']}</b></div>
                    <div class="ops_item"><span>Exams Scheduled</span><b>{c['exam_count']}</b></div>
                    <div class="ops_item"><span>Grade Records</span><b>{c['grade_count']}</b></div>
                    <div class="ops_item"><span>Attendance Records</span><b>{c['attendance_count']}</b></div>
                    <div class="ops_item"><span>Fee Records</span><b>{c['fee_count']}</b></div>
                </div>
            </div>
            <div class="panel" style="margin-top:18px">
                <h3><i class="fa fa-building-o"></i>Class Occupancy Analysis</h3>
                <div class="class_list">
                    {class_rows}
                </div>
            </div>
        </div>
        '''
