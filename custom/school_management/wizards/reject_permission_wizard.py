from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolPermissionRejectWizard(models.TransientModel):
    _name = 'school.permission.reject.wizard'
    _description = 'Reject / Not Approve Permission Request'

    permission_id = fields.Many2one(
        'school.permission',
        string='Permission Request',
        required=True,
    )
    applicant_type = fields.Selection(
        related='permission_id.applicant_type',
        string='Applicant Type',
        readonly=True,
    )
    applicant_name = fields.Char(
        related='permission_id.applicant_name',
        string='Applicant',
        readonly=True,
    )
    student_id = fields.Many2one(
        'school.student',
        related='permission_id.student_id',
        string='Student',
        readonly=True,
    )
    teacher_id = fields.Many2one(
        'school.teacher',
        related='permission_id.teacher_id',
        string='Teacher',
        readonly=True,
    )
    permission_type = fields.Selection(
        related='permission_id.permission_type',
        string='Permission Type',
        readonly=True,
    )
    start_date = fields.Date(
        related='permission_id.start_date',
        string='Start Date',
        readonly=True,
    )
    end_date = fields.Date(
        related='permission_id.end_date',
        string='End Date',
        readonly=True,
    )
    duration_days = fields.Float(
        related='permission_id.duration_days',
        string='Duration (Days)',
        readonly=True,
    )
    rejection_reason = fields.Text(
        string='Reason for Non-Approval',
        required=True,
        help='State clearly why the permission request cannot be approved so the applicant is properly informed.',
    )

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.permission_id:
            raise UserError(_("No permission request selected."))
        self.permission_id.action_reject(reason=self.rejection_reason)
