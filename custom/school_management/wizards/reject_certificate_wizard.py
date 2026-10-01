from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolCertificateRejectWizard(models.TransientModel):
    _name = 'school.certificate.reject.wizard'
    _description = 'Decline / Reject Certificate Print Request'

    certificate_id = fields.Many2one(
        'school.certificate',
        string='Certificate / Transcript',
        required=True,
    )
    student_id = fields.Many2one(
        'school.student',
        related='certificate_id.student_id',
        string='Student',
        readonly=True,
    )
    certificate_type = fields.Selection(
        related='certificate_id.certificate_type',
        string='Credential Type',
        readonly=True,
    )
    rejection_reason = fields.Text(
        string='Reason for Refusal',
        required=True,
        help='State clearly why the print request is declined (e.g. pending tuition payment, incomplete grades).',
    )

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.certificate_id:
            raise UserError(_("No certificate or transcript selected."))
        self.certificate_id.action_reject_print(reason=self.rejection_reason)
        return {'type': 'ir.actions.act_window_close'}
