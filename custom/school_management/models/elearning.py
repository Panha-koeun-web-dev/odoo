from odoo import models, _
from odoo.exceptions import AccessError


class SlideChannelSchool(models.Model):
    _inherit = 'slide.channel'

    def action_open_school_enroll_students(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise AccessError(_('Only school administrators can enroll school students.'))
        self.ensure_one()
        return {
            'name': _('Enroll Selected Students'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.elearning.enroll.students.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_course_id': self.id,
            },
        }
