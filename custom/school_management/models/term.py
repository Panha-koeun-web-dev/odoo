from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class SchoolTerm(models.Model):
    _name = 'school.term'
    _description = 'Academic Term (3 Months / Term, 3 Terms / Year)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'academic_year desc, term_number asc'

    name = fields.Char(
        string='Term Name',
        compute='_compute_name',
        store=True,
        readonly=False,
        tracking=True
    )
    academic_year = fields.Char(
        string='Academic Year',
        required=True,
        default=lambda self: self._default_academic_year(),
        tracking=True,
        help="Academic Year period, e.g. '2025-2026' or '2026-2027' (12 months total)."
    )
    term_number = fields.Selection([
        ('term_1', 'Term 1 (Months 1 - 3)'),
        ('term_2', 'Term 2 (Months 4 - 6)'),
        ('term_3', 'Term 3 (Months 7 - 9 / Final)'),
    ], string='Term Number', required=True, default='term_1', tracking=True)

    date_start = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        compute='_compute_date_end',
        store=True,
        precompute=True,
        readonly=False,
        tracking=True,
        help="Term end date. Automatically set to 3 months from start date by default."
    )

    duration_months = fields.Float(
        string='Duration (Months)',
        compute='_compute_duration',
        store=True,
        help="Calculated duration of this term in months."
    )
    duration_weeks = fields.Integer(
        string='Duration (Weeks)',
        compute='_compute_duration',
        store=True,
        help="Calculated duration of this term in weeks."
    )

    state = fields.Selection([
        ('draft', 'Upcoming / Draft'),
        ('active', 'Active (In Progress)'),
        ('finished', 'Finished / Completed'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)

    color = fields.Integer(string='Color Index', default=0)
    notes = fields.Html(string='Term Objectives & Syllabus Notes')

    # Sequential continuity
    previous_term_id = fields.Many2one(
        'school.term',
        string='Previous Term',
        help="Preceding term in sequence (e.g. Term 1 before Term 2)."
    )
    next_term_id = fields.Many2one(
        'school.term',
        string='Next Term',
        help="Succeeding term in sequence (e.g. Term 2 after Term 1)."
    )

    # Timetable relations
    timetable_ids = fields.One2many(
        'school.timetable',
        'term_id',
        string='Timetable Sessions'
    )
    timetable_count = fields.Integer(
        string='Sessions Count',
        compute='_compute_timetable_count',
        store=True
    )

    # Classes in this term
    class_ids = fields.Many2many(
        'school.class',
        'school_class_term_rel',
        'term_id',
        'class_id',
        string='Classes Enrolled'
    )
    class_count = fields.Integer(
        string='Classes Count',
        compute='_compute_class_count',
        store=True
    )

    # Exams in this term
    exam_ids = fields.One2many(
        'school.exam',
        'term_id',
        string='Term Exams'
    )
    exam_count = fields.Integer(
        string='Exams Count',
        compute='_compute_exam_count'
    )

    _unique_year_term = models.Constraint(
        'unique(academic_year, term_number)',
        'An academic term with this term number already exists for this academic year!',
    )

    @api.model
    def _load_records(self, data_list, update=False):
        """Pre-emptively bind existing school.term records to external IDs during XML import/upgrade.

        If a term record with the same (academic_year, term_number) already exists in the database,
        make sure ir.model.data points to it so Odoo reuses it rather than throwing a duplicate error.
        """
        imd = self.env['ir.model.data'].sudo()
        for data in data_list:
            xml_id = data.get('xml_id')
            values = data.get('values') or {}
            acad_year = values.get('academic_year')
            term_num = values.get('term_number')
            if xml_id and acad_year and term_num:
                module, sep, name = xml_id.partition('.')
                if sep:
                    existing_term = self.sudo().search([
                        ('academic_year', '=', acad_year),
                        ('term_number', '=', term_num),
                    ], limit=1)
                    if existing_term:
                        existing_xml = imd.search([('module', '=', module), ('name', '=', name)], limit=1)
                        if existing_xml:
                            if existing_xml.res_id != existing_term.id or existing_xml.model != self._name:
                                existing_xml.write({'res_id': existing_term.id, 'model': self._name})
                        else:
                            imd.create({
                                'name': name,
                                'module': module,
                                'model': self._name,
                                'res_id': existing_term.id,
                                'noupdate': bool(data.get('noupdate', True)),
                            })
        return super()._load_records(data_list, update=update)

    @api.model
    def _load_records_create(self, vals_list):
        """Prevent UniqueViolation during XML data loading.

        If a term with (academic_year, term_number) already exists in the database,
        reuse/update it instead of calling create() which violates PostgreSQL unique constraints.
        """
        records = self.browse()
        for vals in vals_list:
            acad_year = vals.get('academic_year')
            term_num = vals.get('term_number')
            existing = False
            if acad_year and term_num:
                existing = self.search([
                    ('academic_year', '=', acad_year),
                    ('term_number', '=', term_num),
                ], limit=1)
            if existing:
                write_vals = {k: v for k, v in vals.items() if k not in ('academic_year', 'term_number')}
                if write_vals:
                    existing.write(write_vals)
                records |= existing
            else:
                records |= super()._load_records_create([vals])
        return records

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('date_start') and not vals.get('date_end'):
                d_start = fields.Date.from_string(vals['date_start']) if isinstance(vals['date_start'], str) else vals['date_start']
                vals['date_end'] = d_start + relativedelta(months=3, days=-1)
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # DEFAULTS & COMPUTES
    # -------------------------------------------------------------------------
    @api.model
    def _default_academic_year(self):
        today = fields.Date.context_today(self)
        current_year = today.year
        # If past July, academic year is current-next, else prev-current
        if today.month >= 8:
            return f"{current_year}-{current_year + 1}"
        return f"{current_year - 1}-{current_year}"

    @api.depends('academic_year', 'term_number')
    def _compute_name(self):
        term_labels = dict(self._fields['term_number'].selection)
        for record in self:
            label = term_labels.get(record.term_number, record.term_number or '')
            year = record.academic_year or ''
            record.name = f"{year} - {label}" if year and label else (label or year or _("Academic Term"))

    @api.depends('date_start')
    def _compute_date_end(self):
        for record in self:
            if record.date_start and not record.date_end:
                # 1 term = 3 months
                record.date_end = record.date_start + relativedelta(months=3, days=-1)

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = relativedelta(record.date_end + timedelta(days=1), record.date_start)
                months = delta.years * 12 + delta.months + (delta.days / 30.0)
                record.duration_months = round(months, 1)
                days_diff = (record.date_end - record.date_start).days + 1
                record.duration_weeks = max(1, days_diff // 7)
            else:
                record.duration_months = 3.0
                record.duration_weeks = 12

    @api.depends('timetable_ids')
    def _compute_timetable_count(self):
        for record in self:
            record.timetable_count = len(record.timetable_ids)

    @api.depends('class_ids')
    def _compute_class_count(self):
        for record in self:
            record.class_count = len(record.class_ids)

    def _compute_exam_count(self):
        for record in self:
            record.exam_count = len(record.exam_ids)

    # -------------------------------------------------------------------------
    # CONSTRAINTS & VALIDATIONS
    # -------------------------------------------------------------------------
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError(_("Term Start Date must be before or equal to End Date!"))

    # -------------------------------------------------------------------------
    # BUSINESS WORKFLOW & ACTIONS
    # -------------------------------------------------------------------------
    def action_start_term(self):
        """Activate the term as the currently running academic term."""
        self.ensure_one()
        self.write({'state': 'active'})
        # Also update linked classes current_term_id if not set
        for cls in self.class_ids:
            if not cls.current_term_id or cls.current_term_id.state == 'finished':
                cls.current_term_id = self.id
        self.message_post(
            body=_("Academic Term <b>%s</b> is now active and in progress.") % self.name,
            subtype_xmlid="mail.mt_note",
        )
        return True

    def action_finish_term(self):
        """Mark this term as finished and prompt creation of next term."""
        self.ensure_one()
        self.write({'state': 'finished'})
        self.message_post(
            body=_("Academic Term <b>%s</b> has finished! You can now create or activate the schedule for the next term.") % self.name,
            subtype_xmlid="mail.mt_note",
        )
        # Automatically offer action to prepare/create next term
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Term Finished"),
                'message': _("Term '%s' is completed. Click 'Create / Prepare Next Term' to set up the upcoming term schedule.") % self.name,
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'school.term',
                    'res_id': self.id,
                    'views': [(False, 'form')],
                    'view_mode': 'form',
                    'target': 'current',
                }
            }
        }

    def action_create_next_term(self):
        """Create or navigate to the succeeding 3-month term in sequence."""
        self.ensure_one()
        # If next term already recorded, open it directly
        if self.next_term_id:
            return {
                'name': _('Academic Term - %s') % self.next_term_id.name,
                'type': 'ir.actions.act_window',
                'res_model': 'school.term',
                'res_id': self.next_term_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # Calculate next term sequence:
        # Term 1 -> Term 2 (same year)
        # Term 2 -> Term 3 (same year)
        # Term 3 -> Term 1 (next academic year)
        next_year = self.academic_year
        if self.term_number == 'term_1':
            next_term_num = 'term_2'
        elif self.term_number == 'term_2':
            next_term_num = 'term_3'
        else:
            next_term_num = 'term_1'
            # Roll academic year e.g. 2025-2026 -> 2026-2027
            parts = (self.academic_year or '').split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                y1 = int(parts[0]) + 1
                y2 = int(parts[1]) + 1
                next_year = f"{y1}-{y2}"
            else:
                next_year = f"{fields.Date.today().year}-{fields.Date.today().year + 1}"

        # Start date begins the day after this term ends
        next_start = (self.date_end + timedelta(days=1)) if self.date_end else fields.Date.context_today(self)
        next_end = next_start + relativedelta(months=3, days=-1)

        # Check if matching term already exists
        existing = self.search([
            ('academic_year', '=', next_year),
            ('term_number', '=', next_term_num),
        ], limit=1)

        if existing:
            new_term = existing
        else:
            new_term = self.create({
                'academic_year': next_year,
                'term_number': next_term_num,
                'date_start': next_start,
                'date_end': next_end,
                'previous_term_id': self.id,
                'class_ids': [(6, 0, self.class_ids.ids)],
                'state': 'draft',
            })

        self.next_term_id = new_term.id
        if not new_term.previous_term_id:
            new_term.previous_term_id = self.id

        # Return action to open the new term
        return {
            'name': _('Academic Term - %s') % new_term.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.term',
            'res_id': new_term.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reset_draft(self):
        """Reset term back to draft."""
        self.ensure_one()
        self.write({'state': 'draft'})
        return True

    def action_open_schedule_wizard(self):
        """Open schedule planner wizard for this term."""
        self.ensure_one()
        first_class = self.class_ids[:1]
        return {
            'name': _('Create / Manage Schedule - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.term.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_term_id': self.id,
                'default_class_id': first_class.id if first_class else False,
                'default_source_term_id': self.previous_term_id.id if self.previous_term_id else False,
            }
        }

    def action_view_timetable(self):
        """View all timetable sessions for this term."""
        self.ensure_one()
        ctx = {
            'default_term_id': self.id,
            'search_default_group_class': 1,
            'search_default_filter_mon_fri': 1,
        }
        if self.date_start:
            ctx['initial_date'] = self.date_start.isoformat()
        return {
            'name': _('Term Timetable - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,kanban,list,form',
            'domain': [('term_id', '=', self.id)],
            'context': ctx,
        }

    def action_view_classes(self):
        """View classes enrolled in this term."""
        self.ensure_one()
        return {
            'name': _('Classes - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.class',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', self.class_ids.ids)],
            'context': {
                'default_current_term_id': self.id,
            }
        }
