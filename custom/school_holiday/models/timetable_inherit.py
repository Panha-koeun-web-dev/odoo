from odoo import models, api, _
from odoo.exceptions import ValidationError


class SchoolTimetable(models.Model):
    _inherit = 'school.timetable'

    def _check_holiday_conflict_single(self, rec, days):
        """Extend holiday conflict check to also validate against school.public.holiday."""
        super()._check_holiday_conflict_single(rec, days)
        if rec.is_holiday or not rec.active:
            return

        rec_date = rec._get_session_calendar_date()
        if rec_date:
            cid = rec.company_id.id if hasattr(rec, 'company_id') and rec.company_id else False
            public_hol = self.env['school.public.holiday'].is_holiday(rec_date, company_id=cid)
            if public_hol:
                day_name = days.get(rec.day_of_week, '')
                date_str = str(rec_date) if rec_date else day_name
                raise ValidationError(_(
                    "Cannot schedule class session on %(date)s:\n"
                    "Public Holiday '%(holiday)s' is active on this day.\n"
                    "No regular classes are allowed to stay or be scheduled on a public holiday."
                ) % {
                    'date': date_str,
                    'holiday': public_hol.name,
                })
