from datetime import datetime, date, time, timedelta
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


DAY_SELECTION = [
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
]

PERIOD_SELECTION = [
    ('p1', 'Period 1 (08:00 - 09:00)'),
    ('p2', 'Period 2 (09:15 - 10:15)'),
    ('p3', 'Period 3 (10:25 - 11:25)'),
    ('p4', 'Period 4 (11:25 - 12:25)'),
    ('p5', 'Period 5 (13:30 - 14:30)'),
    ('p6', 'Period 6 (14:30 - 15:30)'),
    ('p7', 'Period 7 (15:45 - 16:45)'),
    ('custom', 'Custom Time Window'),
]

PERIOD_PRESETS = {
    'p1': (8.0, 9.0),
    'p2': (9.25, 10.25),
    'p3': (10.25, 11.25),
    'p4': (11.25, 12.25),
    'p5': (13.5, 14.5),
    'p6': (14.5, 15.5),
    'p7': (15.75, 16.75),
}


class SchoolTimetable(models.Model):
    _name = 'school.timetable'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Class Timetable & Teaching Schedule'
    _order = 'day_of_week, start_time, class_id'
    _rec_name = 'display_name'

    name = fields.Char(string='Session Title', tracking=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    class_id = fields.Many2one(
        'school.class',
        string='Class',
        required=False,
        tracking=True,
        index=True,
        ondelete='cascade'
    )
    student_id = fields.Many2one(
        'school.student',
        string='Specific Student',
        tracking=True,
        index=True,
        help="Optional: set specific student for 1-on-1 tutoring, remedial study, or personalized schedule. If blank, session applies to the entire class."
    )
    student_ids = fields.Many2many(
        'school.student',
        'school_timetable_school_student_rel',
        'timetable_id',
        'student_id',
        string='Enrolled / Assigned Students',
        compute='_compute_student_ids',
        store=True,
        readonly=False,
        help="All students participating in this schedule session (supports individuals, group tutoring, or classes)."
    )
    subject_ids = fields.Many2many(
        'school.subject',
        'school_timetable_subject_rel',
        'timetable_id',
        'subject_id',
        string='Subjects',
        compute='_compute_subject_ids',
        store=True,
        readonly=False,
        tracking=True,
        help="Subjects covered in this session. You can select one or multiple subjects (e.g. Mathematics, Physics for joint/STEM lessons)."
    )
    subject_id = fields.Many2one(
        'school.subject',
        string='Primary Subject',
        compute='_compute_subject_id',
        store=True,
        readonly=False,
        tracking=True,
        index=True,
        help="Primary subject for calendar color coding and legacy compatibility."
    )
    subjects_display = fields.Char(
        string='Subjects Summary',
        compute='_compute_subjects_display',
        store=True,
        help="Display names of all subjects in this session."
    )
    teacher_id = fields.Many2one(
        'school.teacher',
        string='Teacher',
        required=True,
        tracking=True,
        index=True
    )
    day_of_week = fields.Selection(
        DAY_SELECTION,
        string='Day of Week',
        required=True,
        default='0',
        tracking=True,
        index=True
    )
    period = fields.Selection(
        PERIOD_SELECTION,
        string='Period',
        default='p1',
        tracking=True
    )
    start_time = fields.Float(
        string='Start Time',
        default=8.0,
        required=True,
        tracking=True
    )
    end_time = fields.Float(
        string='End Time',
        default=9.0,
        required=True,
        tracking=True
    )
    room = fields.Char(
        string='Classroom / Room',
        tracking=True,
        help="Classroom or hall where this session takes place."
    )
    start_datetime = fields.Datetime(
        string='Session Start',
        required=True,
        tracking=True,
        index=True,
        help="UTC timestamp representing the scheduled session start."
    )
    end_datetime = fields.Datetime(
        string='Session End',
        required=True,
        tracking=True,
        index=True,
        help="UTC timestamp representing the scheduled session end."
    )
    color = fields.Integer(
        string='Color Index',
        compute='_compute_color',
        store=True
    )
    notes = fields.Text(string='Notes / Instructions')
    active = fields.Boolean(default=True, tracking=True)

    # -------------------------------------------------------------------------
    # TIME & TIMEZONE HELPERS
    # -------------------------------------------------------------------------
    def _get_user_tz(self):
        return pytz.timezone(self.env.user.tz or 'UTC')

    def _get_current_week_monday(self):
        today = fields.Date.context_today(self)
        return today - timedelta(days=today.weekday())

    def _format_time(self, float_hour):
        if float_hour is None:
            return "00:00"
        h = int(float_hour)
        m = int(round((float_hour - h) * 60))
        if m >= 60:
            h += 1
            m = 0
        return f"{h:02d}:{m:02d}"

    def _local_to_utc(self, target_date, float_hour):
        tz = self._get_user_tz()
        hours = int(float_hour)
        minutes = int(round((float_hour - hours) * 60))
        if minutes >= 60:
            hours += 1
            minutes = 0
        if hours >= 24:
            hours = 23
            minutes = 59
        naive_dt = datetime.combine(target_date, time(hours, minutes))
        try:
            local_dt = tz.localize(naive_dt, is_dst=None)
            return local_dt.astimezone(pytz.utc).replace(tzinfo=None)
        except Exception:
            return naive_dt

    def _utc_to_local(self, dt):
        if not dt:
            return None
        if isinstance(dt, str):
            dt = fields.Datetime.to_datetime(dt)
        tz = self._get_user_tz()
        try:
            utc_dt = pytz.utc.localize(dt)
            return utc_dt.astimezone(tz)
        except Exception:
            return dt

    def _calculate_datetimes(self, day_of_week, start_time, end_time):
        monday = self._get_current_week_monday()
        day_idx = int(day_of_week) if day_of_week else 0
        target_date = monday + timedelta(days=day_idx)
        start_dt = self._local_to_utc(target_date, start_time or 8.0)
        end_dt = self._local_to_utc(target_date, end_time or 9.0)
        return start_dt, end_dt

    def _match_period(self, start_time, end_time):
        for p_key, (p_start, p_end) in PERIOD_PRESETS.items():
            if abs(start_time - p_start) < 0.02 and abs(end_time - p_end) < 0.02:
                return p_key
        return 'custom'

    # -------------------------------------------------------------------------
    # DEFAULTS & COMPUTATIONS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx_start = self.env.context.get('default_start_datetime')
        ctx_end = self.env.context.get('default_end_datetime')

        if ctx_start and ctx_end:
            local_start = self._utc_to_local(ctx_start)
            local_end = self._utc_to_local(ctx_end)
            if local_start and local_end:
                day_str = str(local_start.weekday())
                s_time = round(local_start.hour + local_start.minute / 60.0, 2)
                e_time = round(local_end.hour + local_end.minute / 60.0, 2)
                res.update({
                    'day_of_week': day_str,
                    'start_time': s_time,
                    'end_time': e_time,
                    'period': self._match_period(s_time, e_time),
                    'start_datetime': ctx_start,
                    'end_datetime': ctx_end,
                })
        else:
            day_str = res.get('day_of_week', '0')
            period_val = res.get('period', 'p1')
            if period_val in PERIOD_PRESETS:
                s_time, e_time = PERIOD_PRESETS[period_val]
            else:
                s_time = res.get('start_time', 8.0)
                e_time = res.get('end_time', 9.0)
            res['start_time'] = s_time
            res['end_time'] = e_time
            if 'start_datetime' in fields_list or 'end_datetime' in fields_list:
                s_dt, e_dt = self._calculate_datetimes(day_str, s_time, e_time)
                res.setdefault('start_datetime', s_dt)
                res.setdefault('end_datetime', e_dt)

        return res

    @api.depends('subject_ids')
    def _compute_subject_id(self):
        for rec in self:
            if rec.subject_ids:
                if not rec.subject_id or rec.subject_id not in rec.subject_ids:
                    rec.subject_id = rec.subject_ids[0]
            elif not rec.subject_ids and not rec.subject_id:
                rec.subject_id = False

    @api.depends('subject_id')
    def _compute_subject_ids(self):
        for rec in self:
            if rec.subject_id and not rec.subject_ids:
                rec.subject_ids = [(6, 0, [rec.subject_id.id])]
            elif not rec.subject_id and not rec.subject_ids:
                rec.subject_ids = False

    @api.depends('subject_ids', 'subject_id', 'subject_ids.name', 'subject_id.name')
    def _compute_subjects_display(self):
        for rec in self:
            subs = rec.subject_ids or (rec.subject_id if rec.subject_id else self.env['school.subject'])
            rec.subjects_display = ', '.join(subs.mapped('name')) if subs else (rec.subject_id.name or '')

    @api.depends('student_id', 'class_id.student_ids')
    def _compute_student_ids(self):
        for rec in self:
            if rec.class_id:
                rec.student_ids = [(6, 0, rec.class_id.student_ids.ids)]
            elif rec.student_id:
                rec.student_ids = [(6, 0, [rec.student_id.id])]
            elif not rec.student_ids:
                rec.student_ids = False

    @api.depends('class_id.name', 'student_id.name', 'subject_id.name', 'subject_ids.name', 'day_of_week', 'start_time', 'end_time', 'room', 'name')
    def _compute_display_name(self):
        days = dict(DAY_SELECTION)
        for rec in self:
            day_str = days.get(rec.day_of_week, '')
            start_str = rec._format_time(rec.start_time)
            end_str = rec._format_time(rec.end_time)
            subs = rec.subject_ids or (rec.subject_id if rec.subject_id else self.env['school.subject'])
            subject_name = ', '.join(subs.mapped('name')) if subs else (rec.subject_id.name or _("Subject"))
            target_name = rec.student_id.name or (rec.class_id.name if rec.class_id else _("Session"))
            room_str = f" [{rec.room}]" if rec.room else ""
            if rec.name and rec.name != f"{target_name} - {subject_name}":
                rec.display_name = f"[{target_name}] {rec.name} ({day_str} {start_str}-{end_str}){room_str}"
            else:
                rec.display_name = f"[{target_name}] {subject_name} ({day_str} {start_str}-{end_str}){room_str}"

    @api.depends('subject_id', 'class_id', 'teacher_id')
    def _compute_color(self):
        for rec in self:
            if rec.teacher_id:
                rec.color = (rec.teacher_id.id * 3 + 1) % 11 + 1
            elif rec.subject_id:
                rec.color = (rec.subject_id.id * 3 + 1) % 11 + 1
            elif rec.class_id:
                rec.color = (rec.class_id.id * 2 + 1) % 11 + 1
            else:
                rec.color = 1

    # -------------------------------------------------------------------------
    # ONCHANGES
    # -------------------------------------------------------------------------
    @api.onchange('subject_ids')
    def _onchange_subject_ids(self):
        if self.subject_ids:
            if not self.subject_id or self.subject_id not in self.subject_ids:
                self.subject_id = self.subject_ids[0]
        else:
            self.subject_id = False

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            if self.student_id.class_id and not self.class_id:
                self.class_id = self.student_id.class_id
            active_studies = self.student_id.study_subject_ids.filtered(lambda s: s.study_status == 'active')
            if active_studies and not self.subject_ids and not self.subject_id:
                self.subject_ids = [(6, 0, [active_studies[0].subject_id.id])]
                self.subject_id = active_studies[0].subject_id
                if active_studies[0].teacher_id and not self.teacher_id:
                    self.teacher_id = active_studies[0].teacher_id

    @api.onchange('teacher_id')
    def _onchange_teacher_id(self):
        if self.teacher_id:
            assignments = self.teacher_id.teaching_assignment_ids.filtered(lambda a: a.active)
            teacher_subjects = self.teacher_id.subject_ids | assignments.mapped('subject_id')
            if teacher_subjects and not self.subject_ids and not self.subject_id:
                self.subject_ids = [(6, 0, [teacher_subjects[0].id])]
                self.subject_id = teacher_subjects[0]
            if assignments and not self.class_id and assignments[0].class_id:
                self.class_id = assignments[0].class_id

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            if not self.room and self.class_id.room:
                self.room = self.class_id.room
            if not self.teacher_id and self.class_id.teacher_id:
                self.teacher_id = self.class_id.teacher_id
            assignments = self.class_id.teaching_assignment_ids.filtered(lambda a: a.active)
            if assignments and not self.subject_ids and not self.subject_id:
                self.subject_ids = [(6, 0, [assignments[0].subject_id.id])]
                self.subject_id = assignments[0].subject_id
                if assignments[0].teacher_id and not self.teacher_id:
                    self.teacher_id = assignments[0].teacher_id

    @api.onchange('class_id', 'subject_ids', 'subject_id')
    def _onchange_class_subject(self):
        sub = self.subject_id or (self.subject_ids[0] if self.subject_ids else False)
        if self.class_id and sub and not self.teacher_id:
            asg = self.env['school.teaching.assignment'].search([
                ('class_id', '=', self.class_id.id),
                ('subject_id', '=', sub.id),
                ('active', '=', True),
            ], limit=1)
            if asg and asg.teacher_id:
                self.teacher_id = asg.teacher_id

    @api.onchange('period')
    def _onchange_period(self):
        if self.period and self.period in PERIOD_PRESETS:
            s_time, e_time = PERIOD_PRESETS[self.period]
            self.start_time = s_time
            self.end_time = e_time
            if self.day_of_week:
                s_dt, e_dt = self._calculate_datetimes(self.day_of_week, s_time, e_time)
                self.start_datetime = s_dt
                self.end_datetime = e_dt

    @api.onchange('day_of_week', 'start_time', 'end_time')
    def _onchange_timing(self):
        if self.start_time is not None and self.end_time is not None:
            self.period = self._match_period(self.start_time, self.end_time)
        if self.day_of_week and self.start_time is not None and self.end_time is not None:
            s_dt, e_dt = self._calculate_datetimes(self.day_of_week, self.start_time, self.end_time)
            self.start_datetime = s_dt
            self.end_datetime = e_dt

    @api.onchange('start_datetime', 'end_datetime')
    def _onchange_datetimes(self):
        if self.start_datetime and self.end_datetime:
            local_start = self._utc_to_local(self.start_datetime)
            local_end = self._utc_to_local(self.end_datetime)
            if local_start and local_end:
                self.day_of_week = str(local_start.weekday())
                self.start_time = round(local_start.hour + local_start.minute / 60.0, 2)
                self.end_time = round(local_end.hour + local_end.minute / 60.0, 2)
                self.period = self._match_period(self.start_time, self.end_time)

    # -------------------------------------------------------------------------
    # CRUD SYNC
    # -------------------------------------------------------------------------
    def _sync_timetable_vals(self, vals):
        target_name = ''
        if vals.get('student_id'):
            target_name = self.env['school.student'].browse(vals['student_id']).name or ''
        elif vals.get('class_id'):
            target_name = self.env['school.class'].browse(vals['class_id']).name or ''

        extracted_sub_ids = []
        if vals.get('subject_ids'):
            for cmd in vals['subject_ids']:
                if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 6:
                    extracted_sub_ids.extend(cmd[2])
                elif isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 4:
                    extracted_sub_ids.append(cmd[1])
                elif isinstance(cmd, int):
                    extracted_sub_ids.append(cmd)
            if extracted_sub_ids and not vals.get('subject_id'):
                vals['subject_id'] = extracted_sub_ids[0]
        elif vals.get('subject_id') and not vals.get('subject_ids'):
            vals['subject_ids'] = [(6, 0, [vals['subject_id']])]
            extracted_sub_ids = [vals['subject_id']]

        if not vals.get('name') and target_name and extracted_sub_ids:
            s_names = ', '.join(self.env['school.subject'].browse(extracted_sub_ids).mapped('name'))
            vals['name'] = f"{s_names} - {target_name}".strip(' -')

        if 'start_datetime' in vals and 'end_datetime' in vals and ('day_of_week' not in vals or 'start_time' not in vals):
            local_start = self._utc_to_local(vals['start_datetime'])
            local_end = self._utc_to_local(vals['end_datetime'])
            if local_start and local_end:
                vals['day_of_week'] = str(local_start.weekday())
                vals['start_time'] = round(local_start.hour + local_start.minute / 60.0, 2)
                vals['end_time'] = round(local_end.hour + local_end.minute / 60.0, 2)
                if 'period' not in vals:
                    vals['period'] = self._match_period(vals['start_time'], vals['end_time'])
        elif ('day_of_week' in vals or 'start_time' in vals or 'end_time' in vals) and ('start_datetime' not in vals):
            d_val = vals.get('day_of_week', '0')
            if vals.get('period') in PERIOD_PRESETS and 'start_time' not in vals:
                vals['start_time'], vals['end_time'] = PERIOD_PRESETS[vals['period']]
            s_val = vals.get('start_time', 8.0)
            e_val = vals.get('end_time', 9.0)
            if 'period' not in vals:
                vals['period'] = self._match_period(s_val, e_val)
            s_dt, e_dt = self._calculate_datetimes(d_val, s_val, e_val)
            vals['start_datetime'] = s_dt
            vals['end_datetime'] = e_dt

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-fill class from student if student given but no class
            if vals.get('student_id') and not vals.get('class_id'):
                student = self.env['school.student'].browse(vals['student_id'])
                if student.class_id:
                    vals['class_id'] = student.class_id.id
            self._sync_timetable_vals(vals)
        records = super().create(vals_list)
        for rec in records:
            if rec.teacher_id:
                subs = rec.subject_ids or (rec.subject_id if rec.subject_id else self.env['school.subject'])
                for sub in subs:
                    if sub not in rec.teacher_id.subject_ids:
                        rec.teacher_id.subject_ids = [(4, sub.id)]
        records._trigger_recompute_stats()
        return records

    def write(self, vals):
        for rec in self:
            merged = dict(vals)
            has_dt = 'start_datetime' in merged or 'end_datetime' in merged
            has_timing = 'day_of_week' in merged or 'start_time' in merged or 'end_time' in merged or 'period' in merged

            if has_dt and not has_timing:
                s_dt = merged.get('start_datetime', rec.start_datetime)
                e_dt = merged.get('end_datetime', rec.end_datetime)
                local_start = rec._utc_to_local(s_dt)
                local_end = rec._utc_to_local(e_dt)
                if local_start and local_end:
                    merged['day_of_week'] = str(local_start.weekday())
                    s_time = round(local_start.hour + local_start.minute / 60.0, 2)
                    e_time = round(local_end.hour + local_end.minute / 60.0, 2)
                    merged['start_time'] = s_time
                    merged['end_time'] = e_time
                    merged['period'] = rec._match_period(s_time, e_time)
            elif has_timing and not has_dt:
                if merged.get('period') in PERIOD_PRESETS and 'start_time' not in merged:
                    merged['start_time'], merged['end_time'] = PERIOD_PRESETS[merged['period']]
                day_str = merged.get('day_of_week', rec.day_of_week)
                s_time = merged.get('start_time', rec.start_time)
                e_time = merged.get('end_time', rec.end_time)
                if 'period' not in merged:
                    merged['period'] = rec._match_period(s_time, e_time)
                s_dt, e_dt = rec._calculate_datetimes(day_str, s_time, e_time)
                merged['start_datetime'] = s_dt
                merged['end_datetime'] = e_dt

            super(SchoolTimetable, rec).write(merged)
            if 'subject_ids' in merged and 'subject_id' not in merged:
                extracted = []
                for cmd in merged['subject_ids']:
                    if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 6:
                        extracted.extend(cmd[2])
                    elif isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 4:
                        extracted.append(cmd[1])
                if extracted:
                    merged['subject_id'] = extracted[0]

            if rec.teacher_id:
                subs = rec.subject_ids or (rec.subject_id if rec.subject_id else self.env['school.subject'])
                for sub in subs:
                    if sub not in rec.teacher_id.subject_ids:
                        rec.teacher_id.subject_ids = [(4, sub.id)]
        self._trigger_recompute_stats()
        return True

    def unlink(self):
        classes = self.mapped('class_id')
        subjects = self.mapped('subject_ids') | self.mapped('subject_id')
        teachers = self.mapped('teacher_id')
        students = self.mapped('student_ids') | self.mapped('student_id') | self.mapped('class_id.student_ids')
        res = super().unlink()
        if subjects:
            asgs = self.env['school.teaching.assignment'].search([
                ('subject_id', 'in', subjects.ids),
                '|', ('class_id', 'in', classes.ids), ('teacher_id', 'in', teachers.ids),
            ])
            if asgs:
                asgs._compute_timetable_stats()
            stu_subs = self.env['school.student.subject'].search([
                ('subject_id', 'in', subjects.ids),
                '|',
                ('class_id', 'in', classes.ids),
                ('student_id', 'in', students.ids),
            ])
            if stu_subs:
                stu_subs._compute_timetable_stats()
        if students:
            students._compute_study_stats()
            students._compute_timetable_ids()
        if teachers:
            teachers._compute_timetable_count()
        if classes:
            classes._compute_timetable_count()
        return res

    def _trigger_recompute_stats(self):
        classes = self.mapped('class_id')
        subjects = self.mapped('subject_ids') | self.mapped('subject_id')
        teachers = self.mapped('teacher_id')
        students = self.mapped('student_ids') | self.mapped('student_id') | self.mapped('class_id.student_ids')

        # 1. Auto-ensure teaching assignments for (teacher, subject, class)
        Assignment = self.env['school.teaching.assignment']
        for sess in self:
            if sess.teacher_id and sess.class_id:
                duration = max(0.0, (sess.end_time or 0.0) - (sess.start_time or 0.0))
                for sub in (sess.subject_ids | sess.subject_id):
                    asg = Assignment.search([
                        ('teacher_id', '=', sess.teacher_id.id),
                        ('class_id', '=', sess.class_id.id),
                        ('subject_id', '=', sub.id),
                    ], limit=1)
                    if not asg:
                        Assignment.create({
                            'teacher_id': sess.teacher_id.id,
                            'class_id': sess.class_id.id,
                            'subject_id': sub.id,
                            'weekly_hours': duration or 2.0,
                            'weekly_sessions': 1,
                            'active': True,
                        })

        # 2. Auto-ensure student study subjects for all attending students
        StudentSubject = self.env['school.student.subject']
        for sess in self:
            target_students = sess.student_ids | sess.student_id | (sess.class_id.student_ids if sess.class_id else self.env['school.student'])
            session_subs = sess.subject_ids | sess.subject_id
            duration = max(0.0, (sess.end_time or 0.0) - (sess.start_time or 0.0))
            for stud in target_students:
                for sub in session_subs:
                    rec_sub = StudentSubject.search([
                        ('student_id', '=', stud.id),
                        ('subject_id', '=', sub.id),
                    ], limit=1)
                    if not rec_sub:
                        StudentSubject.create({
                            'student_id': stud.id,
                            'class_id': stud.class_id.id if stud.class_id else (sess.class_id.id if sess.class_id else False),
                            'subject_id': sub.id,
                            'teacher_id': sess.teacher_id.id if sess.teacher_id else False,
                            'weekly_hours': duration or 2.0,
                            'weekly_sessions': 1,
                            'study_status': 'active',
                            'active': True,
                        })
                    elif not rec_sub.teacher_id and sess.teacher_id:
                        rec_sub.teacher_id = sess.teacher_id.id

        # 3. Recalculate scheduled stats on assignments and student subjects
        if subjects:
            asgs = Assignment.search([
                ('subject_id', 'in', subjects.ids),
                '|', ('class_id', 'in', classes.ids), ('teacher_id', 'in', teachers.ids),
            ])
            if asgs:
                asgs._compute_timetable_stats()

            stu_subs = StudentSubject.search([
                ('subject_id', 'in', subjects.ids),
                '|',
                ('class_id', 'in', classes.ids),
                ('student_id', 'in', students.ids),
            ])
            if stu_subs:
                stu_subs._compute_timetable_stats()

        # 4. Refresh parent model computations
        if students:
            students._compute_study_stats()
            students._compute_timetable_ids()
        if teachers:
            teachers._compute_timetable_count()
        if classes:
            classes._compute_timetable_count()

    # -------------------------------------------------------------------------
    # CONSTRAINTS & CONFLICT CHECKING
    # -------------------------------------------------------------------------
    @api.constrains('subject_id', 'subject_ids')
    def _check_subjects_present(self):
        for rec in self:
            if not rec.subject_ids and not rec.subject_id:
                raise ValidationError(_("Please select at least one Subject for this timetable session."))

    @api.constrains('class_id', 'student_id', 'student_ids')
    def _check_class_or_student(self):
        for rec in self:
            if not rec.class_id and not rec.student_id and not rec.student_ids:
                raise ValidationError(_("Please select either a Class or at least one Student for this timetable session."))

    @api.constrains('start_time', 'end_time', 'start_datetime', 'end_datetime')
    def _check_time_order(self):
        for rec in self:
            if rec.start_time >= rec.end_time:
                raise ValidationError(_(
                    "Invalid Schedule Time: Start Time (%(start)s) must be earlier than End Time (%(end)s)."
                ) % {
                    'start': rec._format_time(rec.start_time),
                    'end': rec._format_time(rec.end_time),
                })
            if rec.start_datetime and rec.end_datetime and rec.start_datetime >= rec.end_datetime:
                raise ValidationError(_(
                    "Invalid Schedule Datetime: Session Start must be strictly earlier than Session End."
                ))

    @api.constrains('teacher_id', 'day_of_week', 'start_time', 'end_time', 'active')
    def _check_teacher_conflict(self):
        days = dict(DAY_SELECTION)
        for rec in self:
            if not rec.active or not rec.teacher_id:
                continue
            conflicts = self.search([
                ('id', '!=', rec.id),
                ('teacher_id', '=', rec.teacher_id.id),
                ('day_of_week', '=', rec.day_of_week),
                ('active', '=', True),
                ('start_time', '<', rec.end_time),
                ('end_time', '>', rec.start_time),
            ])
            if conflicts:
                other = conflicts[0]
                target = other.student_id.name if other.student_id else (other.class_id.name if other.class_id else '')
                raise ValidationError(_(
                    "Teacher Conflict Detected!\n"
                    "Teacher '%(teacher)s' is already scheduled on %(day)s from %(start)s to %(end)s "
                    "for '%(target)s' (Subject: %(subject)s).\n"
                    "A teacher cannot be booked for two overlapping sessions simultaneously."
                ) % {
                    'teacher': rec.teacher_id.name,
                    'day': days.get(rec.day_of_week),
                    'start': rec._format_time(other.start_time),
                    'end': rec._format_time(other.end_time),
                    'target': target,
                    'subject': other.subject_id.name,
                })

    @api.constrains('class_id', 'day_of_week', 'start_time', 'end_time', 'active')
    def _check_class_conflict(self):
        days = dict(DAY_SELECTION)
        for rec in self:
            if not rec.active or not rec.class_id or rec.student_id:
                # If specific 1-on-1 student session, class conflict check does not block entire class
                continue
            conflicts = self.search([
                ('id', '!=', rec.id),
                ('class_id', '=', rec.class_id.id),
                ('student_id', '=', False),
                ('day_of_week', '=', rec.day_of_week),
                ('active', '=', True),
                ('start_time', '<', rec.end_time),
                ('end_time', '>', rec.start_time),
            ])
            if conflicts:
                other = conflicts[0]
                raise ValidationError(_(
                    "Class Conflict Detected!\n"
                    "Class '%(class_name)s' is already scheduled on %(day)s from %(start)s to %(end)s "
                    "for Subject '%(subject)s' with Teacher '%(teacher)s'.\n"
                    "A class cannot have two concurrent class-wide subjects at the same time."
                ) % {
                    'class_name': rec.class_id.name,
                    'day': days.get(rec.day_of_week),
                    'start': rec._format_time(other.start_time),
                    'end': rec._format_time(other.end_time),
                    'subject': other.subject_id.name,
                    'teacher': other.teacher_id.name,
                })

    @api.constrains('student_id', 'student_ids', 'day_of_week', 'start_time', 'end_time', 'active')
    def _check_student_conflict(self):
        days = dict(DAY_SELECTION)
        for rec in self:
            if not rec.active:
                continue
            students_to_check = rec.student_ids or (rec.student_id if rec.student_id else self.env['school.student'])
            if not students_to_check and rec.class_id:
                continue
            for student in students_to_check:
                conflicts = self.search([
                    ('id', '!=', rec.id),
                    ('day_of_week', '=', rec.day_of_week),
                    ('active', '=', True),
                    ('start_time', '<', rec.end_time),
                    ('end_time', '>', rec.start_time),
                    '|',
                    ('student_ids', 'in', student.id),
                    '|',
                    ('student_id', '=', student.id),
                    '&', ('class_id', '=', student.class_id.id if student.class_id else False), ('student_id', '=', False),
                ])
                if conflicts:
                    other = conflicts[0]
                    raise ValidationError(_(
                        "Student Conflict Detected!\n"
                        "Student '%(student)s' is already scheduled on %(day)s from %(start)s to %(end)s "
                        "for session '%(session)s' (Teacher: %(teacher)s, Subject: %(subject)s).\n"
                        "A student cannot attend two overlapping sessions simultaneously."
                    ) % {
                        'student': student.name,
                        'day': days.get(rec.day_of_week),
                        'start': rec._format_time(other.start_time),
                        'end': rec._format_time(other.end_time),
                        'session': other.display_name or other.name,
                        'teacher': other.teacher_id.name,
                        'subject': other.subject_id.name,
                    })

    @api.constrains('room', 'day_of_week', 'start_time', 'end_time', 'active')
    def _check_room_conflict(self):
        days = dict(DAY_SELECTION)
        for rec in self:
            if not rec.active or not rec.room or not rec.room.strip():
                continue
            room_clean = rec.room.strip().lower()
            other_slots = self.search([
                ('id', '!=', rec.id),
                ('day_of_week', '=', rec.day_of_week),
                ('active', '=', True),
                ('start_time', '<', rec.end_time),
                ('end_time', '>', rec.start_time),
            ])
            for other in other_slots:
                if other.room and other.room.strip().lower() == room_clean:
                    target = other.student_id.name if other.student_id else (other.class_id.name if other.class_id else '')
                    raise ValidationError(_(
                        "Classroom/Room Conflict Detected!\n"
                        "Room '%(room)s' is already booked on %(day)s from %(start)s to %(end)s "
                        "for '%(target)s' (Teacher: %(teacher)s, Subject: %(subject)s).\n"
                        "A room cannot host two simultaneous sessions."
                    ) % {
                        'room': rec.room.strip(),
                        'day': days.get(rec.day_of_week),
                        'start': rec._format_time(other.start_time),
                        'end': rec._format_time(other.end_time),
                        'target': target,
                        'teacher': other.teacher_id.name,
                        'subject': other.subject_id.name,
                    })

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_view_class_students(self):
        self.ensure_one()
        if self.class_id:
            domain = [('class_id', '=', self.class_id.id)]
        elif self.student_ids:
            domain = [('id', 'in', self.student_ids.ids)]
        else:
            domain = [('id', '=', self.student_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Students in %s') % (self.student_id.name if self.student_id else (self.class_id.name if self.class_id else _("Session"))),
            'res_model': 'school.student',
            'view_mode': 'list,kanban,form',
            'domain': domain,
            'target': 'current',
        }

    def action_anchor_to_current_week(self):
        for rec in self:
            if rec.day_of_week and rec.start_time is not None and rec.end_time is not None:
                s_dt, e_dt = rec._calculate_datetimes(rec.day_of_week, rec.start_time, rec.end_time)
                rec.write({
                    'start_datetime': s_dt,
                    'end_datetime': e_dt,
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Timetable Synchronized'),
                'message': _('Selected sessions anchored to current week datetimes.'),
                'type': 'success',
                'sticky': False,
            }
        }
