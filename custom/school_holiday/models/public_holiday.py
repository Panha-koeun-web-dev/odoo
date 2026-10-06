from datetime import datetime, date, time, timedelta
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class SchoolPublicHoliday(models.Model):
    _name = 'school.public.holiday'
    _description = 'School Public Holiday'
    _order = 'date asc, name asc'
    _rec_name = 'name'

    name = fields.Char(
        string='Holiday Name',
        required=True,
        index=True,
    )

    date = fields.Date(
        string='Start Date',
        required=True,
        index=True,
    )

    end_date = fields.Date(
        string='End Date',
        index=True,
    )

    year = fields.Integer(
        string='Year',
        compute='_compute_year',
        store=True,
        index=True,
    )

    holiday_type = fields.Selection(
        [
            ('national', 'National Holiday'),
            ('religious', 'Religious Holiday'),
            ('school', 'School Holiday'),
            ('other', 'Other'),
        ],
        string='Holiday Type',
        required=True,
        default='national',
    )

    description = fields.Text(
        string='Description',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    duration = fields.Integer(
        string='Duration (Days)',
        compute='_compute_duration',
        store=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.depends('name', 'date', 'end_date')
    def _compute_display_name(self):
        for record in self:
            if record.end_date and record.date and record.end_date != record.date:
                record.display_name = f"{record.name} ({record.date} to {record.end_date})"
            elif record.date:
                record.display_name = f"{record.name} ({record.date})"
            else:
                record.display_name = record.name or ''

    @api.depends('date')
    def _compute_year(self):
        for record in self:
            record.year = record.date.year if record.date else False

    @api.depends('date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if not record.date:
                record.duration = 0
            elif record.end_date and record.end_date >= record.date:
                record.duration = (record.end_date - record.date).days + 1
            else:
                record.duration = 1

    @api.constrains('date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.date and record.end_date < record.date:
                raise ValidationError(
                    _('The end date cannot be earlier than the start date.')
                )

    @api.constrains('date', 'end_date')
    def _check_overlap(self):
        for record in self:
            if not record.date:
                continue

            record_start = record.date
            record_end = record.end_date or record.date

            overlapping = self.search([
                ('id', '!=', record.id),
                ('active', '=', True),
                ('company_id', '=', record.company_id.id),
                ('date', '<=', record_end),
                '|',
                '&', ('end_date', '=', False), ('date', '>=', record_start),
                '&', ('end_date', '!=', False), ('end_date', '>=', record_start),
            ])

            if overlapping:
                raise ValidationError(
                    _('This holiday overlaps with another public holiday:\n%s')
                    % '\n'.join(overlapping.mapped('name'))
                )

    @api.model
    def is_holiday(self, check_date, company_id=None):
        """
        Check whether a specific date is an active public holiday.

        Args:
            check_date: date object, datetime object, or date string ('YYYY-MM-DD').
            company_id: optional res.company id.

        Returns:
            SchoolPublicHoliday recordset (limit 1) or empty recordset.
        """
        if not check_date:
            return self.browse()

        if isinstance(check_date, str):
            check_date = fields.Date.from_string(check_date)
        elif isinstance(check_date, datetime):
            check_date = check_date.date()

        company = (
            self.env['res.company'].browse(company_id)
            if company_id
            else self.env.company
        )

        return self.search([
            ('active', '=', True),
            ('company_id', '=', company.id),
            ('date', '<=', check_date),
            '|',
            '&', ('end_date', '=', False), ('date', '>=', check_date),
            '&', ('end_date', '!=', False), ('end_date', '>=', check_date),
        ], limit=1)

    def get_holiday_dates(self):
        """Return list of datetime.date objects covered by this holiday record."""
        self.ensure_one()
        if not self.date:
            return []
        start_d = self.date
        end_d = self.end_date or self.date
        if end_d < start_d:
            end_d = start_d
        day_count = (end_d - start_d).days + 1
        return [start_d + timedelta(days=i) for i in range(day_count)]

    def _get_non_holiday_shift_days(self, original_date):
        """
        Find the number of days forward (+7, +14, etc.) to the next week's matching day
        that does not fall on an active public holiday.
        """
        shift = 7
        for _ in range(52):
            target = original_date + timedelta(days=shift)
            if not self.is_holiday(target, self.company_id.id if self.company_id else None):
                return shift
            shift += 7
        return 7

    def _move_timetable_sessions_for_dates(self, dates, holiday_name=None):
        """
        Compare study schedule sessions (school.timetable) with the given holiday dates.
        For any regular session scheduled on a holiday date, move it to the next week
        (+7 days or next non-holiday week).
        Cascades subsequent sessions in the same slot/term to prevent overlapping collisions.
        Also creates or updates a holiday session in school.timetable for calendar visibility.
        """
        Timetable = self.env['school.timetable']
        if not dates:
            return 0

        # 1. Find all active regular sessions on these holiday dates
        all_active_regular = Timetable.search([
            ('is_holiday', '=', False),
            ('active', '=', True),
        ])
        sessions_on_holiday = [
            s for s in all_active_regular
            if s._get_session_calendar_date() in dates
        ]

        moved_count = 0

        # Group sessions by slot to cascade cleanly:
        # Slot: (class_id, student_id, day_of_week, start_time, term_id)
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
            series = Timetable.search([
                ('active', '=', True),
                ('is_holiday', '=', False),
                ('class_id', '=', s.class_id.id if s.class_id else False),
                ('student_id', '=', s.student_id.id if s.student_id else False),
                ('day_of_week', '=', s.day_of_week),
                ('start_time', '=', s.start_time),
                ('term_id', '=', s.term_id.id if s.term_id else False),
                ('start_datetime', '>=', s.start_datetime),
            ], order='start_datetime desc')

            session_date = s._get_session_calendar_date()
            shift_days = self._get_non_holiday_shift_days(session_date)

            for item in series:
                old_start = item.start_datetime
                old_end = item.end_datetime
                if not old_start or not old_end:
                    continue
                new_start = old_start + timedelta(days=shift_days)
                new_end = old_end + timedelta(days=shift_days)
                new_week = item.week_number + (shift_days // 7) if item.week_number else False
                item.write({
                    'start_datetime': new_start,
                    'end_datetime': new_end,
                    'week_number': new_week,
                })
                moved_count += 1

        # 2. Ensure holiday timetable sessions are displayed on calendar for the holiday dates
        self._ensure_holiday_timetable_sessions(dates, holiday_name)

        return moved_count

    def _ensure_holiday_timetable_sessions(self, dates, holiday_name=None):
        """Create or ensure school.timetable records with is_holiday=True exist for the calendar."""
        Timetable = self.env['school.timetable']
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        for d in dates:
            # Check if holiday session already exists on this date
            existing = [
                t for t in Timetable.search([('is_holiday', '=', True), ('active', '=', True)])
                if t._get_session_calendar_date() == d
            ]
            if existing:
                continue

            # Determine UTC start and end for 07:30 to 17:00 local time
            naive_start = datetime.combine(d, time(7, 30, 0))
            naive_end = datetime.combine(d, time(17, 0, 0))
            try:
                start_dt = user_tz.localize(naive_start).astimezone(pytz.utc).replace(tzinfo=None)
                end_dt = user_tz.localize(naive_end).astimezone(pytz.utc).replace(tzinfo=None)
            except Exception:
                start_dt = naive_start
                end_dt = naive_end

            # Find active term if any
            term = self.env['school.term'].search([
                ('date_start', '<=', d),
                ('date_end', '>=', d),
                ('state', '=', 'active'),
            ], limit=1)
            week_num = False
            if term and term.date_start:
                first_mon = term.date_start - timedelta(days=term.date_start.weekday())
                week_num = (d - first_mon).days // 7 + 1

            h_name = holiday_name or self.name or _("School Public Holiday")
            Timetable.create({
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
            })

    def action_validate_and_reschedule(self):
        """
        Validate all timetable schedules against this holiday (or selected holidays)
        and move any conflicting class sessions to the next week.
        """
        total_moved = 0
        for record in self:
            dates = record.get_holiday_dates()
            moved = record._move_timetable_sessions_for_dates(dates, holiday_name=record.name)
            total_moved += moved

        message = (
            _("Successfully validated schedules!\nMoved %d class session(s) to next week.")
            % total_moved
            if total_moved
            else _("Schedule validation complete: No conflicting class sessions found on holiday dates.")
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Schedule Validation & Rescheduling'),
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_auto_reschedule'):
            for record in records:
                if record.active and record.date:
                    dates = record.get_holiday_dates()
                    record._move_timetable_sessions_for_dates(dates, holiday_name=record.name)
        return records

    def write(self, vals):
        res = super().write(vals)
        if ('date' in vals or 'end_date' in vals or 'active' in vals) and vals.get('active', True):
            if not self.env.context.get('skip_auto_reschedule'):
                for record in self:
                    if record.active and record.date:
                        dates = record.get_holiday_dates()
                        record._move_timetable_sessions_for_dates(dates, holiday_name=record.name)
        return res

    def action_archive(self):
        self.write({'active': False})

    def action_unarchive(self):
        self.write({'active': True})
