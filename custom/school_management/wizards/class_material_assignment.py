from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SchoolClassMaterialAssignmentWizard(models.TransientModel):
    _name = 'school.class.material.assignment.wizard'
    _description = 'Assign Materials to Class Students'

    class_id = fields.Many2one('school.class', required=True, readonly=True)
    student_ids = fields.Many2many('school.student', string='Students', required=True)
    line_ids = fields.One2many('school.class.material.assignment.wizard.line', 'wizard_id', string='Books and Materials')
    student_count = fields.Integer(compute='_compute_student_count')
    reassignment_mode = fields.Boolean(
        string='Additional Material Assignment',
        default=lambda self: bool(self.env.context.get('school_material_reassignment')),
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        class_id = values.get('class_id') or self.env.context.get('active_id')
        if class_id and 'student_ids' in fields_list:
            students = self.env['school.class'].browse(class_id).student_ids.filtered(
                lambda student: student.active and student.study_status == 'studying'
            )
            values['student_ids'] = [(6, 0, students.ids)]
        return values

    @api.depends('student_ids')
    def _compute_student_count(self):
        for wizard in self:
            wizard.student_count = len(wizard.student_ids)

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            self.student_ids = self.class_id.student_ids.filtered(
                lambda student: student.active and student.study_status == 'studying'
            )
            return {'domain': {'student_ids': [('class_id', '=', self.class_id.id), ('study_status', '=', 'studying')]}}

    def _check_assignment_access(self):
        if self.env.user.has_group('school_management.group_school_admin'):
            return
        teacher = self.env['school.teacher'].search([('user_id', '=', self.env.user.id)], limit=1)
        assigned = teacher and (
            self.class_id.teacher_id == teacher
            or teacher in self.class_id.teaching_assignment_ids.mapped('teacher_id')
        )
        if not assigned:
            raise UserError(_('Only the class teacher or an assigned subject teacher can assign class materials.'))

    def action_assign_to_class(self):
        self.ensure_one()
        if self.class_id.enrollment_closed and not self.reassignment_mode:
            raise UserError(_('Enrollment is closed for this class. Reopen it before assigning additional materials.'))
        self._check_assignment_access()
        students = self.student_ids.filtered(lambda student: student.active and student.study_status == 'studying')
        if not students:
            raise UserError(_('Select at least one active studying student.'))
        if not self.line_ids:
            raise UserError(_('Add at least one book or material.'))
        student_subjects = students.mapped('study_subject_ids').filtered(
            lambda line: line.active and line.study_status == 'active'
        ).mapped('subject_id')
        subjects = self.class_id.subject_ids | student_subjects
        if not subjects:
            raise ValidationError(_('No active subjects are enrolled for this class or its selected students.'))
        request_line_values = []
        for line in self.line_ids:
            product = line.product_id.sudo()
            if line.subject_id not in subjects:
                raise ValidationError(_('Subject "%s" is not part of this class curriculum.') % line.subject_id.display_name)
            if not product.school_material:
                raise ValidationError(_('Product "%s" is not marked as a School Material.') % product.display_name)
            if line.subject_id not in product.school_subject_ids:
                raise ValidationError(_('Material "%s" is not linked to subject "%s".') % (product.display_name, line.subject_id.display_name))
            if line.quantity <= 0:
                raise ValidationError(_('Quantities must be greater than zero.'))
            request_line_values.append({
                'subject_id': line.subject_id.id,
                'product_id': line.product_id.id,
                'quantity': line.quantity,
            })
        students.sudo().action_sync_subjects_from_class()
        requests = self.env['school.material.request'].sudo().with_context(material_assignment=True)
        created = self.env['school.material.request']
        for student in students:
            active_subject_ids = set(student.study_subject_ids.filtered(
                lambda line: line.active and line.study_status == 'active'
            ).mapped('subject_id').ids)
            student_lines = [values for values in request_line_values if values['subject_id'] in active_subject_ids]
            if not student_lines:
                raise ValidationError(_(
                    'Student "%s" has no active subject matching the selected materials.'
                ) % student.display_name)
            created |= requests.create({
                'student_id': student.id,
                'requested_by': self.env.user.id,
                'state': 'approved',
                'line_ids': [(0, 0, values) for values in student_lines],
            })

        # Administrators can complete the stock assignment immediately when all
        # requested quantities are available. This creates the official outgoing
        # transfer, validates it, and creates the student's material holdings.
        # Requests without sufficient stock remain approved for the RFQ flow.
        pending_stock = self.env['school.material.request']
        if self.env.user.has_group('school_management.group_school_admin'):
            for request in created:
                try:
                    with self.env.cr.savepoint():
                        request.action_prepare_delivery()
                        result = request.stock_picking_id.with_context(
                            skip_sanity_check=True,
                            skip_backorder=True,
                        ).button_validate()
                        if isinstance(result, dict) and result.get('res_model'):
                            raise UserError(_('Inventory requires an additional operation for %s.') % request.name)
                        request.action_mark_delivered()
                except UserError:
                    pending_stock |= request
        return {
            'type': 'ir.actions.act_window',
            'name': _('Class Material Assignments - %s') % self.class_id.name,
            'res_model': 'school.material.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'context': {
                'school_material_assignment_pending_stock': pending_stock.ids,
            },
        }


class SchoolClassMaterialAssignmentWizardLine(models.TransientModel):
    _name = 'school.class.material.assignment.wizard.line'
    _description = 'Class Material Assignment Line'

    wizard_id = fields.Many2one('school.class.material.assignment.wizard', required=True, ondelete='cascade')
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
