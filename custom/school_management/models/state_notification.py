import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class SchoolStateChangeNotification(models.AbstractModel):
    _name = 'school.state.notification'
    _description = 'Send email notification when the state/status of a record changes'

    _state_field = 'status'

    def _get_state_email_template(self):
        return False

    def _get_state_change_recipients(self):
        return False

    def _notify_state_change(self, old_val, new_val):
        template_xmlid = self._get_state_email_template()
        if not template_xmlid or not new_val or old_val == new_val:
            return
        try:
            template = self.env.ref(template_xmlid)
        except ValueError:
            _logger.warning(
                'Status notification skipped: template %r not found', template_xmlid, exc_info=True
            )
            return
        for rec in self:
            recipients = rec._get_state_change_recipients()
            if not recipients:
                continue
            try:
                template.send_mail(
                    rec.id,
                    force_send=False,
                    email_values={'email_to': recipients},
                )
            except Exception:
                _logger.warning(
                    'Failed to send status change email for %s (id %s)',
                    rec._name, rec.id, exc_info=True,
                )

    @api.model_create_multi
    def create(self, vals_list):
        state_field = self._state_field
        default_val = self.default_get([state_field]).get(state_field)
        records = super().create(vals_list)
        for rec in records:
            new_val = rec[state_field]
            if new_val and new_val != default_val:
                rec._notify_state_change(False, new_val)
        return records

    def write(self, vals):
        state_field = self._state_field
        old_vals = {rec.id: rec[state_field] for rec in self} if state_field in vals else {}
        result = super().write(vals)
        if old_vals:
            for rec in self:
                rec._notify_state_change(old_vals.get(rec.id), rec[state_field])
        return result