from odoo import models, fields, _


class SchoolStudentStopWizard(models.TransientModel):
    _name = 'school.student.stop.wizard'
    _description = 'Stop Student Study Wizard'

    student_id = fields.Many2one('school.student', string='Student', required=True)
    stop_date = fields.Date(string='Stop Date', required=True, default=fields.Date.today)
    reason_type = fields.Selection([
        ('kicked', 'Dismissed / Kicked (Disciplinary)'),
        ('dropped', 'Requested to Stop / Dropped Out'),
        ('financial', 'Financial Difficulty'),
        ('personal', 'Personal / Family Reasons'),
        ('transfer', 'Transferred to Another School'),
        ('health', 'Health / Medical Reasons'),
        ('other', 'Other Reason'),
    ], string='Reason Category', required=True, default='dropped')
    stop_reason = fields.Text(string='Detailed Reason / Remarks')

    def action_confirm_stop(self):
        self.ensure_one()
        category_label = dict(self._fields['reason_type'].selection).get(self.reason_type, '')
        full_reason = f"[{category_label}] {self.stop_reason}" if self.stop_reason else f"[{category_label}]"
        self.student_id.write({
            'study_status': 'stopped',
            'stop_date': self.stop_date,
            'stop_reason': full_reason,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Student Stopped Studying'),
                'message': _("Student '%s' has been marked as Stopped Studying.") % self.student_id.name,
                'type': 'warning',
                'sticky': False,
            }
        }
