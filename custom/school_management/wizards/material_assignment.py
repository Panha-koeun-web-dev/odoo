from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SchoolMaterialAssignmentWizard(models.TransientModel):
    _name = 'school.material.assignment.wizard'
    _description = 'Assign Books and Materials to Student'

    student_id = fields.Many2one('school.student', required=True, readonly=True)
    line_ids = fields.One2many('school.material.assignment.wizard.line', 'wizard_id', string='Books and Materials')
    note = fields.Text(string='Assignment Note')

    def _enrolled_subjects(self):
        self.ensure_one()
        if not self.student_id:
            return self.env['school.subject']
        return self.student_id.study_subject_ids.filtered(
            lambda line: line.active and line.study_status == 'active'
        ).mapped('subject_id')

    def _check_teacher_student_access(self):
        if self.env.user.has_group('school_management.group_school_admin'):
            return
        if not self.env.user.has_group('school_management.group_school_teacher'):
            raise UserError(_('Only administrators and teachers can assign materials.'))
        teacher = self.env['school.teacher'].search([('user_id', '=', self.env.user.id)], limit=1)
        student = self.student_id
        assigned = (
            student.class_id.teacher_id == teacher
            or teacher in student.class_id.teaching_assignment_ids.mapped('teacher_id')
            or teacher in student.study_subject_ids.mapped('teacher_id')
        ) if teacher else False
        if not assigned:
            raise UserError(_('You can assign materials only to students assigned to you.'))

    def action_create_assignment(self):
        self.ensure_one()
        self._check_teacher_student_access()
        if not self.line_ids:
            raise UserError(_('Add at least one book or material.'))
        enrolled = self._enrolled_subjects()
        request_lines = []
        for line in self.line_ids:
            product = line.product_id.sudo()
            if line.subject_id not in enrolled:
                raise ValidationError(_('The student is not actively enrolled in subject "%s".') % line.subject_id.display_name)
            if not product.school_material:
                raise ValidationError(_('Product "%s" is not marked as a School Material.') % product.display_name)
            if line.subject_id not in product.school_subject_ids:
                raise ValidationError(_('Material "%s" is not linked to subject "%s".') % (product.display_name, line.subject_id.display_name))
            if line.quantity <= 0:
                raise ValidationError(_('Quantities must be greater than zero.'))
            request_lines.append((0, 0, {
                'subject_id': line.subject_id.id,
                'product_id': line.product_id.id,
                'quantity': line.quantity,
            }))
        request = self.env['school.material.request'].sudo().with_context(material_assignment=True).create({
            'student_id': self.student_id.id,
            'requested_by': self.env.user.id,
            'state': 'approved',
            'line_ids': request_lines,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Assignment %s') % request.name,
            'res_model': 'school.material.request',
            'view_mode': 'form',
            'res_id': request.id,
            'target': 'current',
        }


class SchoolMaterialAssignmentWizardLine(models.TransientModel):
    _name = 'school.material.assignment.wizard.line'
    _description = 'Material Assignment Line'

    wizard_id = fields.Many2one('school.material.assignment.wizard', required=True, ondelete='cascade')
    subject_id = fields.Many2one('school.subject', required=True)
    product_id = fields.Many2one('product.product', required=True, domain=[('school_material', '=', True)])
    quantity = fields.Float(default=1.0, required=True)

    @api.onchange('subject_id')
    def _onchange_subject_id(self):
        if self.product_id and self.subject_id not in self.product_id.school_subject_ids:
            self.product_id = False
        return {'domain': {'product_id': [
            ('school_material', '=', True),
            ('school_subject_ids', 'in', self.subject_id.id),
        ] if self.subject_id else [('school_material', '=', True)]}}

    @api.constrains('quantity')
    def _check_quantity(self):
        if any(line.quantity <= 0 for line in self):
            raise ValidationError(_('Quantity must be greater than zero.'))
