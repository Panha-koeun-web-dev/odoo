from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ElearningEnrollStudentsWizard(models.TransientModel):
    _name = 'school.elearning.enroll.students.wizard'
    _description = 'Enroll Selected Students in an eLearning Course'

    course_id = fields.Many2one('slide.channel', string='eLearning Course', required=True, readonly=True)
    student_ids = fields.Many2many(
        'school.student', string='Students',
        domain="[('active', '=', True), ('study_status', '=', 'studying')]",
        required=True,
    )
    student_count = fields.Integer(compute='_compute_student_count')

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if self.env.context.get('active_id') and 'course_id' in fields_list:
            values['course_id'] = self.env.context['active_id']
        return values

    @api.depends('student_ids')
    def _compute_student_count(self):
        for wizard in self:
            wizard.student_count = len(wizard.student_ids)

    def action_enroll(self):
        self.ensure_one()
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('Only school administrators can enroll students in eLearning courses.'))
        students_without_users = self.student_ids.filtered(lambda student: not student.user_id.partner_id)
        if students_without_users:
            raise UserError(_(
                'These students do not have a linked login account: %s. '
                'Create their login account before enrolling them.'
            ) % ', '.join(students_without_users.mapped('name')))

        attendees = self.course_id.sudo()._action_add_members(
            self.student_ids.mapped('user_id.partner_id'),
            member_status='joined',
            raise_on_access=True,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Students Enrolled'),
                'message': _('%s student(s) enrolled in %s.') % (len(attendees), self.course_id.name),
                'type': 'success',
                'sticky': False,
            },
        }
