import base64
import csv
import io

from odoo import fields, models
from odoo.exceptions import UserError, ValidationError


class ImportSchoolHolidayWizard(models.TransientModel):
    _name = 'school.import.holiday.wizard'
    _description = 'Import School Public Holidays'

    file = fields.Binary(
        string='File',
        required=True,
    )

    filename = fields.Char(
        string='Filename',
    )

    import_mode = fields.Selection(
        [
            ('create', 'Create New Holidays'),
            ('update', 'Create or Update'),
        ],
        string='Import Mode',
        default='create',
        required=True,
    )

    def action_import(self):
        self.ensure_one()

        if not self.file:
            raise UserError('Please upload a file.')

        filename = (self.filename or '').lower()

        if not filename.endswith('.csv'):
            raise UserError(
                'Please upload a CSV file.\n\n'
                'Example:\n'
                'public_holidays.csv'
            )

        try:
            file_content = base64.b64decode(self.file)
            decoded_content = file_content.decode('utf-8-sig')
        except Exception as error:
            raise UserError(
                f'Unable to read the uploaded file: {error}'
            )

        reader = csv.DictReader(
            io.StringIO(decoded_content)
        )

        required_columns = {
            'name',
            'date',
        }

        actual_columns = set(
            reader.fieldnames or []
        )

        missing_columns = required_columns - actual_columns

        if missing_columns:
            raise UserError(
                'Missing required columns:\n%s'
                % ', '.join(sorted(missing_columns))
            )

        created = 0
        updated = 0
        errors = []

        Holiday = self.env['school.public.holiday']

        for row_number, row in enumerate(
            reader,
            start=2,
        ):

            try:

                name = (row.get('name') or '').strip()
                date_value = (row.get('date') or '').strip()
                end_date_value = (
                    row.get('end_date') or ''
                ).strip()

                holiday_type = (
                    row.get('holiday_type')
                    or 'national'
                ).strip().lower()

                description = (
                    row.get('description')
                    or ''
                ).strip()

                if not name:
                    raise ValidationError(
                        'Holiday name is required.'
                    )

                if not date_value:
                    raise ValidationError(
                        'Start date is required.'
                    )

                date = fields.Date.from_string(
                    date_value
                )

                end_date = False

                if end_date_value:
                    end_date = fields.Date.from_string(
                        end_date_value
                    )

                allowed_types = {
                    'national',
                    'religious',
                    'school',
                    'other',
                }

                if holiday_type not in allowed_types:
                    raise ValidationError(
                        'Invalid holiday_type. '
                        'Allowed values: %s'
                        % ', '.join(sorted(allowed_types))
                    )

                values = {
                    'name': name,
                    'date': date,
                    'end_date': end_date,
                    'holiday_type': holiday_type,
                    'description': description,
                    'company_id': self.env.company.id,
                }

                existing = Holiday.search([
                    ('name', '=', name),
                    ('date', '=', date),
                    ('company_id', '=', self.env.company.id),
                ], limit=1)

                if existing and self.import_mode == 'update':

                    existing.write(values)

                    updated += 1

                elif existing:

                    raise ValidationError(
                        'Holiday already exists.'
                    )

                else:

                    Holiday.create(values)

                    created += 1

            except Exception as error:

                errors.append(
                    f'Row {row_number}: {error}'
                )

        if errors:
            message = (
                'Import completed with errors.\n\n'
                f'Created: {created}\n'
                f'Updated: {updated}\n'
                f'Errors: {len(errors)}\n\n'
                + '\n'.join(errors)
            )

            raise UserError(message)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Successful',
                'message': (
                    f'{created} holiday(s) created '
                    f'and {updated} holiday(s) updated.'
                ),
                'type': 'success',
                'sticky': False,
            },
        }