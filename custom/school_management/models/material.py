from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    school_material = fields.Boolean(
        string='School Material',
        help='Make this product available for student material requests.',
    )
    school_subject_ids = fields.Many2many(
        'school.subject',
        'school_material_subject_rel',
        'product_tmpl_id',
        'subject_id',
        string='School Subjects',
        help='Students may request this material only when they study one of these subjects.',
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    school_material = fields.Boolean(related='product_tmpl_id.school_material', readonly=True, store=True)
    school_subject_ids = fields.Many2many(
        related='product_tmpl_id.school_subject_ids',
        relation='school_material_product_subject_rel',
        column1='product_id',
        column2='subject_id',
        readonly=True,
        store=True,
    )


class SchoolMaterialRequest(models.Model):
    _name = 'school.material.request'
    _description = 'Student Material Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False, tracking=True)
    student_id = fields.Many2one('school.student', required=True, index=True, tracking=True)
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Confirmed'),
        ('purchasing', 'Purchasing'),
        ('ready', 'Ready for Delivery'),
        ('delivery', 'Delivery'),
        ('assigned', 'Done'),
        ('rejected', 'Rejected'),
    ], default='draft', required=True, tracking=True, copy=False)
    line_ids = fields.One2many('school.material.request.line', 'request_id', string='Materials', copy=True)
    stock_picking_id = fields.Many2one('stock.picking', string='Issue Transfer', readonly=True, copy=False)
    purchase_order_ids = fields.Many2many(
        'purchase.order',
        'school_material_request_purchase_rel',
        'request_id',
        'purchase_order_id',
        string='Official Purchase Orders',
        readonly=True,
        copy=False,
    )
    rejection_reason = fields.Text(copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True, readonly=True)

    @api.model
    def _default_student(self):
        return self.env['school.student'].search([('user_id', '=', self.env.user.id)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.has_group('school_management.group_school_student') and not self.env.user.has_group('school_management.group_school_admin'):
            student = self._default_student()
            if not student:
                raise UserError(_('Your user is not linked to a student profile.'))
            for vals in vals_list:
                vals['student_id'] = student.id
        records = super().create(vals_list)
        for record in records:
            if record.name == _('New'):
                record.name = self.env['ir.sequence'].next_by_code('school.material.request') or _('New')
            record._check_student_access()
        return records

    def write(self, vals):
        self._check_student_access()
        if any(record.state not in ('draft', 'submitted') for record in self) and not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('Only draft or submitted requests can be changed.'))
        return super().write(vals)

    def unlink(self):
        """Allow admins to remove requests that never entered the stock flow.

        Once a request has a purchase order, an issue transfer, or a student
        holding, it is part of the inventory audit trail.  Removing it would
        either leave orphaned purchasing/stock documents or break the holding
        history, so those records must be cancelled/returned instead.
        """
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('Only school administrators can delete material requests.'))

        holdings = self.env['school.material.holding'].sudo().search_count([
            ('request_id', 'in', self.ids),
        ])
        protected = self.filtered(
            lambda record: record.state in ('delivery', 'assigned')
            or record.stock_picking_id
            or record.purchase_order_ids
        )
        if protected or holdings:
            names = ', '.join(protected.mapped('name')) or _('the selected requests')
            raise UserError(_(
                'You cannot delete %(names)s because they already have '
                'purchase, delivery, or student-holding history. '
                'Cancel the request or return the materials instead.'
            ) % {'names': names})

        return super().unlink()

    def _check_student_access(self):
        if self.env.user.has_group('school_management.group_school_admin'):
            return
        if self.env.context.get('material_assignment') and self.env.user.has_group('school_management.group_school_teacher'):
            return
        student = self._default_student()
        if any(record.student_id != student for record in self):
            raise UserError(_('You can only access your own material requests.'))

    def _validate_lines(self):
        if not self.line_ids:
            raise UserError(_('Add at least one material before submitting the request.'))
        enrolled_subjects = self.student_id.study_subject_ids.filtered(
            lambda line: line.active and line.study_status == 'active'
        ).mapped('subject_id')
        for line in self.line_ids:
            # Product fields can trigger Manufacturing BoM computations in Odoo 19.
            # Validate through sudo so students do not need Manufacturing permissions.
            product = self.env['product.product'].sudo().browse(line.product_id.id)
            if not product.school_material:
                raise ValidationError(_('Product "%s" is not marked as a School Material.') % product.display_name)
            if line.subject_id not in enrolled_subjects:
                raise ValidationError(_('The student is not actively enrolled in subject "%s".') % line.subject_id.display_name)
            if line.subject_id not in product.school_subject_ids:
                raise ValidationError(_('Material "%s" is not linked to subject "%s".') % (product.display_name, line.subject_id.display_name))
            if line.quantity <= 0:
                raise ValidationError(_('Requested quantities must be greater than zero.'))

    def action_submit(self):
        for record in self:
            record._check_student_access()
            record._validate_lines()
            if record.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            record.state = 'submitted'
        return True

    def action_approve(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('Only a school administrator can approve requests.'))
        for record in self:
            record._validate_lines()
            if record.state != 'submitted':
                raise UserError(_('Only submitted requests can be approved.'))
            record.state = 'approved'
        return True

    def action_reject(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('Only a school administrator can reject requests.'))
        self.write({'state': 'rejected'})
        return True

    def _get_delivery_picking_type(self):
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not warehouse:
            raise UserError(_('Configure a warehouse before preparing delivery.'))
        picking_type = warehouse.out_type_id
        if not picking_type.default_location_src_id or not picking_type.default_location_dest_id:
            raise UserError(_('The warehouse outgoing operation has no source or destination location.'))
        return picking_type

    def _purchase_orders_received(self):
        self.ensure_one()
        active_orders = self.purchase_order_ids.filtered(lambda order: order.state != 'cancel')
        if not active_orders:
            return True
        return all(order.picking_ids and all(picking.state == 'done' for picking in order.picking_ids) for order in active_orders)

    def action_prepare_delivery(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('Only a school administrator can prepare deliveries.'))
        for record in self:
            if record.state not in ('approved', 'purchasing', 'ready'):
                raise UserError(_('Confirm the request and complete purchasing before preparing delivery.'))
            record._validate_lines()
            if not record._purchase_orders_received():
                raise UserError(_('Receive all official purchase orders before preparing delivery.'))
            picking_type = record._get_delivery_picking_type()
            source = picking_type.default_location_src_id
            destination = picking_type.default_location_dest_id
            for line in record.line_ids:
                available = line.product_id.with_context(location=source.id).free_qty
                if available < line.quantity:
                    raise UserError(_(
                        'Not enough stock for %(product)s. Required: %(required)s; available: %(available)s.'
                    ) % {'product': line.product_id.display_name, 'required': line.quantity, 'available': available})
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': source.id,
                'location_dest_id': destination.id,
                'partner_id': record.student_id.user_id.partner_id.id or False,
                'origin': record.name,
                'company_id': record.company_id.id,
            })
            for line in record.line_ids:
                self.env['stock.move'].create({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': source.id,
                    'location_dest_id': destination.id,
                    'company_id': record.company_id.id,
                })
            picking.action_confirm()
            picking.action_assign()
            if any(move.state != 'assigned' for move in picking.move_ids):
                raise UserError(_('The transfer could not reserve all requested materials.'))
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
            record.write({'stock_picking_id': picking.id, 'state': 'delivery'})
        return self.action_view_picking()

    def action_assign_material(self):
        """Backward-compatible button name for the delivery preparation action."""
        return self.action_prepare_delivery()

    def action_mark_delivered(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('Only a school administrator can complete deliveries.'))
        for record in self:
            if record.state != 'delivery' or not record.stock_picking_id:
                raise UserError(_('Prepare the delivery before completing this request.'))
            if record.stock_picking_id.state != 'done':
                raise UserError(_('Validate the outgoing delivery in Inventory before marking it Done.'))
            if record.line_ids and record.env['school.material.holding'].search_count([('request_id', '=', record.id)]):
                record.state = 'assigned'
                continue
            for line in record.line_ids:
                self.env['school.material.holding'].create({
                    'student_id': record.student_id.id,
                    'subject_id': line.subject_id.id,
                    'product_id': line.product_id.id,
                    'quantity_assigned': line.quantity,
                    'request_id': record.id,
                    'picking_id': record.stock_picking_id.id,
                })
            record.state = 'assigned'
        return True

    def action_create_purchase_order(self):
        """Create official Purchase RFQs for quantities missing from stock."""
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('Only a school administrator can create purchase orders.'))
        PurchaseOrder = self.env['purchase.order']
        for record in self:
            record._validate_lines()
            if record.state not in ('submitted', 'approved'):
                raise UserError(_('Submit the request before creating a purchase order.'))
            if record.purchase_order_ids.filtered(lambda order: order.state != 'cancel'):
                raise UserError(_('An official purchase order already exists for this request.'))
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', record.company_id.id)], limit=1)
            location = warehouse.lot_stock_id if warehouse else self.env['stock.location']
            shortages = []
            for line in record.line_ids:
                available = line.product_id.with_context(location=location.id).free_qty if location else 0.0
                shortage = max(0.0, line.quantity - available)
                if shortage:
                    seller = line.product_id._select_seller(
                        quantity=shortage,
                        date=fields.Date.today(),
                        uom_id=line.product_id.uom_id,
                    )
                    if not seller:
                        raise UserError(_('Configure a vendor on product "%s" first.') % line.product_id.display_name)
                    shortages.append((line, shortage, seller))
            if not shortages:
                raise UserError(_('There is enough stock for this request; no purchase order is required.'))
            orders_by_vendor = {}
            for line, shortage, seller in shortages:
                vendor = seller.partner_id
                order = orders_by_vendor.get(vendor.id)
                if not order:
                    order = PurchaseOrder.create({
                        'partner_id': vendor.id,
                        'origin': record.name,
                        'company_id': record.company_id.id,
                        'date_order': fields.Datetime.now(),
                    })
                    orders_by_vendor[vendor.id] = order
                self.env['purchase.order.line'].create({
                    'order_id': order.id,
                    'product_id': line.product_id.id,
                    'product_qty': shortage,
                    'product_uom_id': line.product_id.uom_id.id,
                    'date_planned': fields.Datetime.now(),
                    'price_unit': seller.price,
                })
            record.purchase_order_ids = [(6, 0, [order.id for order in orders_by_vendor.values()])]
            record.state = 'purchasing'
        return self.action_view_purchase_orders()

    def action_view_purchase_orders(self):
        self.ensure_one()
        if not self.purchase_order_ids:
            raise UserError(_('No official purchase order exists yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Official Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.purchase_order_ids.ids)],
        }

    def action_view_picking(self):
        self.ensure_one()
        if not self.stock_picking_id:
            raise UserError(_('No issue transfer exists yet.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.stock_picking_id.id,
        }


class SchoolMaterialRequestLine(models.Model):
    _name = 'school.material.request.line'
    _description = 'Student Material Request Line'

    request_id = fields.Many2one('school.material.request', required=True, ondelete='cascade')
    student_id = fields.Many2one(related='request_id.student_id', store=True, readonly=True)
    subject_id = fields.Many2one('school.subject', required=True)
    product_id = fields.Many2one('product.product', required=True, domain=[('school_material', '=', True)])
    quantity = fields.Float(default=1.0, required=True)
    available_qty = fields.Float(compute='_compute_available_qty', compute_sudo=True)
    shortage_qty = fields.Float(compute='_compute_available_qty', compute_sudo=True)

    @api.depends('product_id')
    def _compute_available_qty(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        location = warehouse.lot_stock_id if warehouse else self.env['stock.location']
        for line in self:
            # Read stock directly so the student form never evaluates mrp.bom through
            # product.free_qty when the Manufacturing app is installed.
            line.available_qty = (
                self.env['stock.quant'].sudo()._get_available_quantity(
                    line.product_id.sudo(), location,
                ) if location and line.product_id else 0
            )
            line.shortage_qty = max(0.0, line.quantity - line.available_qty)

    @api.onchange('request_id', 'subject_id')
    def _onchange_subject_id(self):
        if self.subject_id and self.product_id and self.subject_id not in self.product_id.school_subject_ids:
            self.product_id = False
        student = self.request_id.student_id
        enrolled = student.study_subject_ids.filtered(lambda line: line.active and line.study_status == 'active').mapped('subject_id') if student else self.env['school.subject']
        return {'domain': {'subject_id': [('id', 'in', enrolled.ids)], 'product_id': [('school_material', '=', True), ('school_subject_ids', 'in', self.subject_id.id)] if self.subject_id else [('school_material', '=', True)]}}

    @api.constrains('quantity')
    def _check_quantity(self):
        if any(line.quantity <= 0 for line in self):
            raise ValidationError(_('Quantity must be greater than zero.'))


class SchoolMaterialHolding(models.Model):
    _name = 'school.material.holding'
    _description = 'Material Currently Held by Student'
    _order = 'student_id, product_id, id'
    _rec_name = 'product_id'

    student_id = fields.Many2one('school.student', required=True, index=True, ondelete='restrict')
    subject_id = fields.Many2one('school.subject', required=True, index=True, ondelete='restrict')
    product_id = fields.Many2one('product.product', required=True, index=True, ondelete='restrict')
    quantity_assigned = fields.Float(string='Assigned Quantity', required=True)
    quantity_returned = fields.Float(string='Returned Quantity', default=0.0)
    quantity_held = fields.Float(string='Currently Held', compute='_compute_quantity_held', store=True)
    request_id = fields.Many2one('school.material.request', string='Student Request', required=True, readonly=True, ondelete='restrict')
    picking_id = fields.Many2one('stock.picking', string='Issue Transfer', required=True, readonly=True, ondelete='restrict')
    assigned_date = fields.Datetime(default=fields.Datetime.now, readonly=True)

    @api.depends('quantity_assigned', 'quantity_returned')
    def _compute_quantity_held(self):
        for record in self:
            record.quantity_held = max(0.0, record.quantity_assigned - record.quantity_returned)

    @api.constrains('quantity_assigned', 'quantity_returned')
    def _check_quantities(self):
        for record in self:
            if record.quantity_assigned <= 0:
                raise ValidationError(_('Assigned quantity must be greater than zero.'))
            if record.quantity_returned < 0 or record.quantity_returned > record.quantity_assigned:
                raise ValidationError(_('Returned quantity must be between zero and the assigned quantity.'))
