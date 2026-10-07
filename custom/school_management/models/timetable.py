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

START_TIME_SELECTION = [
    ('0.0', '12:00 AM (00:00)'),
    ('0.5', '12:30 AM (00:30)'),
    ('1.0', '01:00 AM (01:00)'),
    ('1.5', '01:30 AM (01:30)'),
    ('2.0', '02:00 AM (02:00)'),
    ('2.5', '02:30 AM (02:30)'),
    ('3.0', '03:00 AM (03:00)'),
    ('3.5', '03:30 AM (03:30)'),
    ('4.0', '04:00 AM (04:00)'),
    ('4.5', '04:30 AM (04:30)'),
    ('5.0', '05:00 AM (05:00)'),
    ('5.5', '05:30 AM (05:30)'),
    ('6.0', '06:00 AM (06:00)'),
    ('6.5', '06:30 AM (06:30)'),
    ('7.0', '07:00 AM (07:00)'),
    ('7.5', '07:30 AM (07:30)'),
    ('8.0', '08:00 AM (08:00)'),
    ('8.5', '08:30 AM (08:30)'),
    ('9.0', '09:00 AM (09:00)'),
    ('9.5', '09:30 AM (09:30)'),
    ('10.0', '10:00 AM (10:00)'),
    ('10.5', '10:30 AM (10:30)'),
    ('11.0', '11:00 AM (11:00)'),
    ('11.5', '11:30 AM (11:30)'),
    ('12.0', '12:00 PM (12:00)'),
    ('12.5', '12:30 PM (12:30)'),
    ('13.0', '01:00 PM (13:00)'),
    ('13.5', '01:30 PM (13:30)'),
    ('14.0', '02:00 PM (14:00)'),
    ('14.5', '02:30 PM (14:30)'),
    ('15.0', '03:00 PM (15:00)'),
    ('15.5', '03:30 PM (15:30)'),
    ('16.0', '04:00 PM (16:00)'),
    ('16.5', '04:30 PM (16:30)'),
    ('17.0', '05:00 PM (17:00)'),
    ('17.5', '05:30 PM (17:30)'),
    ('18.0', '06:00 PM (18:00)'),
    ('18.5', '06:30 PM (18:30)'),
    ('19.0', '07:00 PM (19:00)'),
    ('19.5', '07:30 PM (19:30)'),
    ('20.0', '08:00 PM (20:00)'),
    ('20.5', '08:30 PM (20:30)'),
    ('21.0', '09:00 PM (21:00)'),
    ('21.5', '09:30 PM (21:30)'),
    ('22.0', '10:00 PM (22:00)'),
    ('22.5', '10:30 PM (22:30)'),
    ('23.0', '11:00 PM (23:00)'),
]

PERIOD_SELECTION = [
    ('h00', '12:00 AM - 01:00 AM (Midnight)'),
    ('h01', '01:00 AM - 02:00 AM'),
    ('h02', '02:00 AM - 03:00 AM'),
    ('h03', '03:00 AM - 04:00 AM'),
    ('h04', '04:00 AM - 05:00 AM'),
    ('h05', '05:00 AM - 06:00 AM'),
    ('h06', '06:00 AM - 07:00 AM (Early Morning)'),
    ('h07', '07:00 AM - 08:00 AM (Morning Prep)'),
    ('p1', 'Period 1 (08:00 - 09:00)'),
    ('p2', 'Period 2 (09:15 - 10:15)'),
    ('p3', 'Period 3 (10:25 - 11:25)'),
    ('p4', 'Period 4 (11:25 - 12:25)'),
    ('h12', '12:00 PM - 01:00 PM (Noon / Lunch)'),
    ('p5', 'Period 5 (13:30 - 14:30)'),
    ('p6', 'Period 6 (14:30 - 15:30)'),
    ('p7', 'Period 7 (15:45 - 16:45)'),
    ('h17', '05:00 PM - 06:00 PM (Evening 1)'),
    ('h18', '06:00 PM - 07:00 PM (Evening 2)'),
    ('h19', '07:00 PM - 08:00 PM (Night 1)'),
    ('h20', '08:00 PM - 09:00 PM (Night 2)'),
    ('h21', '09:00 PM - 10:00 PM (Late Night 1)'),
    ('h22', '10:00 PM - 11:00 PM (Late Night 2)'),
    ('h23', '11:00 PM - 12:00 AM (Night Final)'),
    ('p_m1', 'Morning 1 (08:00 - 09:30)'),
    ('p_m2', 'Morning 2 (10:30 - 12:00)'),
    ('p_a1', 'Afternoon 1 (13:30 - 15:00)'),
    ('p_a2', 'Afternoon 2 (16:00 - 17:30)'),
    ('custom', 'Custom Time Window'),
]

PERIOD_PRESETS = {
    'h00': (0.0, 1.0),
    'h01': (1.0, 2.0),
    'h02': (2.0, 3.0),
    'h03': (3.0, 4.0),
    'h04': (4.0, 5.0),
    'h05': (5.0, 6.0),
    'h06': (6.0, 7.0),
    'h07': (7.0, 8.0),
    'p1': (8.0, 9.0),
    'p2': (9.25, 10.25),
    'p3': (10.25, 11.25),
    'p4': (11.25, 12.25),
    'h12': (12.0, 13.0),
    'p5': (13.5, 14.5),
    'p6': (14.5, 15.5),
    'p7': (15.75, 16.75),
    'h17': (17.0, 18.0),
    'h18': (18.0, 19.0),
    'h19': (19.0, 20.0),
    'h20': (20.0, 21.0),
    'h21': (21.0, 22.0),
    'h22': (22.0, 23.0),
    'h23': (23.0, 24.0),
    'p_m1': (8.0, 9.5),
    'p_m2': (10.5, 12.0),
    'p_a1': (13.5, 15.0),
    'p_a2': (16.0, 17.5),
}


class SchoolTimetable(models.Model):
    _name = 'school.timetable'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Class Timetable & Teaching Schedule'
    _order = 'day_of_week, start_time, class_id'
    _rec_name = 'display_name'

    name = fields.Char(string='Session Title', tracking=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    term_id = fields.Many2one(
        'school.term',
        string='Academic Term',
        tracking=True,
        index=True,
        ondelete='cascade',
        help="Academic term to which this timetable session belongs."
    )
    week_number = fields.Integer(
        string='Academic Week',
        default=1,
        index=True,
        help="Week number within the academic term (e.g. Week 1 to Week 12)."
    )
    week_name = fields.Char(
        string='Week',
        compute='_compute_week_name',
        store=True,
        help="Display label for the academic week (e.g. Week 1)."
    )
    iso_week_number = fields.Integer(
        string='Calendar Week (ISO)',
        compute='_compute_iso_week_number',
        store=True,
        index=True,
        help="ISO 8601 calendar week number (1-53)"
    )
    is_holiday = fields.Boolean(
        string='Holiday / No Study',
        default=False,
        tracking=True,
        index=True,
        help="Mark this session as a school holiday or non-study day (no classes scheduled)."
    )
    holiday_name = fields.Char(
        string='Holiday Reason',
        tracking=True,
        help="e.g. Khmer New Year, Water Festival, Public Holiday, Teacher Day, National Break"
    )
    is_exam = fields.Boolean(
        string='Examination Session',
        default=False,
        tracking=True,
        index=True,
        help="Mark this session as an examination or assessment session."
    )
    exam_id = fields.Many2one(
        'school.exam',
        string='Examination',
        tracking=True,
        index=True,
        ondelete='cascade',
        help="Related examination record."
    )
    schedule_status = fields.Selection([
        ('regular', 'Class Session'),
        ('holiday', 'Holiday / No Study'),
        ('exam', 'Examination'),
    ], string='Status', compute='_compute_schedule_status', store=True, index=True)

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
        required=False,
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
    period_short = fields.Char(
        string='Period Label',
        compute='_compute_period_short',
        store=True,
    )
    specific_start_time = fields.Selection(
        START_TIME_SELECTION,
        string='Specific Start Hour',
        compute='_compute_specific_start_time',
        inverse='_inverse_specific_start_time',
        store=True,
        tracking=True,
        help="Select a specific start time from 12:00 AM (00:00) until 11:00 PM (23:00)."
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
    time_display = fields.Char(
        string='Time Range',
        compute='_compute_time_display',
        store=True,
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
        tz_name = (
            self.env.context.get('tz')
            or (self.env.user.tz if self.env.user and self.env.user.tz else False)
            or (self.company_id.partner_id.tz if hasattr(self, 'company_id') and self.company_id and self.company_id.partner_id.tz else False)
            or (self.env.company.partner_id.tz if hasattr(self.env, 'company') and self.env.company and self.env.company.partner_id.tz else False)
            or 'Asia/Phnom_Penh'
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.timezone('Asia/Phnom_Penh')

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

    def _format_time_12h(self, float_hour):
        """Format float time into 12-hour AM/PM string, e.g. 0.0 -> 12:00 AM, 23.0 -> 11:00 PM."""
        if float_hour is None:
            return "12:00 AM"
        h = int(float_hour)
        m = int(round((float_hour - h) * 60))
        if m >= 60:
            h += 1
            m = 0
        if h == 0 or h == 24:
            return f"12:{m:02d} AM"
        elif h < 12:
            return f"{h:02d}:{m:02d} AM"
        elif h == 12:
            return f"12:{m:02d} PM"
        else:
            return f"{h - 12:02d}:{m:02d} PM"

    def _local_to_utc(self, target_date, float_hour):
        tz = self._get_user_tz()
        if float_hour is None:
            float_hour = 0.0
        clamped_hour = max(0.0, min(24.0, float(float_hour)))
        hours = int(clamped_hour)
        minutes = int(round((clamped_hour - hours) * 60))
        if minutes >= 60:
            hours += 1
            minutes = 0
        if hours >= 24:
            hours = 23
            minutes = 59
            seconds = 59
        else:
            seconds = 0
        naive_dt = datetime.combine(target_date, time(hours, minutes, seconds))
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

    def _calculate_datetimes(self, day_of_week, start_time, end_time, term=None, week_number=None):
        if not term and hasattr(self, 'term_id') and self.term_id:
            term = self.term_id
        if not week_number and hasattr(self, 'week_number') and self.week_number:
            week_number = self.week_number

        w_num = int(week_number or 1)
        day_idx = int(day_of_week) if day_of_week else 0

        if w_num > 20:
            target_year = term.date_start.year if (term and term.date_start) else fields.Date.context_today(self).year
            try:
                target_date = date.fromisocalendar(target_year, w_num, day_idx + 1)
            except Exception:
                target_date = self._get_current_week_monday() + timedelta(days=day_idx)
        elif term and term.date_start:
            first_monday = term.date_start - timedelta(days=term.date_start.weekday())
            target_date = first_monday + timedelta(weeks=w_num - 1, days=day_idx)
        else:
            monday = self._get_current_week_monday()
            target_date = monday + timedelta(days=day_idx)

        s_time = 8.0 if start_time is None else start_time
        e_time = 9.0 if end_time is None else end_time
        start_dt = self._local_to_utc(target_date, s_time)
        end_dt = self._local_to_utc(target_date, e_time)
        return start_dt, end_dt

    def _match_period(self, start_time, end_time):
        if start_time is None or end_time is None:
            return 'custom'
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
                res['day_of_week'] = day_str
                res['start_time'] = s_time
                res['end_time'] = e_time
                res['period'] = self._match_period(s_time, e_time)

        if 'day_of_week' in res and ('start_time' in res or 'period' in res or 'start_time' in self.env.context):
            day_str = res.get('day_of_week', '0')
            if 'start_time' in res and res.get('start_time') is not None:
                s_time = res['start_time']
                e_time = res.get('end_time', min(24.0, s_time + 1.0))
            else:
                period_val = res.get('period', 'p1')
                if period_val in PERIOD_PRESETS:
                    s_time, e_time = PERIOD_PRESETS[period_val]
                else:
                    s_time = 8.0
                    e_time = 9.0
            res['start_time'] = s_time
            res['end_time'] = e_time
            if 'start_datetime' in fields_list or 'end_datetime' in fields_list:
                effective_term_id = res.get('term_id') or self.env.context.get('default_term_id')
                term_obj = self.env['school.term'].browse(effective_term_id) if effective_term_id else False
                w_num = res.get('week_number', 1)
                s_dt, e_dt = self._calculate_datetimes(day_str, s_time, e_time, term=term_obj, week_number=w_num)
                res.setdefault('start_datetime', s_dt)
                res.setdefault('end_datetime', e_dt)

        return res

    @api.depends('week_number')
    def _compute_week_name(self):
        for rec in self:
            rec.week_name = f"Week {rec.week_number}" if rec.week_number else False

    @api.depends('start_datetime', 'week_number', 'term_id')
    def _compute_iso_week_number(self):
        for rec in self:
            if rec.start_datetime:
                local_dt = rec._utc_to_local(rec.start_datetime)
                rec.iso_week_number = local_dt.date().isocalendar()[1] if local_dt else (rec.week_number or 1)
            elif rec.week_number and rec.week_number > 20:
                rec.iso_week_number = rec.week_number
            elif rec.term_id and rec.term_id.date_start and rec.week_number:
                first_mon = rec.term_id.date_start - timedelta(days=rec.term_id.date_start.weekday())
                target_mon = first_mon + timedelta(weeks=rec.week_number - 1)
                rec.iso_week_number = target_mon.isocalendar()[1]
            else:
                rec.iso_week_number = rec.week_number or 1

    @api.depends('is_holiday', 'is_exam', 'exam_id')
    def _compute_schedule_status(self):
        for rec in self:
            if rec.is_holiday:
                rec.schedule_status = 'holiday'
            elif rec.is_exam or rec.exam_id:
                rec.schedule_status = 'exam'
            else:
                rec.schedule_status = 'regular'

    @api.depends('period')
    def _compute_period_short(self):
        period_dict = dict(PERIOD_SELECTION)
        for rec in self:
            if rec.period in period_dict:
                raw_label = period_dict[rec.period]
                if '(' in raw_label:
                    rec.period_short = raw_label.split('(')[0].strip()
                elif '-' in raw_label:
                    rec.period_short = raw_label.split('-')[0].strip()
                else:
                    rec.period_short = raw_label
            else:
                rec.period_short = _('Period')

    @api.depends('start_time', 'end_time')
    def _compute_time_display(self):
        for rec in self:
            rec.time_display = f"{rec._format_time(rec.start_time)} - {rec._format_time(rec.end_time)}"

    @api.depends('start_time')
    def _compute_specific_start_time(self):
        valid_keys = [k for k, _ in START_TIME_SELECTION]
        for rec in self:
            if rec.start_time is not None:
                matched_key = False
                for k in valid_keys:
                    if abs(rec.start_time - float(k)) < 0.02:
                        matched_key = k
                        break
                rec.specific_start_time = matched_key
            else:
                rec.specific_start_time = False

    def _inverse_specific_start_time(self):
        for rec in self:
            if rec.specific_start_time:
                val = float(rec.specific_start_time)
                if abs(rec.start_time - val) > 0.001:
                    duration = (rec.end_time - rec.start_time) if (rec.end_time and rec.end_time > rec.start_time) else 1.0
                    rec.start_time = val
                    rec.end_time = min(24.0, round(val + duration, 2))
                    rec.period = rec._match_period(rec.start_time, rec.end_time)

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
            if rec.student_id:
                rec.student_ids = [(6, 0, [rec.student_id.id])]
            elif rec.class_id:
                rec.student_ids = [(6, 0, rec.class_id.student_ids.ids)]
            elif not rec.student_ids:
                rec.student_ids = False

    @api.depends('class_id.name', 'student_id.name', 'subject_id.name', 'subject_ids.name', 'day_of_week', 'start_time', 'end_time', 'room', 'name', 'is_holiday', 'holiday_name', 'is_exam', 'exam_id.name')
    def _compute_display_name(self):
        days = dict(DAY_SELECTION)
        for rec in self:
            day_str = days.get(rec.day_of_week, '')
            start_str = rec._format_time(rec.start_time)
            end_str = rec._format_time(rec.end_time)
            target_name = rec.student_id.name or (rec.class_id.name if rec.class_id else _("Session"))
            target_str = f" ({target_name})" if target_name else ""
            room_str = f" [{rec.room}]" if rec.room else ""
            if rec.is_holiday:
                h_title = rec.holiday_name or rec.name or _("Holiday / No Class")
                rec.display_name = f"Holiday: {h_title}{target_str}"
                continue
            if rec.is_exam or rec.exam_id:
                e_title = rec.exam_id.name or rec.name or _("Exam")
                rec.display_name = f"[EXAM] {e_title}{target_str}{room_str}"
                continue
            subs = rec.subject_ids or (rec.subject_id if rec.subject_id else self.env['school.subject'])
            subject_name = ', '.join(subs.mapped('name')) if subs else (rec.subject_id.name or _("Subject"))
            if rec.name and rec.name != f"{target_name} - {subject_name}" and rec.name != f"{subject_name} - {target_name}":
                rec.display_name = f"{rec.name}{target_str}{room_str}"
            else:
                rec.display_name = f"{subject_name}{target_str}{room_str}"

    @api.depends('subject_id', 'class_id', 'teacher_id', 'is_holiday', 'is_exam', 'exam_id')
    def _compute_color(self):
        for rec in self:
            if rec.is_holiday:
                rec.color = 2
            elif rec.is_exam or rec.exam_id:
                rec.color = 9
            elif rec.teacher_id:
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
            matched_key = False
            for k, _ in START_TIME_SELECTION:
                if abs(s_time - float(k)) < 0.02:
                    matched_key = k
                    break
            self.specific_start_time = matched_key
            if self.day_of_week:
                s_dt, e_dt = self._calculate_datetimes(self.day_of_week, s_time, e_time, term=self.term_id, week_number=self.week_number)
                self.start_datetime = s_dt
                self.end_datetime = e_dt

    @api.onchange('specific_start_time')
    def _onchange_specific_start_time(self):
        if self.specific_start_time:
            val = float(self.specific_start_time)
            duration = (self.end_time - self.start_time) if (self.end_time and self.end_time > self.start_time) else 1.0
            self.start_time = val
            self.end_time = min(24.0, round(val + duration, 2))
            self.period = self._match_period(self.start_time, self.end_time)
            if self.day_of_week:
                s_dt, e_dt = self._calculate_datetimes(self.day_of_week, self.start_time, self.end_time, term=self.term_id, week_number=self.week_number)
                self.start_datetime = s_dt
                self.end_datetime = e_dt

    @api.onchange('day_of_week', 'start_time', 'end_time', 'week_number', 'term_id')
    def _onchange_timing(self):
        if self.start_time is not None and self.end_time is not None:
            self.period = self._match_period(self.start_time, self.end_time)
            matched_key = False
            for k, _ in START_TIME_SELECTION:
                if abs(self.start_time - float(k)) < 0.02:
                    matched_key = k
                    break
            self.specific_start_time = matched_key
        if self.day_of_week and self.start_time is not None and self.end_time is not None:
            s_dt, e_dt = self._calculate_datetimes(self.day_of_week, self.start_time, self.end_time, term=self.term_id, week_number=self.week_number)
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
                matched_key = False
                for k, _ in START_TIME_SELECTION:
                    if abs(self.start_time - float(k)) < 0.02:
                        matched_key = k
                        break
                self.specific_start_time = matched_key

    @api.onchange('is_holiday')
    def _onchange_is_holiday(self):
        if self.is_holiday:
            self.teacher_id = False
            self.subject_id = False
            self.subject_ids = False
            self.period = 'custom'
            self.start_time = 7.5
            self.end_time = 17.0
            if not self.holiday_name:
                self.holiday_name = _("School Holiday")
        else:
            self.holiday_name = False

    # -------------------------------------------------------------------------
    # CRUD SYNC
    # -------------------------------------------------------------------------
    def _sync_timetable_vals(self, vals):
        target_name = ''
        if vals.get('student_id'):
            target_name = self.env['school.student'].browse(vals['student_id']).name or ''
        elif vals.get('class_id'):
            target_name = self.env['school.class'].browse(vals['class_id']).name or ''

        # Sync student_id and student_ids
        if vals.get('student_id') and not vals.get('student_ids'):
            vals['student_ids'] = [(6, 0, [vals['student_id']])]
        elif vals.get('student_ids') and not vals.get('student_id'):
            stu_ids = []
            for cmd in vals['student_ids']:
                if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 6:
                    stu_ids.extend(cmd[2])
                elif isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 4:
                    stu_ids.append(cmd[1])
                elif isinstance(cmd, int):
                    stu_ids.append(cmd)
            if len(stu_ids) == 1:
                vals['student_id'] = stu_ids[0]
            if not target_name and stu_ids:
                target_name = ', '.join(self.env['school.student'].browse(stu_ids).mapped('name'))

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
            extracted_sub_ids = [vals['subject_id'] if isinstance(vals['subject_id'], int) else vals['subject_id'].id]

        if vals.get('is_holiday'):
            vals['teacher_id'] = False
            vals['subject_id'] = False
            vals['subject_ids'] = [(5, 0, 0)]
            if not vals.get('name') or vals.get('name') == _("New Session"):
                vals['name'] = vals.get('holiday_name') or _("School Holiday")
            if not vals.get('holiday_name'):
                vals['holiday_name'] = vals.get('name') or _("School Holiday")
            if 'start_time' not in vals or (vals.get('start_time') == 8.0 and vals.get('end_time') == 9.0):
                vals.setdefault('start_time', 7.5)
                vals.setdefault('end_time', 17.0)
                vals.setdefault('period', 'custom')
        elif not vals.get('name') and target_name and extracted_sub_ids:
            s_names = ', '.join(self.env['school.subject'].browse(extracted_sub_ids).mapped('name'))
            vals['name'] = f"{s_names} - {target_name}".strip(' -')

        term = None
        if vals.get('term_id'):
            term = self.env['school.term'].browse(vals['term_id'])
        elif vals.get('class_id'):
            cls_obj = self.env['school.class'].browse(vals['class_id'])
            if cls_obj.current_term_id:
                vals['term_id'] = cls_obj.current_term_id.id
                term = cls_obj.current_term_id

        if not vals.get('week_number') and vals.get('start_datetime'):
            s_dt = fields.Datetime.to_datetime(vals['start_datetime'])
            if term and term.date_start:
                first_mon = term.date_start - timedelta(days=term.date_start.weekday())
                w_diff = (s_dt.date() - first_mon).days // 7 + 1
                if 1 <= w_diff <= (term.duration_weeks or 12):
                    vals['week_number'] = w_diff
                else:
                    vals['week_number'] = s_dt.date().isocalendar()[1]
            else:
                vals['week_number'] = s_dt.date().isocalendar()[1]

        if 'start_datetime' in vals and 'end_datetime' in vals and ('day_of_week' not in vals or 'start_time' not in vals):
            local_start = self._utc_to_local(vals['start_datetime'])
            local_end = self._utc_to_local(vals['end_datetime'])
            if local_start and local_end:
                vals['day_of_week'] = str(local_start.weekday())
                vals['start_time'] = round(local_start.hour + local_start.minute / 60.0, 2)
                vals['end_time'] = round(local_end.hour + local_end.minute / 60.0, 2)
                if 'period' not in vals:
                    vals['period'] = self._match_period(vals['start_time'], vals['end_time'])
        elif ('day_of_week' in vals or 'start_time' in vals or 'end_time' in vals or 'period' in vals) and ('start_datetime' not in vals):
            d_val = vals.get('day_of_week', '0')
            if vals.get('period') in PERIOD_PRESETS and 'start_time' not in vals:
                vals['start_time'], vals['end_time'] = PERIOD_PRESETS[vals['period']]
            s_val = vals['start_time'] if ('start_time' in vals and vals['start_time'] is not None) else (7.5 if vals.get('is_holiday') else 8.0)
            e_val = vals['end_time'] if ('end_time' in vals and vals['end_time'] is not None) else (17.0 if vals.get('is_holiday') else 9.0)
            if 'period' not in vals:
                vals['period'] = self._match_period(s_val, e_val)
            elif vals.get('period') in PERIOD_PRESETS and ('start_time' in vals or 'end_time' in vals):
                ps, pe = PERIOD_PRESETS[vals['period']]
                if abs(s_val - ps) > 0.02 or abs(e_val - pe) > 0.02:
                    vals['period'] = self._match_period(s_val, e_val)
            term = self.env['school.term'].browse(vals['term_id']) if vals.get('term_id') else (getattr(self, 'term_id', False))
            w_num = vals.get('week_number') or getattr(self, 'week_number', 1)
            s_dt, e_dt = self._calculate_datetimes(d_val, s_val, e_val, term=term, week_number=w_num)
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
            elif vals.get('student_ids') and not vals.get('class_id'):
                stu_ids = []
                for cmd in vals.get('student_ids', []):
                    if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 6:
                        stu_ids.extend(cmd[2])
                    elif isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 4:
                        stu_ids.append(cmd[1])
                    elif isinstance(cmd, int):
                        stu_ids.append(cmd)
                if stu_ids:
                    students = self.env['school.student'].browse(stu_ids)
                    classes = students.mapped('class_id')
                    if len(classes) == 1:
                        vals['class_id'] = classes[0].id
            self._sync_timetable_vals(vals)
        records = super().create(vals_list)
        for rec in records:
            if not rec.is_holiday:
                subs = rec.subject_ids or (rec.subject_id if rec.subject_id else self.env['school.subject'])
                if rec.teacher_id:
                    rec.teacher_id.subject_ids |= subs
                    for sub in subs:
                        existing = self.env['school.teaching.assignment'].search([
                            ('teacher_id', '=', rec.teacher_id.id),
                            ('subject_id', '=', sub.id),
                            ('class_id', '=', rec.class_id.id if rec.class_id else False),
                            ('active', '=', True),
                        ], limit=1)
                        if not existing and rec.class_id:
                            self.env['school.teaching.assignment'].create({
                                'teacher_id': rec.teacher_id.id,
                                'subject_id': sub.id,
                                'class_id': rec.class_id.id,
                                'weekly_hours': max(1.0, round(rec.end_time - rec.start_time, 2)),
                            })
                students = rec.student_ids or (rec.student_id if rec.student_id else (rec.class_id and rec.class_id.student_ids))
                if students and subs:
                    for stu in students:
                        for sub in subs:
                            stu_sub = self.env['school.student.subject'].search([
                                ('student_id', '=', stu.id),
                                ('subject_id', '=', sub.id),
                            ], limit=1)
                            if not stu_sub:
                                self.env['school.student.subject'].create({
                                    'student_id': stu.id,
                                    'subject_id': sub.id,
                                    'class_id': rec.class_id.id if rec.class_id else (stu.class_id.id if stu.class_id else False),
                                    'weekly_hours': max(1.0, round(rec.end_time - rec.start_time, 2)),
                                })

        holidays = records.filtered(lambda r: r.is_holiday)
        if holidays:
            holidays._cleanup_regular_classes_for_holiday()

        records._trigger_recompute_stats()
        return records

    def write(self, vals):
        if 'student_id' in vals and not vals.get('student_id') and not vals.get('student_ids'):
            for rec in self:
                if rec.class_id:
                    vals['student_ids'] = [(6, 0, rec.class_id.student_ids.ids)]

        if vals.get('period') in PERIOD_PRESETS and 'start_time' not in vals:
            vals['start_time'], vals['end_time'] = PERIOD_PRESETS[vals['period']]

        res = super().write(vals)

        # Resync timing if day or start/end datetimes changed
        if any(k in vals for k in ('start_datetime', 'end_datetime', 'day_of_week', 'start_time', 'end_time', 'period', 'is_holiday', 'week_number', 'term_id')):
            for rec in self:
                sync_vals = {}
                if 'start_datetime' in vals or 'end_datetime' in vals:
                    local_s = rec._utc_to_local(rec.start_datetime)
                    local_e = rec._utc_to_local(rec.end_datetime)
                    if local_s and local_e:
                        sync_vals['day_of_week'] = str(local_s.weekday())
                        sync_vals['start_time'] = round(local_s.hour + local_s.minute / 60.0, 2)
                        sync_vals['end_time'] = round(local_e.hour + local_e.minute / 60.0, 2)
                        sync_vals['period'] = rec._match_period(sync_vals['start_time'], sync_vals['end_time'])
                elif any(k in vals for k in ('day_of_week', 'start_time', 'end_time', 'period', 'week_number', 'term_id')):
                    term = rec.term_id
                    w_num = rec.week_number
                    s_dt, e_dt = rec._calculate_datetimes(rec.day_of_week, rec.start_time, rec.end_time, term=term, week_number=w_num)
                    sync_vals['start_datetime'] = s_dt
                    sync_vals['end_datetime'] = e_dt
                    if 'period' not in vals:
                        sync_vals['period'] = rec._match_period(rec.start_time, rec.end_time)

                if rec.is_holiday:
                    sync_vals.update({
                        'teacher_id': False,
                        'subject_id': False,
                        'subject_ids': [(5, 0, 0)],
                        'period': 'custom',
                        'start_time': 7.5,
                        'end_time': 17.0,
                    })

                if sync_vals:
                    super(SchoolTimetable, rec).write(sync_vals)

        holidays = self.filtered(lambda r: r.is_holiday)
        if holidays:
            holidays._cleanup_regular_classes_for_holiday()

        self._trigger_recompute_stats()
        return res

    def unlink(self):
        regular_sessions = self.filtered(lambda s: not s.is_holiday)
        subjects = regular_sessions.mapped('subject_ids') | regular_sessions.mapped('subject_id')
        classes = regular_sessions.mapped('class_id')
        teachers = regular_sessions.mapped('teacher_id')
        students = regular_sessions.mapped('student_ids') | regular_sessions.mapped('student_id') | regular_sessions.mapped('class_id.student_ids')

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
        regular_sessions = self.filtered(lambda s: not s.is_holiday)
        classes = regular_sessions.mapped('class_id')
        subjects = regular_sessions.mapped('subject_ids') | regular_sessions.mapped('subject_id')
        teachers = regular_sessions.mapped('teacher_id')
        students = regular_sessions.mapped('student_ids') | regular_sessions.mapped('student_id') | regular_sessions.mapped('class_id.student_ids')

        # 1. Update teaching assignment counts & hours
        if subjects:
            assignments = self.env['school.teaching.assignment'].search([
                ('subject_id', 'in', subjects.ids),
                '|', ('class_id', 'in', classes.ids), ('teacher_id', 'in', teachers.ids),
            ])
            if assignments:
                assignments._compute_timetable_stats()

        # 2. Update student subject study counts & hours
        if subjects:
            stu_subjects = self.env['school.student.subject'].search([
                ('subject_id', 'in', subjects.ids),
                '|',
                ('class_id', 'in', classes.ids),
                ('student_id', 'in', students.ids),
            ])
            if stu_subjects:
                stu_subjects._compute_timetable_stats()

        # 3. Refresh parent model computations
        if students:
            students._compute_study_stats()
            students._compute_timetable_ids()
        if teachers:
            teachers._compute_timetable_count()
        if classes:
            classes._compute_timetable_count()

    def _get_session_calendar_date(self):
        """Determine the calendar date for a timetable session (from start_datetime or term + week + day)."""
        self.ensure_one()
        if self.start_datetime:
            return self._utc_to_local(self.start_datetime).date()
        w_num = int(self.week_number or 1)
        day_offset = int(self.day_of_week) if self.day_of_week else 0
        if w_num > 20:
            target_year = self.term_id.date_start.year if (self.term_id and self.term_id.date_start) else fields.Date.context_today(self).year
            try:
                return date.fromisocalendar(target_year, w_num, day_offset + 1)
            except Exception:
                pass
        if self.term_id and self.term_id.date_start:
            first_mon = self.term_id.date_start - timedelta(days=self.term_id.date_start.weekday())
            return first_mon + timedelta(weeks=w_num - 1, days=day_offset)
        return False

    def _is_holiday_applicable(self, regular_rec, holiday_rec):
        """Check if a holiday applies to a given regular class session."""
        # 1. Class scope:
        if holiday_rec.class_id:
            reg_classes = regular_rec.class_id
            if regular_rec.student_ids or regular_rec.student_id:
                reg_classes |= (regular_rec.student_ids | regular_rec.student_id).mapped('class_id')
            if holiday_rec.class_id not in reg_classes:
                return False

        # 2. Term scope:
        if regular_rec.term_id and holiday_rec.term_id:
            if regular_rec.term_id != holiday_rec.term_id:
                return False
        elif holiday_rec.term_id:
            h_term = holiday_rec.term_id
            if h_term.state != 'active':
                return False
            if regular_rec.start_datetime and h_term.date_start and h_term.date_end:
                r_date = regular_rec._utc_to_local(regular_rec.start_datetime).date()
                if not (h_term.date_start <= r_date <= h_term.date_end):
                    return False
        elif regular_rec.term_id:
            r_term = regular_rec.term_id
            if holiday_rec.start_datetime and r_term.date_start and r_term.date_end:
                h_date = holiday_rec._utc_to_local(holiday_rec.start_datetime).date()
                if not (r_term.date_start <= h_date <= r_term.date_end):
                    return False

        # 3. Date / Day match:
        r_local_date = regular_rec._get_session_calendar_date()
        h_local_date = holiday_rec._get_session_calendar_date()

        if r_local_date and h_local_date:
            return r_local_date == h_local_date

        if regular_rec.term_id and holiday_rec.term_id and regular_rec.term_id == holiday_rec.term_id:
            if regular_rec.week_number and holiday_rec.week_number and regular_rec.week_number == holiday_rec.week_number:
                return regular_rec.day_of_week == holiday_rec.day_of_week

        if not regular_rec.term_id and not holiday_rec.term_id and not regular_rec.start_datetime and not holiday_rec.start_datetime:
            return regular_rec.day_of_week == holiday_rec.day_of_week

        return False

    def _cleanup_regular_classes_for_holiday(self):
        """Ensure no regular classes stay on the same day/column as a holiday.
        If school-wide holiday (class_id=False): unlinks ALL regular class sessions on that day/date.
        If class-specific (class_id=X): unlinks all regular class sessions for class X on that day/date."""
        for holiday in self:
            if not holiday.is_holiday or not holiday.active:
                continue

            base_domain = [
                ('id', '!=', holiday.id),
                ('is_holiday', '=', False),
                ('active', '=', True),
            ]
            if holiday.class_id:
                base_domain.append(('class_id', '=', holiday.class_id.id))

            all_candidates = self.env['school.timetable'].search(base_domain)
            to_remove = self.env['school.timetable']
            for cand in all_candidates:
                if self._is_holiday_applicable(cand, holiday):
                    to_remove |= cand

            if to_remove:
                to_remove.unlink()

    @api.model
    def action_cleanup_holiday_conflicts(self):
        """Purge any regular classes that exist concurrently with holidays across the system."""
        holidays = self.search([('is_holiday', '=', True), ('active', '=', True)])
        holidays._cleanup_regular_classes_for_holiday()
        return True

    def action_toggle_holiday(self):
        """Toggle holiday status for this timetable session."""
        for rec in self:
            if rec.is_holiday:
                first_tch = (rec.class_id and rec.class_id.teacher_id) or self.env['school.teacher'].search([], limit=1)
                first_sub = self.env['school.subject'].search([], limit=1)
                vals = {
                    'is_holiday': False,
                    'holiday_name': False,
                    'schedule_status': 'regular',
                }
                if not rec.teacher_id:
                    vals['teacher_id'] = first_tch.id if first_tch else False
                if not rec.subject_id and not rec.subject_ids:
                    if first_sub:
                        vals['subject_id'] = first_sub.id
                        vals['subject_ids'] = [(6, 0, [first_sub.id])]
                rec.write(vals)
            else:
                h_name = rec.holiday_name or _("School Holiday")
                rec.write({
                    'is_holiday': True,
                    'holiday_name': h_name,
                    'schedule_status': 'holiday',
                    'start_time': 7.5,
                    'end_time': 17.0,
                    'period': 'custom',
                    'teacher_id': False,
                    'subject_id': False,
                    'subject_ids': [(5, 0, 0)],
                })
                rec._cleanup_regular_classes_for_holiday()

    def action_view_class_students(self):
        """Navigate to students enrolled in the class or session."""
        self.ensure_one()
        target_domain = [('class_id', '=', self.class_id.id)] if self.class_id else [('id', 'in', self.student_ids.ids)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Class Students'),
            'res_model': 'school.student',
            'view_mode': 'list,form',
            'domain': target_domain,
            'context': {'default_class_id': self.class_id.id if self.class_id else False},
        }

    def action_view_teaching_assignments(self):
        """Navigate to teaching assignments associated with this session's teacher or class."""
        self.ensure_one()
        domain = []
        name = _('Teaching Assignments')
        if self.teacher_id:
            domain = [('teacher_id', '=', self.teacher_id.id)]
            name = _('Teaching Assignments - %s') % (self.teacher_id.name or '')
        elif self.class_id:
            domain = [('class_id', '=', self.class_id.id)]
            name = _('Teaching Assignments - %s') % (self.class_id.name or '')
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'school.teaching.assignment',
            'view_mode': 'list,kanban,form',
            'domain': domain,
            'context': {
                'default_teacher_id': self.teacher_id.id if self.teacher_id else False,
                'default_class_id': self.class_id.id if self.class_id else False,
            },
        }

    def action_anchor_to_current_week(self):
        """Re-anchor session datetime to match corresponding term week and weekday."""
        today = fields.Date.context_today(self)
        monday_this_week = today - timedelta(days=today.weekday())
        for rec in self:
            day_offset = int(rec.day_of_week) if rec.day_of_week else 0
            w_num = int(rec.week_number or 1)
            if w_num > 20:
                target_year = rec.term_id.date_start.year if (rec.term_id and rec.term_id.date_start) else today.year
                try:
                    session_date = date.fromisocalendar(target_year, w_num, day_offset + 1)
                except Exception:
                    session_date = monday_this_week + timedelta(days=day_offset)
            elif rec.term_id and rec.term_id.date_start:
                first_monday = rec.term_id.date_start - timedelta(days=rec.term_id.date_start.weekday())
                session_date = first_monday + timedelta(weeks=w_num - 1, days=day_offset)
            else:
                session_date = monday_this_week + timedelta(weeks=w_num - 1, days=day_offset)
            start_dt = rec._local_to_utc(session_date, rec.start_time)
            end_dt = rec._local_to_utc(session_date, rec.end_time)
            rec.write({
                'start_datetime': start_dt,
                'end_datetime': end_dt,
            })

    def action_open_week_selector(self):
        """Open the Select / Jump to Week wizard pre-filled with this session's week and class."""
        self.ensure_one()
        return {
            'name': _('Select / Jump to Week'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable.week.selector.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_term_id': self.term_id.id if self.term_id else False,
                'default_class_id': self.class_id.id if self.class_id else False,
                'default_teacher_id': self.teacher_id.id if self.teacher_id else False,
                'default_week_number': str(self.week_number) if self.week_number else '41',
            },
        }

    def action_teacher_request_permission(self):
        """Allow a teacher or admin to submit a leave / absence request for this specific session."""
        self.ensure_one()
        current_teacher = self.env['school.teacher'].search([('user_id', '=', self.env.uid)], limit=1)
        target_teacher = current_teacher or self.teacher_id
        session_date = None
        if self.start_datetime:
            local_dt = self._utc_to_local(self.start_datetime)
            session_date = local_dt.date() if local_dt else None
        if not session_date:
            today = fields.Date.context_today(self)
            monday_this_week = today - timedelta(days=today.weekday())
            day_offset = int(self.day_of_week) if self.day_of_week else 0
            session_date = monday_this_week + timedelta(days=day_offset)

        subject_label = self.subject_id.name if self.subject_id else (self.name or _('Session'))
        return {
            'name': _('Request Leave for Session: %s') % subject_label,
            'type': 'ir.actions.act_window',
            'res_model': 'school.permission',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_applicant_type': 'teacher',
                'default_teacher_id': target_teacher.id if target_teacher else False,
                'default_class_id': self.class_id.id if self.class_id else False,
                'default_timetable_id': self.id,
                'default_permission_type': 'leave',
                'default_session_type': 'custom',
                'default_start_date': session_date,
                'default_end_date': session_date,
                'default_start_time': self.start_time,
                'default_end_time': self.end_time,
            },
        }

    # -------------------------------------------------------------------------
    # CONSTRAINTS & CONFLICT CHECKING (SCOPED BY ACADEMIC TERM)
    # -------------------------------------------------------------------------
    def _is_term_conflict(self, other):
        """Returns True if self and other belong to the same term or overlapping terms,
        AND are scheduled on the same calendar date (if exact dates are specified)."""
        self.ensure_one()
        if self.is_holiday or other.is_holiday:
            return False
        if self.start_datetime and other.start_datetime:
            if self.start_datetime.date() != other.start_datetime.date():
                return False
        if self.week_number and other.week_number and self.week_number != other.week_number:
            return False
        if not self.term_id and not other.term_id:
            return True
        if self.term_id and other.term_id:
            if self.term_id.id == other.term_id.id:
                return True
            if self.term_id.date_start and self.term_id.date_end and other.term_id.date_start and other.term_id.date_end:
                return max(self.term_id.date_start, other.term_id.date_start) <= min(self.term_id.date_end, other.term_id.date_end)
            return False
        term_to_check = self.term_id or other.term_id
        return bool(term_to_check and term_to_check.state == 'active')

    def _check_holiday_conflict_single(self, rec, days):
        """Check if any active holiday conflicts with this regular session."""
        domain = [
            ('id', '!=', rec.id),
            ('is_holiday', '=', True),
            ('active', '=', True),
        ]
        candidate_holidays = self.env['school.timetable'].search(domain)
        for hol in candidate_holidays:
            if self._is_holiday_applicable(rec, hol):
                h_name = hol.holiday_name or hol.name or _("School Holiday")
                day_name = days.get(rec.day_of_week, '')
                rec_local_date = rec._get_session_calendar_date()
                date_str = str(rec_local_date) if rec_local_date else day_name
                scope_str = _("School-Wide Holiday") if not hol.class_id else _("Class Holiday (%s)") % hol.class_id.name
                raise ValidationError(_(
                    "Cannot schedule class session on %(date)s:\n"
                    "%(scope)s '%(holiday)s' is active on this day.\n"
                    "No regular classes are allowed to stay or be scheduled on a holiday."
                ) % {
                    'date': date_str,
                    'scope': scope_str,
                    'holiday': h_name,
                })

    @api.constrains('teacher_id', 'is_holiday', 'is_exam')
    def _check_teacher_required(self):
        for rec in self:
            if not rec.is_holiday and not rec.is_exam and not rec.teacher_id:
                raise ValidationError(_("Teacher is required for regular class sessions."))

    @api.constrains('subject_id', 'subject_ids', 'is_holiday', 'is_exam')
    def _check_subjects_present(self):
        for rec in self:
            if not rec.is_holiday and not rec.is_exam and not rec.subject_ids and not rec.subject_id:
                raise ValidationError(_("Please select at least one Subject for this timetable session."))

    @api.constrains('class_id', 'student_id', 'student_ids', 'is_holiday', 'is_exam')
    def _check_class_or_student(self):
        for rec in self:
            if rec.is_holiday or rec.is_exam:
                continue
            if not rec.class_id and not rec.student_id and not rec.student_ids:
                raise ValidationError(_("Please select either a Class or at least one Student for this timetable session."))

    @api.constrains('start_time', 'end_time', 'start_datetime', 'end_datetime')
    def _check_time_order(self):
        for rec in self:
            if rec.start_time < 0.0 or rec.start_time > 23.0:
                raise ValidationError(_(
                    "Invalid Start Time: Start Time (%(start)s) must be between 12:00 AM (00:00) and 11:00 PM (23:00)."
                ) % {
                    'start': rec._format_time(rec.start_time),
                })
            if rec.end_time <= 0.0 or rec.end_time > 24.0:
                raise ValidationError(_(
                    "Invalid End Time: End Time (%(end)s) must be between 00:01 and 24:00 (12:00 AM next day)."
                ) % {
                    'end': rec._format_time(rec.end_time),
                })
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

    def _check_teacher_conflict_single(self, rec, overlapping, days):
        """Check if teacher is already booked in overlapping sessions."""
        if not rec.teacher_id:
            return
        t_conflicts = [o for o in overlapping if o.teacher_id == rec.teacher_id]
        if t_conflicts:
            other = t_conflicts[0]
            target = other.student_id.name if other.student_id else (other.class_id.name if other.class_id else '')
            term_str = f" in {other.term_id.name}" if other.term_id else ""
            raise ValidationError(_(
                "Teacher Conflict Detected!\n"
                "Teacher '%(teacher)s' is already scheduled on %(day)s from %(start)s to %(end)s %(term)s "
                "for '%(target)s' (Subject: %(subject)s).\n"
                "A teacher cannot be booked for two overlapping sessions simultaneously."
            ) % {
                'teacher': rec.teacher_id.name,
                'day': days.get(rec.day_of_week),
                'start': rec._format_time(other.start_time),
                'end': rec._format_time(other.end_time),
                'term': term_str,
                'target': target,
                'subject': other.subject_id.name,
            })

    def _check_class_conflict_single(self, rec, overlapping, days):
        """Check if class is already scheduled in overlapping sessions."""
        if not rec.class_id or rec.student_id:
            return
        c_conflicts = [o for o in overlapping if o.class_id == rec.class_id and not o.student_id]
        if c_conflicts:
            other = c_conflicts[0]
            term_str = f" in {other.term_id.name}" if other.term_id else ""
            raise ValidationError(_(
                "Class Conflict Detected!\n"
                "Class '%(class_name)s' is already scheduled on %(day)s from %(start)s to %(end)s %(term)s "
                "for Subject '%(subject)s' with Teacher '%(teacher)s'.\n"
                "A class cannot have two concurrent class-wide subjects at the same time."
            ) % {
                'class_name': rec.class_id.name,
                'day': days.get(rec.day_of_week),
                'start': rec._format_time(other.start_time),
                'end': rec._format_time(other.end_time),
                'term': term_str,
                'subject': other.subject_id.name,
                'teacher': other.teacher_id.name,
            })

    def _check_student_conflict_single(self, rec, overlapping, days):
        """Check if any enrolled student is already scheduled in overlapping sessions."""
        students_to_check = rec.student_ids or (rec.student_id if rec.student_id else self.env['school.student'])
        if not students_to_check and rec.class_id:
            students_to_check = rec.class_id.student_ids
        if not students_to_check:
            return
        for other in overlapping:
            other_students = other.student_ids or (other.student_id if other.student_id else other.class_id.student_ids)
            colliding = students_to_check & other_students
            if colliding:
                student_names = ', '.join(colliding.mapped('name')) if colliding else _("Student")
                term_str = f" in {other.term_id.name}" if other.term_id else ""
                other_name = other.display_name or (other.subject_id.name if other.subject_id else '')
                raise ValidationError(_(
                    "Student Schedule Conflict Detected!\n"
                    "Student '%(students)s' already has another conflicting session on %(day)s %(term)s:\n"
                    "%(other_session)s (%(start)s - %(end)s).\n"
                    "A student cannot be scheduled in multiple timetable sessions at the same time."
                ) % {
                    'students': student_names,
                    'day': days.get(rec.day_of_week),
                    'term': term_str,
                    'other_session': other_name,
                    'start': rec._format_time(other.start_time),
                    'end': rec._format_time(other.end_time),
                })

    def _check_room_conflict_single(self, rec, overlapping, days):
        """Check if classroom is already occupied in overlapping sessions."""
        if not rec.room:
            return
        rec_room = rec.room.strip().lower()
        r_conflicts = [o for o in overlapping if o.room and o.room.strip().lower() == rec_room]
        if r_conflicts:
            other = r_conflicts[0]
            target = other.student_id.name if other.student_id else (other.class_id.name if other.class_id else '')
            term_str = f" in {other.term_id.name}" if other.term_id else ""
            raise ValidationError(_(
                "Room Collision Detected!\n"
                "Room '%(room)s' is already booked on %(day)s from %(start)s to %(end)s %(term)s "
                "for '%(target)s' (Teacher: %(teacher)s, Subject: %(subject)s).\n"
                "Two classes or sessions cannot occupy the same room simultaneously."
            ) % {
                'room': rec.room,
                'day': days.get(rec.day_of_week),
                'start': rec._format_time(other.start_time),
                'end': rec._format_time(other.end_time),
                'term': term_str,
                'target': target,
                'teacher': other.teacher_id.name,
                'subject': other.subject_id.name,
            })

    @api.constrains(
        'teacher_id', 'class_id', 'student_id', 'student_ids', 'room',
        'subject_id', 'subject_ids',
        'day_of_week', 'start_time', 'end_time', 'start_datetime', 'end_datetime',
        'term_id', 'week_number', 'is_holiday', 'active'
    )
    def _check_schedule_conflicts(self):
        """Unified conflict validation pipeline.
        Combines holiday, teacher, class, student, and room collision checks into one path,
        querying overlapping candidates only once for all checks."""
        days = dict(DAY_SELECTION)
        for rec in self:
            if not rec.active or rec.is_holiday:
                continue

            # 1. Holiday collision check
            self._check_holiday_conflict_single(rec, days)

            # 2. Shared Overlap Query: find all concurrent sessions once
            overlapping_candidates = self.search([
                ('id', '!=', rec.id),
                ('active', '=', True),
                ('is_holiday', '=', False),
                ('day_of_week', '=', rec.day_of_week),
                ('start_time', '<', rec.end_time),
                ('end_time', '>', rec.start_time),
            ])
            overlapping = [o for o in overlapping_candidates if rec._is_term_conflict(o)]
            if not overlapping:
                continue

            # 3. Check specific collisions against overlapping sessions
            self._check_teacher_conflict_single(rec, overlapping, days)
            self._check_class_conflict_single(rec, overlapping, days)
            self._check_student_conflict_single(rec, overlapping, days)
            self._check_room_conflict_single(rec, overlapping, days)
            self._check_subject_conflict_single(rec, overlapping, days)

    def _check_subject_conflict_single(self, rec, overlapping, days):
        """Check if any session has overlapping subjects for the same audience or class."""
        if rec.is_exam:
            return
        rec_subjects = rec.subject_ids or (rec.subject_id if rec.subject_id else self.env['school.subject'])
        if not rec_subjects:
            return

        for other in overlapping:
            if other.is_exam:
                continue
            other_subjects = other.subject_ids or (other.subject_id if other.subject_id else self.env['school.subject'])
            common_subjects = rec_subjects & other_subjects
            if not common_subjects:
                continue

            # Check if they share the same class or common students
            shares_class = rec.class_id and other.class_id and (rec.class_id == other.class_id)
            rec_students = rec.student_ids or (rec.student_id if rec.student_id else (rec.class_id.student_ids if rec.class_id else self.env['school.student']))
            other_students = other.student_ids or (other.student_id if other.student_id else (other.class_id.student_ids if other.class_id else self.env['school.student']))
            shares_students = bool(rec_students & other_students)

            if shares_class or shares_students:
                subj_name = ', '.join(common_subjects.mapped('name'))
                term_str = f" in {other.term_id.name}" if other.term_id else ""
                target_name = rec.class_id.name if rec.class_id else (rec.student_id.name if rec.student_id else _("Students"))
                raise ValidationError(_(
                    "Subject Conflict Detected!\n"
                    "The subject '%(subject)s' is already scheduled at the same time on %(day)s from %(start)s to %(end)s%(term)s for '%(target)s'.\n"
                    "A class or student cannot have the same subject scheduled concurrently at the same time."
                ) % {
                    'subject': subj_name,
                    'day': days.get(rec.day_of_week),
                    'start': rec._format_time(other.start_time),
                    'end': rec._format_time(other.end_time),
                    'term': term_str,
                    'target': target_name,
                })

    def _check_holiday_conflict(self):
        self._check_schedule_conflicts()

    def _check_teacher_conflict(self):
        self._check_schedule_conflicts()

    def _check_class_conflict(self):
        self._check_schedule_conflicts()

    def _check_student_conflict(self):
        self._check_schedule_conflicts()

    def _check_room_conflict(self):
        self._check_schedule_conflicts()

    def _check_subject_conflict(self):
        self._check_schedule_conflicts()

    def action_open_exam(self):
        self.ensure_one()
        if not self.exam_id:
            return False
        return {
            'name': self.exam_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.exam',
            'res_id': self.exam_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def action_open_master_timetable(self):
        """Open master timetable calendar dynamically anchored to the active term's start date."""
        today = fields.Date.context_today(self)
        active_term = self.env['school.term'].search([('state', '=', 'active')], limit=1)
        if not active_term:
            active_term = self.env['school.term'].search([
                ('date_start', '<=', today),
                ('date_end', '>=', today),
            ], limit=1)
        if not active_term:
            active_term = self.env['school.term'].search([], order='date_start desc', limit=1)

        ctx = {
            'search_default_filter_mon_fri': 1,
        }
        if active_term and active_term.state == 'active':
            ctx['search_default_filter_active_term'] = 1

        if active_term and active_term.date_start:
            ctx['default_term_id'] = active_term.id
            if active_term.date_end and (today < active_term.date_start or today > active_term.date_end):
                ctx['initial_date'] = active_term.date_start.isoformat()
            else:
                ctx['initial_date'] = today.isoformat()
        else:
            ctx['initial_date'] = today.isoformat()

        user = self.env.user
        is_admin = user.has_group('school_management.group_school_admin')
        is_teacher = user.has_group('school_management.group_school_teacher')
        is_student = user.has_group('school_management.group_school_student')
        if is_student and not is_admin:
            ctx['search_default_filter_my_timetable'] = 1
        elif is_teacher and not is_admin:
            ctx['search_default_filter_my_teaching'] = 1

        action = self.env.ref('school_management.action_timetable').read()[0]
        action['context'] = ctx
        return action
