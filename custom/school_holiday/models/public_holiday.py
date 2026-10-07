# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
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
            ('public', 'Public Holiday'),
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

    @api.constrains('name', 'date', 'end_date', 'company_id')
    def _check_overlap(self):
        for record in self:
            if not record.date or not record.name:
                continue

            record_start = record.date
            record_end = record.end_date or record.date

            overlapping = self.search([
                ('id', '!=', record.id),
                ('active', '=', True),
                ('company_id', '=', record.company_id.id),
                ('name', '=ilike', record.name.strip()),
                ('date', '<=', record_end),
                '|',
                '&', ('end_date', '=', False), ('date', '>=', record_start),
                '&', ('end_date', '!=', False), ('end_date', '>=', record_start),
            ])

            if overlapping:
                raise ValidationError(
                    _('A holiday with the name "%(name)s" already exists covering this date period:\n%(overlap)s')
                    % {
                        'name': record.name,
                        'overlap': '\n'.join(overlapping.mapped('name')),
                    }
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

    def action_validate_and_reschedule(self):
        """
        Validate all timetable schedules against this holiday (or selected holidays)
        and move any conflicting class sessions to the next week via the dedicated service.
        """
        service = self.env['school.holiday.timetable.service']
        total_moved = 0
        for record in self:
            dates = record.get_holiday_dates()
            moved = service.move_timetable_sessions_for_dates(
                dates,
                holiday_name=record.name,
                company_id=record.company_id.id,
            )
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
            service = self.env['school.holiday.timetable.service']
            for record in records:
                if record.active and record.date:
                    dates = record.get_holiday_dates()
                    service.move_timetable_sessions_for_dates(
                        dates,
                        holiday_name=record.name,
                        company_id=record.company_id.id,
                    )
        return records

    def write(self, vals):
        res = super().write(vals)
        if ('date' in vals or 'end_date' in vals or 'active' in vals) and vals.get('active', True):
            if not self.env.context.get('skip_auto_reschedule'):
                service = self.env['school.holiday.timetable.service']
                for record in self:
                    if record.active and record.date:
                        dates = record.get_holiday_dates()
                        service.move_timetable_sessions_for_dates(
                            dates,
                            holiday_name=record.name,
                            company_id=record.company_id.id,
                        )
        return res

    def action_archive(self):
        self.write({'active': False})

    def action_unarchive(self):
        self.write({'active': True})
