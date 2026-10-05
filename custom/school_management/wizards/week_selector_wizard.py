from datetime import timedelta, date
from odoo import models, fields, api, _
from odoo.exceptions import UserError

WEEK_SELECTION = [(str(w), f'Week {w}') for w in range(1, 54)]


class SchoolTimetableWeekSelectorWizard(models.TransientModel):
    _name = 'school.timetable.week.selector.wizard'
    _description = 'Select & View Specific Week Calendar Schedule'

    week_number = fields.Selection(
        WEEK_SELECTION,
        string='Select Academic / Calendar Week',
        required=True,
        default='41',
        help="Choose any specific week (Week 1 to Week 53) to auto-relate to term and view schedule."
    )

    term_id = fields.Many2one(
        'school.term',
        string='Academic Term',
        required=True,
        help="Academic term auto-related to the chosen week."
    )
    academic_year = fields.Char(related='term_id.academic_year', string='Academic Year', readonly=True)
    term_number = fields.Selection(related='term_id.term_number', string='Term Sequence', readonly=True)
    term_state = fields.Selection(related='term_id.state', string='Term Status', readonly=True)

    class_id = fields.Many2one(
        'school.class',
        string='Class Filter (Optional)',
        help="Filter schedule sessions to a specific class. If empty, shows all classes."
    )
    teacher_id = fields.Many2one(
        'school.teacher',
        string='Teacher Filter (Optional)',
        help="Filter schedule sessions to a specific teacher. If empty, shows all teachers."
    )

    view_mode = fields.Selection([
        ('calendar', 'Calendar View (Visual Weekly Grid)'),
        ('list', 'List / Table View'),
        ('kanban', 'Kanban Cards View'),
    ], string='Open In', default='calendar', required=True)

    week_date_info = fields.Char(
        string='Week Dates',
        compute='_compute_week_info',
    )
    session_count = fields.Integer(
        string='Scheduled Sessions',
        compute='_compute_week_info',
    )
    session_ids = fields.Many2many(
        'school.timetable',
        string='Weekly Schedule Sessions',
        compute='_compute_week_info',
        help="Timetable sessions scheduled in this specific week."
    )

    # -------------------------------------------------------------------------
    # TERM RESOLUTION HELPER
    # -------------------------------------------------------------------------
    def _find_term_for_week(self, w_num):
        """Find the matching Academic Term for a given week number (1..53)."""
        today = fields.Date.context_today(self)

        # 1. Check existing sessions in the database for this week
        existing = self.env['school.timetable'].search([
            ('week_number', '=', w_num),
            ('term_id', '!=', False)
        ], limit=1)
        if existing and existing.term_id:
            return existing.term_id

        # 2. Match by ISO calendar date
        active_term = self.env['school.term'].search([('state', '=', 'active')], limit=1)
        base_year = (active_term.date_start.year if (active_term and active_term.date_start) else today.year)
        target_year = base_year if w_num >= 30 else (base_year + 1)
        try:
            target_monday = date.fromisocalendar(target_year, w_num, 1)
            matching_term = self.env['school.term'].search([
                ('date_start', '<=', target_monday),
                ('date_end', '>=', target_monday),
            ], limit=1)
            if matching_term:
                return matching_term
        except Exception:
            pass

        # 3. Fallback: active term or latest term
        if active_term:
            return active_term
        return self.env['school.term'].search([], order='date_start desc', limit=1)

    # -------------------------------------------------------------------------
    # DEFAULTS & COMPUTATIONS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user = self.env.user
        today = fields.Date.context_today(self)
        iso_week = today.isocalendar()[1]

        # Default to current ISO week (e.g. 41)
        if not res.get('week_number'):
            res['week_number'] = str(iso_week)

        w_num = int(res['week_number'])
        auto_term = self._find_term_for_week(w_num)
        if auto_term and not res.get('term_id'):
            res['term_id'] = auto_term.id

        ctx_class = self.env.context.get('default_class_id')
        if ctx_class and not res.get('class_id'):
            res['class_id'] = ctx_class

        ctx_teacher = self.env.context.get('default_teacher_id')
        if ctx_teacher and not res.get('teacher_id'):
            res['teacher_id'] = ctx_teacher

        # Role-based defaults for Teacher and Student
        is_admin = user.has_group('school_management.group_school_admin')
        is_teacher = user.has_group('school_management.group_school_teacher')
        is_student = user.has_group('school_management.group_school_student')

        if is_teacher and not is_admin and not res.get('teacher_id'):
            teacher = self.env['school.teacher'].search([('user_id', '=', user.id)], limit=1)
            if teacher:
                res['teacher_id'] = teacher.id

        if is_student and not is_admin and not res.get('class_id'):
            student = self.env['school.student'].search([('user_id', '=', user.id)], limit=1)
            if student and student.class_id:
                res['class_id'] = student.class_id.id

        return res

    def _get_week_target_monday(self, w_num):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.term_id and self.term_id.date_start:
            target_year = self.term_id.date_start.year
            if self.term_id.date_end and self.term_id.date_end.year > target_year and w_num < 30:
                target_year = self.term_id.date_end.year
            try:
                return date.fromisocalendar(target_year, w_num, 1)
            except Exception:
                pass

        base_year = today.year if today.month >= 8 else (today.year - 1)
        target_year = base_year if w_num >= 30 else (base_year + 1)
        try:
            return date.fromisocalendar(target_year, w_num, 1)
        except Exception:
            monday_this_week = today - timedelta(days=today.weekday())
            return monday_this_week + timedelta(weeks=w_num - 1)

    # -------------------------------------------------------------------------
    # ONCHANGES (AUTO-RELATE TO TERM & VICE VERSA)
    # -------------------------------------------------------------------------
    @api.onchange('week_number')
    def _onchange_week_number(self):
        """Auto-relate to the corresponding Academic Term as soon as a week is chosen."""
        if self.week_number:
            w_num = int(self.week_number)
            matching_term = self._find_term_for_week(w_num)
            if matching_term and (not self.term_id or self.term_id != matching_term):
                self.term_id = matching_term

    @api.onchange('term_id')
    def _onchange_term_id(self):
        """When user manually switches Academic Term, align week_number to that Term."""
        if self.term_id and self.term_id.date_start:
            today = fields.Date.context_today(self)
            if self.term_id.date_start <= today <= (self.term_id.date_end or today):
                self.week_number = str(today.isocalendar()[1])
            else:
                self.week_number = str(self.term_id.date_start.isocalendar()[1])

    @api.depends('term_id', 'week_number', 'class_id', 'teacher_id')
    def _compute_week_info(self):
        Timetable = self.env['school.timetable']
        for rec in self:
            w_num = int(rec.week_number or '1')
            mon = rec._get_week_target_monday(w_num)
            fri = mon + timedelta(days=4)
            sun = mon + timedelta(days=6)
            term_label = f" ({rec.term_id.name})" if rec.term_id else ""
            rec.week_date_info = f"Week {w_num}: {mon.strftime('%d %b %Y')} to {fri.strftime('%d %b %Y')} (Monday – Friday){term_label}"

            mon_str = mon.strftime('%Y-%m-%d 00:00:00')
            sun_str = sun.strftime('%Y-%m-%d 23:59:59')

            domain = [
                ('active', '=', True),
                '|', '|',
                ('week_number', '=', w_num),
                ('iso_week_number', '=', w_num),
                '&', ('start_datetime', '>=', mon_str), ('start_datetime', '<=', sun_str),
            ]
            if rec.term_id:
                domain.append(('term_id', '=', rec.term_id.id))
            if rec.class_id:
                domain.append(('class_id', '=', rec.class_id.id))
            if rec.teacher_id:
                domain.append(('teacher_id', '=', rec.teacher_id.id))

            matched_sessions = Timetable.search(domain, order='day_of_week, start_time')
            rec.session_ids = [(6, 0, matched_sessions.ids)]
            rec.session_count = len(matched_sessions)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_auto_integrate_week_schedule(self):
        """1-Click: Auto-integrate & populate Monday-Friday schedule for this chosen week."""
        self.ensure_one()
        w_num = int(self.week_number or '41')
        target_class = self.class_id or self.env['school.class'].search([], limit=1)
        if not target_class:
            raise UserError(_("Please configure at least one Class in the system to integrate schedule."))

        target_term = self.term_id or self._find_term_for_week(w_num)
        if not target_term:
            raise UserError(_("No Academic Term found for Week %d.") % w_num)

        plan_wiz = self.env['school.term.schedule.wizard'].create({
            'term_id': target_term.id,
            'class_id': target_class.id,
            'mode': 'create_slots',
            'week_apply_mode': 'this_week',
            'target_week': str(w_num),
            'overwrite_existing': False,
        })
        plan_wiz.action_prefill_from_class_curriculum()
        plan_wiz.action_apply_schedule()

        self._compute_week_info()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }

    def action_view_week_schedule(self):
        """Open Timetable centered on selected week."""
        self.ensure_one()
        w_num = int(self.week_number or '1')
        target_monday = self._get_week_target_monday(w_num)
        target_sunday = target_monday + timedelta(days=6)
        mon_str = target_monday.strftime('%Y-%m-%d 00:00:00')
        sun_str = target_sunday.strftime('%Y-%m-%d 23:59:59')

        ctx = {
            'search_default_filter_mon_fri': 1,
            'initial_date': target_monday.isoformat(),
        }
        if self.term_id:
            ctx['default_term_id'] = self.term_id.id
        if self.class_id:
            ctx['default_class_id'] = self.class_id.id
        if self.teacher_id:
            ctx['default_teacher_id'] = self.teacher_id.id

        domain = []
        if self.term_id:
            domain.append(('term_id', '=', self.term_id.id))
        if self.class_id:
            domain.append(('class_id', '=', self.class_id.id))
        if self.teacher_id:
            domain.append(('teacher_id', '=', self.teacher_id.id))

        if self.view_mode == 'calendar':
            ctx[f'search_default_filter_week_{w_num}'] = 1
        else:
            domain.extend([
                '|', '|',
                ('week_number', '=', w_num),
                ('iso_week_number', '=', w_num),
                '&', ('start_datetime', '>=', mon_str), ('start_datetime', '<=', sun_str),
            ])

        target_title = self.class_id.name or self.teacher_id.name or (self.term_id.name if self.term_id else '')
        title_prefix = f" - {target_title}" if target_title else ""
        action_name = _("Timetable: Week %(w)d (%(dates)s)%(target)s") % {
            'w': w_num,
            'dates': target_monday.strftime('%d %b %Y'),
            'target': title_prefix,
        }

        mode_order = {
            'calendar': 'calendar,kanban,list,form',
            'list': 'list,calendar,kanban,form',
            'kanban': 'kanban,calendar,list,form',
        }.get(self.view_mode, 'calendar,kanban,list,form')

        return {
            'name': action_name,
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': mode_order,
            'domain': domain,
            'context': ctx,
        }

    def action_plan_for_this_week(self):
        """Convenient shortcut: open Schedule Planning Wizard prefilled with this specific week."""
        self.ensure_one()
        w_num = self.week_number or '41'
        return {
            'name': _('Plan Schedule for Week %s') % w_num,
            'type': 'ir.actions.act_window',
            'res_model': 'school.term.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_term_id': self.term_id.id if self.term_id else False,
                'default_class_id': self.class_id.id if self.class_id else False,
                'default_target_week': w_num,
                'default_week_apply_mode': 'this_week',
            },
        }
