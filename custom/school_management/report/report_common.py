import base64
from pathlib import Path

from odoo import models, fields
from odoo.tools import format_date, format_datetime
from odoo.tools.image import image_data_uri


def _fmt_number(value):
    return '{:,.2f}'.format(value or 0.0)


class SchoolReportCommon(models.AbstractModel):
    _name = 'school.report.common'
    _description = 'Common helpers for School Reports'

    def _format_date(self, value):
        return format_date(self.env, value) if value else ''

    def _format_datetime(self, value):
        return format_datetime(self.env, value) if value else ''

    def _format_number(self, value):
        return _fmt_number(value)

    def _generated_on(self):
        return format_datetime(self.env, fields.Datetime.now())

    def _company_logo_uri(self, company):
        if company.logo and not company.uses_default_logo:
            return image_data_uri(company.logo)
        return False

    def _static_image_uri(self, rel_path):
        module_root = Path(__file__).resolve().parent.parent
        img_path = module_root / rel_path
        if img_path.exists():
            return image_data_uri(base64.b64encode(img_path.read_bytes()))
        return False

    def _selection_label(self, model_name, field_name, value):
        field = self.env[model_name]._fields.get(field_name)
        if field and field.selection and value:
            return dict(field.selection).get(value, value)
        return value
