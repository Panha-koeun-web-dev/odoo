# -*- coding: utf-8 -*-
from datetime import datetime, date, time, timedelta
import pytz
from odoo import api, fields, models, _


class SchoolHolidayTimetableService(models.AbstractModel):
    """
    Dedicated domain service to decouple timetable synchronization,
    calendar visualization, and conflict cascading from the core holiday model.
    """
    _name = 'school.holiday.timetable.service'
    _description = 'Holiday Timetable Synchronization Service'

    @api.model
    def get_non_holiday_shift_days(self, original_date, company_id=None):
        """
        Find the number of days forward to the next school day (Monday to Friday)
        after the holiday finishes that does not fall on an active public holiday.
        """
        PublicHoliday = self.env['school.public.holiday']
        curr = original_date + timedelta(days=1)
        for _ in range(365):
            # Skip weekends (Saturday=5, Sunday=6)
            if curr.weekday() >= 5:
                curr += timedelta(days=1)
                continue
            if not PublicHoliday.is_holiday(curr, company_id=company_id):
                return (curr - original_date).days
            curr += timedelta(days=1)
        return 1

    @api.model
    def move_timetable_sessions_for_dates(self, dates, holiday_name=None, company_id=None):
        """
        Compare study schedule sessions (school.timetable) with the given holiday dates.
        For any regular session scheduled on a holiday date, move it to the next school day
        after the holiday finishes (skipping weekends and any subsequent holidays).
        Cascades subsequent sessions in the same slot/term to prevent overlapping collisions.
        Also creates or updates a holiday session in school.timetable for calendar visibility.
        """
        if not dates:
            return 0

        Timetable = self.env['school.timetable']
        min_date = min(dates)
        max_date = max(dates)

        # Optimize search domain with bounded UTC datetimes instead of loading all database records
        min_dt = datetime.combine(min_date, time.min) - timedelta(days=1)
        max_dt = datetime.combine(max_date, time.max) + timedelta(days=1)

        domain = [
            ('is_holiday', '=', False),
            ('active', '=', True),
            ('start_datetime', '>=', min_dt),
            ('start_datetime', '<=', max_dt),
        ]
        if company_id and 'company_id' in Timetable._fields:
            domain.append(('company_id', '=', company_id))

        candidate_sessions = Timetable.search(domain)
        sessions_on_holiday = [
            s for s in candidate_sessions
            if s._get_session_calendar_date() in dates
        ]

        if not sessions_on_holiday:
            # Ensure calendar display blocks even if no regular classes conflicted
            self.ensure_holiday_timetable_sessions(dates, holiday_name=holiday_name, company_id=company_id)
            return 0

        moved_count = 0
        processed_slots = set()

        for s in sessions_on_holiday:
            slot_key = (
                s.class_id.id if s.class_id else False,
                s.student_id.id if s.student_id else False,
                s.day_of_week,
                s.start_time,
                s.term_id.id if s.term_id else False,
            )
            if slot_key in processed_slots:
                continue
            processed_slots.add(slot_key)

            # Find all sessions in this slot on or after the holiday session, sorted descending (latest first)
            slot_domain = [
                ('active', '=', True),
                ('is_holiday', '=', False),
                ('class_id', '=', s.class_id.id if s.class_id else False),
                ('student_id', '=', s.student_id.id if s.student_id else False),
                ('day_of_week', '=', s.day_of_week),
                ('start_time', '=', s.start_time),
                ('term_id', '=', s.term_id.id if s.term_id else False),
                ('start_datetime', '>=', s.start_datetime),
            ]
            if company_id and 'company_id' in Timetable._fields:
                slot_domain.append(('company_id', '=', company_id))

            series = Timetable.search(slot_domain, order='start_datetime desc')
            session_date = s._get_session_calendar_date()
            shift_days = self.get_non_holiday_shift_days(session_date, company_id=company_id)

            for item in series:
                old_start = item.start_datetime
                old_end = item.end_datetime
                if not old_start or not old_end:
                    continue
                new_start = old_start + timedelta(days=shift_days)
                new_end = old_end + timedelta(days=shift_days)
                old_cal_date = item._get_session_calendar_date()
                new_cal_date = old_cal_date + timedelta(days=shift_days) if old_cal_date else False
                new_day_of_week = str(new_cal_date.weekday()) if new_cal_date else item.day_of_week
                new_week = item.week_number + (shift_days // 7) if item.week_number else False
                item.write({
                    'start_datetime': new_start,
                    'end_datetime': new_end,
                    'day_of_week': new_day_of_week,
                    'week_number': new_week,
                })
                moved_count += 1

        # Ensure holiday timetable sessions are displayed on calendar for the holiday dates
        self.ensure_holiday_timetable_sessions(dates, holiday_name=holiday_name, company_id=company_id)

        return moved_count

    @api.model
    def _get_tz(self, company_id=None):
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company
        tz_name = (
            self.env.context.get('tz')
            or (self.env.user.tz if self.env.user and self.env.user.tz else False)
            or (company.partner_id.tz if company and company.partner_id.tz else False)
            or 'Asia/Phnom_Penh'
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.timezone('Asia/Phnom_Penh')

    @api.model
    def ensure_holiday_timetable_sessions(self, dates, holiday_name=None, company_id=None):
        """Create or ensure school.timetable records with is_holiday=True exist for the calendar."""
        Timetable = self.env['school.timetable']
        user_tz = self._get_tz(company_id=company_id)

        for d in dates:
            # Check if holiday session already exists on this date
            day_min_dt = datetime.combine(d, time.min) - timedelta(days=1)
            day_max_dt = datetime.combine(d, time.max) + timedelta(days=1)
            search_domain = [
                ('is_holiday', '=', True),
                ('active', '=', True),
                ('start_datetime', '>=', day_min_dt),
                ('start_datetime', '<=', day_max_dt),
            ]
            if company_id and 'company_id' in Timetable._fields:
                search_domain.append(('company_id', '=', company_id))

            existing = [
                t for t in Timetable.search(search_domain)
                if t._get_session_calendar_date() == d
            ]
            if existing:
                continue

            naive_start = datetime.combine(d, time(7, 30, 0))
            naive_end = datetime.combine(d, time(17, 0, 0))
            try:
                start_dt = user_tz.localize(naive_start).astimezone(pytz.utc).replace(tzinfo=None)
                end_dt = user_tz.localize(naive_end).astimezone(pytz.utc).replace(tzinfo=None)
            except Exception:
                start_dt = naive_start
                end_dt = naive_end

            # Find active term if any
            term_domain = [
                ('date_start', '<=', d),
                ('date_end', '>=', d),
                ('state', '=', 'active'),
            ]
            term = self.env['school.term'].search(term_domain, limit=1)
            week_num = False
            if term and term.date_start:
                first_mon = term.date_start - timedelta(days=term.date_start.weekday())
                week_num = (d - first_mon).days // 7 + 1

            h_name = holiday_name or _("School Public Holiday")

            vals = {
                'name': h_name,
                'holiday_name': h_name,
                'is_holiday': True,
                'schedule_status': 'holiday',
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'start_time': 7.5,
                'end_time': 17.0,
                'period': 'custom',
                'day_of_week': str(d.weekday()),
                'week_number': week_num or d.isocalendar()[1],
                'term_id': term.id if term else False,
            }
            if company_id and 'company_id' in Timetable._fields:
                vals['company_id'] = company_id
            Timetable.create(vals)
