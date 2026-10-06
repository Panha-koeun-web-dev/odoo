from odoo import api, fields, models
from odoo.exceptions import ValidationError


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
        string='Duration',
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

    @api.depends('date')
    def _compute_year(self):
        for record in self:
            record.year = record.date.year if record.date else False

    @api.depends('date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if not record.date:
                record.duration = 0
            elif record.end_date:
                record.duration = (
                    record.end_date - record.date
                ).days + 1
            else:
                record.duration = 1

    @api.constrains('date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.end_date < record.date:
                raise ValidationError(
                    'The end date cannot be earlier than the start date.'
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
                ('end_date', '=', False),
                ('end_date', '>=', record_start),
            ])

            if overlapping:
                raise ValidationError(
                    'This holiday overlaps with another public holiday:\n%s'
                    % '\n'.join(overlapping.mapped('name'))
                )

    def name_get(self):
        result = []

        for record in self:
            if record.end_date:
                name = f'{record.name} ({record.date} - {record.end_date})'
            elif record.date:
                name = f'{record.name} ({record.date})'
            else:
                name = record.name

            result.append((record.id, name))

        return result

    @api.model
    def is_holiday(self, check_date, company_id=None):
        """
        Check whether a specific date is a public holiday.

        Returns:
            SchoolPublicHoliday recordset
        """
        if not check_date:
            return self.browse()

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
            ('end_date', '=', False),
            ('end_date', '>=', check_date),
        ], limit=1)

    def action_archive(self):
        self.write({'active': False})

    def action_unarchive(self):
        self.write({'active': True})