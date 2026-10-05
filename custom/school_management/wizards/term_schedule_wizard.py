from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from ..models.timetable import DAY_SELECTION, PERIOD_SELECTION, PERIOD_PRESETS, START_TIME_SELECTION

WEEK_SELECTION = [
    ('1', 'Week 1'),
    ('2', 'Week 2'),
    ('3', 'Week 3'),
    ('4', 'Week 4'),
    ('5', 'Week 5'),
    ('6', 'Week 6'),
    ('7', 'Week 7'),
    ('8', 'Week 8'),
    ('9', 'Week 9'),
    ('10', 'Week 10'),
    ('11', 'Week 11'),
    ('12', 'Week 12'),
]


class SchoolTermScheduleWizard(models.TransientModel):
    _name = 'school.term.schedule.wizard'
    _description = 'Academic Term Schedule Creation & Rollover Wizard'

    term_id = fields.Many2one(
        'school.term',
        string='Academic Term',
        required=True,
        help="Select the academic term to create or roll over schedule for."
    )
    academic_year = fields.Char(related='term_id.academic_year', string='Academic Year', readonly=True)
    term_number = fields.Selection(related='term_id.term_number', string='Term Sequence', readonly=True)
    date_start = fields.Date(related='term_id.date_start', string='Term Start', readonly=True)
    date_end = fields.Date(related='term_id.date_end', string='Term End', readonly=True)
    term_state = fields.Selection(related='term_id.state', string='Term Status', readonly=True)

    class_id = fields.Many2one(
        'school.class',
        string='Target Class',
        required=True,
        help="The student class for which the schedule is being planned."
    )
    class_room = fields.Char(related='class_id.room', string='Class Default Room', readonly=True)

    mode = fields.Selection([
        ('create_slots', 'Plan Weekly Schedule (Monday - Friday)'),
        ('copy_term', 'Roll Over / Copy Schedule from Another Term'),
        ('quick_slot', 'Add Single Recurring Schedule Slot'),
    ], string='Scheduling Mode', default='create_slots', required=True)

    # Week Selection & Application Scope
    target_week = fields.Selection(
        WEEK_SELECTION,
        string='Selected Week',
        default='1',
        required=True,
        help="Select which week of the term you want to plan and assign."
    )
    week_apply_mode = fields.Selection([
        ('all_weeks', 'All Weeks of the Term (Week 1 to 12)'),
        ('this_week', 'Current Week Only'),
        ('selected_weeks', 'Select Specific Weeks...'),
    ], string='Apply Schedule To', default='all_weeks', required=True,
    help="Choose whether this schedule applies only to the selected week or is replicated across the full term.")

    schedule_scope = fields.Selection([
        ('full_term', 'All Weeks of the Term (Week 1 to 12)'),
        ('single_week', 'Current Week Only'),
        ('all_term_weeks', 'All Weeks of the Term'),
        ('specific_weeks', 'Select Specific Weeks...'),
    ], string='Schedule Scope (Legacy)', default='full_term')

    week_date_info = fields.Char(
        string='Selected Week Dates',
        compute='_compute_week_date_info',
    )

    # Multi-week selection flags
    apply_w1 = fields.Boolean('Week 1', default=True)
    apply_w2 = fields.Boolean('Week 2', default=True)
    apply_w3 = fields.Boolean('Week 3', default=True)
    apply_w4 = fields.Boolean('Week 4', default=True)
    apply_w5 = fields.Boolean('Week 5', default=True)
    apply_w6 = fields.Boolean('Week 6', default=True)
    apply_w7 = fields.Boolean('Week 7', default=True)
    apply_w8 = fields.Boolean('Week 8', default=True)
    apply_w9 = fields.Boolean('Week 9', default=True)
    apply_w10 = fields.Boolean('Week 10', default=True)
    apply_w11 = fields.Boolean('Week 11', default=True)
    apply_w12 = fields.Boolean('Week 12', default=True)

    # Rollover Options
    source_term_id = fields.Many2one(
        'school.term',
        string='Source Term to Copy From',
        help="Term whose schedule will be copied into this term."
    )
    source_session_count = fields.Integer(
        string='Available Source Sessions',
        compute='_compute_source_session_count'
    )
    activate_target_term = fields.Boolean(
        string='Activate Term Immediately',
        default=True,
        help="If checked, the target term will be marked as Active / In Progress upon creation."
    )
    overwrite_existing = fields.Boolean(
        string='Replace / Overwrite Existing Sessions',
        default=True,
        help="If checked, replaces previous timetable sessions for this class and target week(s)."
    )

    # Monday - Friday Generator Settings
    mon_fri_periods = fields.Selection([
        ('4_morning', 'Morning: 4 Periods (08:00 - 12:25)'),
        ('6_fullday', 'Full Day: 6 Periods (08:00 - 15:30)'),
        ('2_morning', 'Short Morning: 2 Periods (08:00 - 10:15)'),
    ], string='Daily Periods Preset', default='4_morning')

    include_mon = fields.Boolean(string='Monday', default=True)
    include_tue = fields.Boolean(string='Tuesday', default=True)
    include_wed = fields.Boolean(string='Wednesday', default=True)
    include_thu = fields.Boolean(string='Thursday', default=True)
    include_fri = fields.Boolean(string='Friday', default=True)

    distribute_subjects = fields.Boolean(
        string='Auto-distribute Class Curriculum (Subjects & Teachers)',
        default=True,
        help="If checked, automatically spreads teaching assignments and curriculum across the Monday - Friday grid."
    )

    # Holiday Quick Planning
    holiday_day = fields.Selection(
        DAY_SELECTION,
        string='Holiday Day of Week',
        default='2',
        help="Select a weekday to declare as Holiday (No Study Day)."
    )
    holiday_reason_input = fields.Char(
        string='Holiday Name / Reason',
        default='National Holiday',
        help="e.g. Water Festival, Khmer New Year, Public Holiday, Teacher Day, School Break"
    )

    # Batch slots creation
    line_ids = fields.One2many(
        'school.term.schedule.wizard.line',
        'wizard_id',
        string='Term Schedule Sessions'
    )

    # Single recurring slot
    single_subject_id = fields.Many2one('school.subject', string='Subject')
    single_teacher_id = fields.Many2one('school.teacher', string='Teacher')
    single_day_of_week = fields.Selection(DAY_SELECTION, string='Day of Week', default='0')
    single_period = fields.Selection(PERIOD_SELECTION, string='Period Preset', default='p1')
    single_specific_start_time = fields.Selection(
        START_TIME_SELECTION,
        string='Specific Start Hour',
        help="Quickly set a specific start time from 12 AM to 11 PM"
    )
    single_start_time = fields.Float(string='Start Time', default=8.0)
    single_end_time = fields.Float(string='End Time', default=9.0)
    single_room = fields.Char(string='Room / Location')
    single_notes = fields.Char(string='Session Notes')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'schedule_scope' in vals and 'week_apply_mode' not in vals:
                if vals['schedule_scope'] == 'single_week':
                    vals['week_apply_mode'] = 'this_week'
                elif vals['schedule_scope'] in ('full_term', 'all_term_weeks'):
                    vals['week_apply_mode'] = 'all_weeks'
                elif vals['schedule_scope'] == 'specific_weeks':
                    vals['week_apply_mode'] = 'selected_weeks'
        return super().create(vals_list)

    @api.model
    def _build_empty_mon_fri_lines(self, class_id=None, period_keys=None):
        """Construct standard Monday to Friday period slots so users never have to add them one by one."""
        if period_keys is None:
            period_keys = ['p1', 'p2', 'p3', 'p4']
        room = class_id.room if class_id and class_id.room else ''
        weekdays = [('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'), ('4', 'Friday')]
        lines = []
        for day_code, _label in weekdays:
            for p_key in period_keys:
                s_time, e_time = PERIOD_PRESETS.get(p_key, (8.0, 9.0))
                matched_s = next((k for k, _ in START_TIME_SELECTION if abs(s_time - float(k)) < 0.02), False)
                lines.append((0, 0, {
                    'day_of_week': day_code,
                    'period': p_key,
                    'specific_start_time': matched_s,
                    'start_time': s_time,
                    'end_time': e_time,
                    'subject_id': False,
                    'teacher_id': False,
                    'room': room,
                    'notes': '',
                }))
        return lines

    @api.depends('term_id', 'target_week', 'week_apply_mode')
    def _compute_week_date_info(self):
        for rec in self:
            if not rec.term_id:
                rec.week_date_info = ''
                continue
            term_start = rec.term_id.date_start or fields.Date.context_today(rec)
            first_monday = term_start - timedelta(days=term_start.weekday())
            w_num = int(rec.target_week or '1')
            w_monday = first_monday + timedelta(weeks=w_num - 1)
            w_friday = w_monday + timedelta(days=4)
            mon_str = w_monday.strftime('%d %b %Y')
            fri_str = w_friday.strftime('%d %b %Y')
            if rec.week_apply_mode == 'all_weeks':
                total_w = rec.term_id.duration_weeks or 12
                last_fri = first_monday + timedelta(weeks=total_w - 1, days=4)
                rec.week_date_info = f"All {total_w} Weeks ({mon_str} to {last_fri.strftime('%d %b %Y')}) — Monday to Friday"
            else:
                rec.week_date_info = f"Week {w_num}: {mon_str} to {fri_str} (Monday to Friday)"

    @api.depends('source_term_id', 'class_id')
    def _compute_source_session_count(self):
        Timetable = self.env['school.timetable']
        for rec in self:
            if rec.source_term_id and rec.class_id:
                rec.source_session_count = Timetable.search_count([
                    ('term_id', '=', rec.source_term_id.id),
                    ('class_id', '=', rec.class_id.id),
                    ('active', '=', True),
                ])
            elif rec.source_term_id:
                rec.source_session_count = Timetable.search_count([
                    ('term_id', '=', rec.source_term_id.id),
                    ('active', '=', True),
                ])
            else:
                rec.source_session_count = 0

    # -------------------------------------------------------------------------
    # DEFAULTS & ONCHANGES
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get('term_id'):
            active_term = self.env['school.term'].search([('state', '=', 'active')], limit=1)
            if not active_term:
                active_term = self.env['school.term'].search([('state', '=', 'draft')], order='date_start asc', limit=1)
            if active_term:
                res['term_id'] = active_term.id
                if active_term.previous_term_id:
                    res['source_term_id'] = active_term.previous_term_id.id

        if not res.get('class_id'):
            first_class = self.env['school.class'].search([], limit=1)
            if first_class:
                res['class_id'] = first_class.id
                if first_class.room:
                    res['single_room'] = first_class.room

        # Pre-populate Monday to Friday slots right away!
        if res.get('class_id') and not res.get('line_ids'):
            cls = self.env['school.class'].browse(res['class_id'])
            term_id = res.get('term_id')
            if term_id:
                w1_existing = self.env['school.timetable'].search([
                    ('term_id', '=', term_id),
                    ('class_id', '=', cls.id),
                    ('week_number', '=', 1),
                    ('active', '=', True),
                ], order='day_of_week, start_time')
                if w1_existing:
                    lines = []
                    for s in w1_existing:
                        lines.append((0, 0, {
                            'day_of_week': s.day_of_week,
                            'period': s.period,
                            'specific_start_time': s.specific_start_time,
                            'start_time': s.start_time,
                            'end_time': s.end_time,
                            'subject_id': s.subject_id.id if s.subject_id else False,
                            'teacher_id': s.teacher_id.id if s.teacher_id else False,
                            'room': s.room or cls.room or '',
                            'notes': s.notes or '',
                        }))
                    res['line_ids'] = lines

            if not res.get('line_ids'):
                res['line_ids'] = self._build_empty_mon_fri_lines(cls)

        return res

    @api.onchange('term_id')
    def _onchange_term_id(self):
        if self.term_id:
            if self.term_id.previous_term_id:
                self.source_term_id = self.term_id.previous_term_id
            else:
                prev = self.env['school.term'].search([
                    ('id', '!=', self.term_id.id),
                    ('date_end', '<=', self.term_id.date_start),
                ], order='date_end desc', limit=1)
                if prev:
                    self.source_term_id = prev

    @api.onchange('source_term_id')
    def _onchange_source_term(self):
        self._compute_source_session_count()

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            if self.class_id.room and not self.single_room:
                self.single_room = self.class_id.room
            if self.class_id.teacher_id and not self.single_teacher_id:
                self.single_teacher_id = self.class_id.teacher_id
            self._load_or_build_week_schedule()

    @api.onchange('target_week')
    def _onchange_target_week(self):
        self._load_or_build_week_schedule()

    def _load_or_build_week_schedule(self):
        """Helper to load existing schedule for the selected week or build a clean Monday-Friday grid."""
        if not self.class_id or not self.term_id:
            return
        w_num = int(self.target_week or '1')
        existing = self.env['school.timetable'].search([
            ('term_id', '=', self.term_id.id),
            ('class_id', '=', self.class_id.id),
            ('week_number', '=', w_num),
            ('active', '=', True),
        ], order='day_of_week, start_time')
        if existing:
            lines = []
            for s in existing:
                lines.append((0, 0, {
                    'day_of_week': s.day_of_week,
                    'period': s.period,
                    'specific_start_time': s.specific_start_time,
                    'start_time': s.start_time,
                    'end_time': s.end_time,
                    'subject_id': s.subject_id.id if s.subject_id else False,
                    'teacher_id': s.teacher_id.id if s.teacher_id else False,
                    'room': s.room or self.class_id.room or '',
                    'notes': s.notes or '',
                }))
            self.line_ids = [(5, 0, 0)] + lines
        else:
            self.line_ids = [(5, 0, 0)] + self._build_empty_mon_fri_lines(self.class_id)

    @api.onchange('single_period')
    def _onchange_single_period(self):
        if self.single_period in PERIOD_PRESETS:
            s_time, e_time = PERIOD_PRESETS[self.single_period]
            self.single_start_time = s_time
            self.single_end_time = e_time
            matched = False
            for k, _ in START_TIME_SELECTION:
                if abs(s_time - float(k)) < 0.02:
                    matched = k
                    break
            self.single_specific_start_time = matched

    @api.onchange('single_specific_start_time')
    def _onchange_single_specific_start_time(self):
        if self.single_specific_start_time:
            val = float(self.single_specific_start_time)
            dur = (self.single_end_time - self.single_start_time) if (self.single_end_time and self.single_end_time > self.single_start_time) else 1.0
            self.single_start_time = val
            self.end_time = min(24.0, round(val + dur, 2))
            matched_p = 'custom'
            for p_key, (ps, pe) in PERIOD_PRESETS.items():
                if abs(self.single_start_time - ps) < 0.02 and abs(self.single_end_time - pe) < 0.02:
                    matched_p = p_key
                    break
            self.single_period = matched_p

    @api.onchange('single_start_time', 'single_end_time')
    def _onchange_single_start_end_time(self):
        if self.single_start_time is not None:
            matched = False
            for k, _ in START_TIME_SELECTION:
                if abs(self.single_start_time - float(k)) < 0.02:
                    matched = k
                    break
            self.single_specific_start_time = matched
        if self.single_start_time is not None and self.single_end_time is not None:
            matched_p = 'custom'
            for p_key, (ps, pe) in PERIOD_PRESETS.items():
                if abs(self.single_start_time - ps) < 0.02 and abs(self.single_end_time - pe) < 0.02:
                    matched_p = p_key
                    break
            self.single_period = matched_p

    def _reopen_wizard(self):
        """Helper to reload the wizard dialog so modified line_ids immediately refresh in the UI."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }

    # -------------------------------------------------------------------------
    # QUICK ACTIONS
    # -------------------------------------------------------------------------
    def _get_class_curriculum_pool(self):
        """Build pool of (subject_id, teacher_id) for the class with multi-level fallbacks."""
        self.ensure_one()
        if not self.class_id:
            return []

        # 1. Try class-specific teaching assignments
        assignments = self.env['school.teaching.assignment'].search([
            ('class_id', '=', self.class_id.id),
            ('active', '=', True),
        ], order='weekly_hours desc, id asc')

        pool = []
        for asg in assignments:
            slots_needed = max(1, int(round(asg.weekly_hours or 2.0)))
            for _slot_idx in range(slots_needed):
                pool.append((asg.subject_id.id, asg.teacher_id.id if asg.teacher_id else (self.class_id.teacher_id.id if self.class_id.teacher_id else False)))

        # 2. Fallback to subjects directly linked to class
        if not pool and self.class_id.subject_ids:
            for sub in self.class_id.subject_ids:
                t_id = sub.teacher_ids[0].id if sub.teacher_ids else (self.class_id.teacher_id.id if self.class_id.teacher_id else False)
                for _ in range(2):
                    pool.append((sub.id, t_id))

        # 3. Fallback to active subjects in the school
        if not pool:
            active_subjects = self.env['school.subject'].search([('active', '=', True)], limit=8)
            for sub in active_subjects:
                t_id = sub.teacher_ids[0].id if sub.teacher_ids else (self.class_id.teacher_id.id if self.class_id.teacher_id else False)
                for _ in range(2):
                    pool.append((sub.id, t_id))

        return pool

    def action_populate_empty_mon_fri(self):
        """Prepare Monday to Friday slots (20 rows) and auto-fill weekly schedule with subjects and teachers."""
        self.ensure_one()
        pool = self._get_class_curriculum_pool()
        pool_len = len(pool) if pool else 0
        empty_slots = self._build_empty_mon_fri_lines(self.class_id)

        # If lines already exist, update them in place to preserve their record IDs in the browser!
        if len(self.line_ids) == len(empty_slots):
            for idx, (_, _, vals) in enumerate(empty_slots):
                if pool:
                    sub_id, tch_id = pool[idx % pool_len]
                    vals['subject_id'] = sub_id
                    vals['teacher_id'] = tch_id or (self.class_id.teacher_id.id if self.class_id.teacher_id else False)
                self.line_ids[idx].write(vals)
        else:
            built_lines = []
            for idx, (_, _, vals) in enumerate(empty_slots):
                if pool:
                    sub_id, tch_id = pool[idx % pool_len]
                    vals['subject_id'] = sub_id
                    vals['teacher_id'] = tch_id or (self.class_id.teacher_id.id if self.class_id.teacher_id else False)
                built_lines.append((0, 0, vals))
            self.line_ids = [(5, 0, 0)] + built_lines
        return self._reopen_wizard()

    def action_clear_all_lines(self):
        """Remove all schedule lines."""
        self.ensure_one()
        self.line_ids.unlink()
        return self._reopen_wizard()

    def action_generate_monday_to_friday(self):
        """Generate Monday to Friday schedule grid and optionally distribute curriculum."""
        self.ensure_one()
        self.action_populate_empty_mon_fri()
        if self.distribute_subjects:
            self.action_prefill_from_class_curriculum()
        return self._reopen_wizard()

    def action_mark_day_as_holiday(self):
        """Mark all session lines on the selected day as Holiday / No Study."""
        self.ensure_one()
        if not self.holiday_day:
            raise UserError(_("Please select a weekday to mark as holiday."))
        target_lines = self.line_ids.filtered(lambda l: l.day_of_week == self.holiday_day)
        if not target_lines:
            raise UserError(_("No schedule lines found for the selected day."))
        reason = self.holiday_reason_input or _("School Holiday")
        
        # Keep 1 full-day holiday line spanning 07:30 to 17:00, unlinking redundant lines
        first_line = target_lines[0]
        first_line.write({
            'period': 'custom',
            'specific_start_time': False,
            'start_time': 7.5,
            'end_time': 17.0,
            'is_holiday': True,
            'holiday_name': reason,
            'subject_id': False,
            'teacher_id': False,
            'room': False,
            'notes': _("No Classes - %s") % reason,
        })
        other_lines = target_lines[1:]
        if other_lines:
            other_lines.unlink()

        return self._reopen_wizard()

    def action_unmark_day_holiday(self):
        """Restore holiday lines on selected day back to regular class slots."""
        self.ensure_one()
        if not self.holiday_day:
            raise UserError(_("Please select a weekday to unmark."))
        target_lines = self.line_ids.filtered(lambda l: l.day_of_week == self.holiday_day and l.is_holiday)
        if target_lines:
            target_lines.unlink()
        day_lines = []
        default_periods = [
            ('p1', 8.0, 9.0),
            ('p2', 9.25, 10.25),
            ('p3', 10.25, 11.25),
            ('p4', 11.25, 12.25),
        ]
        default_room = self.class_id.room if self.class_id else False
        for p_code, s_time, e_time in default_periods:
            matched_s = next((k for k, _ in START_TIME_SELECTION if abs(s_time - float(k)) < 0.02), False)
            day_lines.append((0, 0, {
                'day_of_week': self.holiday_day,
                'period': p_code,
                'specific_start_time': matched_s,
                'start_time': s_time,
                'end_time': e_time,
                'is_holiday': False,
                'holiday_name': False,
                'room': default_room,
            }))
        self.write({'line_ids': day_lines})
        return self._reopen_wizard()

    def action_copy_from_week_1(self):
        """Clone Week 1's schedule into the currently selected week with 1 click."""
        self.ensure_one()
        if not self.class_id or not self.term_id:
            raise UserError(_("Please select Class and Term first."))

        w1_sessions = self.env['school.timetable'].search([
            ('term_id', '=', self.term_id.id),
            ('class_id', '=', self.class_id.id),
            ('week_number', '=', 1),
            ('active', '=', True),
        ], order='day_of_week, start_time')

        if not w1_sessions:
            raise UserError(_("No saved timetable found for Week 1 yet. Please configure and save Week 1 first."))

        lines = []
        for s in w1_sessions:
            lines.append((0, 0, {
                'day_of_week': s.day_of_week,
                'period': s.period,
                'specific_start_time': s.specific_start_time,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'subject_id': s.subject_id.id if s.subject_id else False,
                'teacher_id': s.teacher_id.id if s.teacher_id else False,
                'room': s.room or self.class_id.room or '',
                'notes': s.notes or '',
            }))
        self.line_ids = [(5, 0, 0)] + lines
        return self._reopen_wizard()

    def action_copy_monday_to_all_weekdays(self):
        """Duplicate Monday's subjects and teachers across Tuesday, Wednesday, Thursday, Friday."""
        self.ensure_one()
        monday_lines = self.line_ids.filtered(lambda l: l.day_of_week == '0')
        if not monday_lines:
            raise UserError(_("No schedule configured on Monday to copy from."))

        new_lines = []
        for day_code in ['1', '2', '3', '4']:
            for m in monday_lines:
                new_lines.append((0, 0, {
                    'day_of_week': day_code,
                    'period': m.period,
                    'specific_start_time': m.specific_start_time,
                    'start_time': m.start_time,
                    'end_time': m.end_time,
                    'subject_id': m.subject_id.id if m.subject_id else False,
                    'teacher_id': m.teacher_id.id if m.teacher_id else False,
                    'room': m.room or '',
                    'notes': m.notes or '',
                }))

        # Keep Monday and replace others
        self.line_ids = [(6, 0, monday_lines.ids)] + new_lines
        return self._reopen_wizard()

    def action_prefill_from_class_curriculum(self):
        """Intelligently pre-populate the Monday - Friday grid using the Class's teaching assignments."""
        self.ensure_one()
        if not self.class_id:
            raise UserError(_("Please select a Class first."))

        pool = self._get_class_curriculum_pool()
        if not pool:
            raise UserError(_("No subjects or teaching assignments found for Class '%s'.") % self.class_id.name)

        if not self.line_ids:
            self.line_ids = [(5, 0, 0)] + self._build_empty_mon_fri_lines(self.class_id)

        pool_idx = 0
        pool_len = len(pool)
        for line in self.line_ids:
            if not line.is_holiday:
                sub_id, tch_id = pool[pool_idx % pool_len]
                line.write({
                    'subject_id': sub_id,
                    'teacher_id': tch_id or (self.class_id.teacher_id.id if self.class_id.teacher_id else False),
                    'room': self.class_id.room or '',
                })
                pool_idx += 1

        return self._reopen_wizard()

    def action_load_source_term_sessions(self):
        """Load timetable sessions from the selected source term into the lines grid."""
        self.ensure_one()
        if not self.source_term_id:
            raise UserError(_("Please select a Source Term to load."))
        if not self.class_id:
            raise UserError(_("Please select a Class first."))

        source_sessions = self.env['school.timetable'].search([
            ('term_id', '=', self.source_term_id.id),
            ('class_id', '=', self.class_id.id),
            ('active', '=', True),
        ], order='day_of_week, start_time')

        if not source_sessions:
            raise UserError(_("No active timetable sessions found in source term '%s' for class '%s'.") % (
                self.source_term_id.name, self.class_id.name
            ))

        lines = []
        for s in source_sessions:
            lines.append((0, 0, {
                'subject_id': s.subject_id.id if s.subject_id else False,
                'teacher_id': s.teacher_id.id if s.teacher_id else False,
                'day_of_week': s.day_of_week,
                'period': s.period,
                'specific_start_time': s.specific_start_time,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'room': s.room or self.class_id.room or '',
                'notes': s.notes or '',
            }))

        self.mode = 'create_slots'
        self.line_ids = [(5, 0, 0)] + lines
        return self._reopen_wizard()

    # -------------------------------------------------------------------------
    # MAIN APPLY ACTION
    # -------------------------------------------------------------------------
    def action_apply_schedule(self):
        self.ensure_one()
        if not self.term_id:
            raise UserError(_("Please select an Academic Term."))
        if not self.class_id:
            raise UserError(_("Please select a Class."))

        Timetable = self.env['school.timetable']

        # Determine target weeks
        target_weeks = []
        if self.week_apply_mode == 'this_week':
            target_weeks = [int(self.target_week)]
        elif self.week_apply_mode == 'all_weeks':
            total_weeks = self.term_id.duration_weeks or 12
            target_weeks = list(range(1, total_weeks + 1))
        elif self.week_apply_mode == 'selected_weeks':
            for w in range(1, 13):
                if getattr(self, f'apply_w{w}', False):
                    target_weeks.append(w)
            if not target_weeks:
                target_weeks = [int(self.target_week)]

        # Check existing sessions for this class, term, and target weeks
        if self.overwrite_existing:
            existing = Timetable.search([
                ('term_id', '=', self.term_id.id),
                ('class_id', '=', self.class_id.id),
            ])
            if existing:
                existing.unlink()

        term_start = self.term_id.date_start or fields.Date.context_today(self)
        first_monday = term_start - timedelta(days=term_start.weekday())

        target_name = self.class_id.name or ""
        target_students = [(6, 0, self.class_id.student_ids.ids)] if self.class_id.student_ids else False

        # Query all existing active holidays (school-wide or class-specific)
        existing_holidays = Timetable.search([
            ('is_holiday', '=', True),
            ('active', '=', True),
            '|', ('class_id', '=', False), ('class_id', '=', self.class_id.id),
        ])
        existing_holiday_dates = set()
        for h in existing_holidays:
            h_date = h._get_session_calendar_date()
            if h_date:
                existing_holiday_dates.add(h_date)

        vals_list = []

        # MODE 1: Roll over from source term
        if self.mode == 'copy_term':
            if not self.source_term_id:
                raise UserError(_("Please select a Source Term."))
            source_sessions = Timetable.search([
                ('term_id', '=', self.source_term_id.id),
                ('class_id', '=', self.class_id.id),
                ('active', '=', True),
            ])
            if not source_sessions:
                raise UserError(_("No active timetable sessions found in '%s'.") % self.source_term_id.name)

            seen_slots = set()
            for s in source_sessions:
                slot_key = (s.day_of_week, s.period, s.start_time, s.end_time, s.subject_id.id)
                if slot_key in seen_slots:
                    continue
                seen_slots.add(slot_key)
                sub_name = s.subject_id.name or ""
                custom_title = f"{s.notes} - {target_name}" if s.notes else (f"{sub_name} - {target_name}" if target_name else sub_name)

                for w_num in target_weeks:
                    week_monday = first_monday + timedelta(weeks=w_num - 1)
                    t_date = week_monday + timedelta(days=int(s.day_of_week))
                    if not s.is_holiday and t_date in existing_holiday_dates:
                        continue
                    s_dt = Timetable._local_to_utc(t_date, s.start_time)
                    e_dt = Timetable._local_to_utc(t_date, s.end_time)
                    vals_list.append({
                        'name': custom_title,
                        'term_id': self.term_id.id,
                        'class_id': self.class_id.id,
                        'week_number': w_num,
                        'is_holiday': s.is_holiday,
                        'holiday_name': s.holiday_name if s.is_holiday else False,
                        'teacher_id': s.teacher_id.id if not s.is_holiday else False,
                        'subject_id': s.subject_id.id if not s.is_holiday else False,
                        'subject_ids': ([(6, 0, s.subject_ids.ids)] if s.subject_ids else [(6, 0, [s.subject_id.id])]) if not s.is_holiday else False,
                        'student_ids': target_students,
                        'day_of_week': s.day_of_week,
                        'period': s.period,
                        'specific_start_time': s.specific_start_time,
                        'start_time': s.start_time,
                        'end_time': s.end_time,
                        'start_datetime': s_dt,
                        'end_datetime': e_dt,
                        'room': s.room or self.class_id.room,
                        'notes': s.notes,
                    })

        # MODE 2: Batch slots creation (Monday - Friday)
        elif self.mode == 'create_slots':
            # Check which weekdays in line_ids are marked as holidays
            holiday_days = set()
            for l in self.line_ids:
                if l.is_holiday:
                    holiday_days.add(l.day_of_week)

            # If a day is a holiday, regular class lines on that weekday are completely excluded!
            active_lines = self.line_ids.filtered(
                lambda l: l.is_holiday or (l.day_of_week not in holiday_days and bool(l.subject_id))
            )
            if not active_lines:
                raise UserError(_("Please configure at least one schedule line with a Subject or mark as Holiday."))

            # Intra-wizard validation: detect overlapping regular lines on the same day of week
            regular_lines = [l for l in active_lines if not l.is_holiday]
            for i in range(len(regular_lines)):
                for j in range(i + 1, len(regular_lines)):
                    l1, l2 = regular_lines[i], regular_lines[j]
                    if l1.day_of_week == l2.day_of_week:
                        if l1.start_time < l2.end_time and l1.end_time > l2.start_time:
                            d_name = dict(DAY_SELECTION).get(l1.day_of_week, l1.day_of_week)
                            s1_name = l1.subject_id.name or _('Subject 1')
                            s2_name = l2.subject_id.name or _('Subject 2')
                            if l1.subject_id == l2.subject_id:
                                raise ValidationError(_(
                                    "Duplicate Subject at Same Time!\n"
                                    "Subject '%(subject)s' is configured multiple times on %(day)s in overlapping time slots (%(t1)s and %(t2)s).\n"
                                    "A class cannot have the same subject scheduled concurrently at the same time."
                                ) % {
                                    'subject': s1_name,
                                    'day': d_name,
                                    't1': f"{l1.start_time:.2f}-{l1.end_time:.2f}",
                                    't2': f"{l2.start_time:.2f}-{l2.end_time:.2f}",
                                })
                            else:
                                raise ValidationError(_(
                                    "Overlapping Schedule Collision!\n"
                                    "On %(day)s, '%(s1)s' (%(t1)s) overlaps with '%(s2)s' (%(t2)s).\n"
                                    "A class cannot have two concurrent subjects at the same time."
                                ) % {
                                    'day': d_name,
                                    's1': s1_name,
                                    't1': f"{l1.start_time:.2f}-{l1.end_time:.2f}",
                                    't2': f"{l2.start_time:.2f}-{l2.end_time:.2f}",
                                })

            for idx, line in enumerate(active_lines, 1):
                day_name = dict(DAY_SELECTION).get(line.day_of_week, line.day_of_week)
                period_name = dict(PERIOD_SELECTION).get(line.period, line.period)
                if not line.is_holiday and not line.teacher_id:
                    raise UserError(_("Line %d (%s, %s): Please assign a Teacher for %s.") % (
                        idx, day_name, period_name, line.subject_id.name
                    ))

            holiday_created_weeks = set()  # (w_num, day_idx) to ensure only 1 holiday session per day

            for w_num in target_weeks:
                week_monday = first_monday + timedelta(weeks=w_num - 1)
                for line in active_lines:
                    day_idx = int(line.day_of_week)
                    target_date = week_monday + timedelta(days=day_idx)

                    # If this date already has an existing holiday (school-wide or class-specific),
                    # NEVER create regular classes on top of it!
                    if not line.is_holiday and target_date in existing_holiday_dates:
                        continue

                    if line.is_holiday:
                        if (w_num, day_idx) in holiday_created_weeks:
                            continue
                        holiday_created_weeks.add((w_num, day_idx))

                        h_title = line.holiday_name or _("School Holiday")
                        custom_title = f"Holiday: {h_title} - {target_name}".strip(' -')
                        s_dt = Timetable._local_to_utc(target_date, 7.5)
                        e_dt = Timetable._local_to_utc(target_date, 17.0)
                        vals_list.append({
                            'name': custom_title,
                            'term_id': self.term_id.id,
                            'class_id': self.class_id.id,
                            'week_number': w_num,
                            'is_holiday': True,
                            'holiday_name': h_title,
                            'teacher_id': False,
                            'subject_id': False,
                            'subject_ids': False,
                            'student_ids': target_students,
                            'day_of_week': line.day_of_week,
                            'period': 'custom',
                            'specific_start_time': False,
                            'start_time': 7.5,
                            'end_time': 17.0,
                            'start_datetime': s_dt,
                            'end_datetime': e_dt,
                            'room': False,
                            'notes': line.notes or (_("Holiday - %s") % h_title),
                        })
                    else:
                        sub_name = line.subject_id.name or ""
                        custom_title = f"{line.notes} - {target_name}" if line.notes else (f"{sub_name} - {target_name}" if target_name else sub_name)
                        s_dt = Timetable._local_to_utc(target_date, line.start_time)
                        e_dt = Timetable._local_to_utc(target_date, line.end_time)
                        vals_list.append({
                            'name': custom_title,
                            'term_id': self.term_id.id,
                            'class_id': self.class_id.id,
                            'week_number': w_num,
                            'is_holiday': False,
                            'teacher_id': line.teacher_id.id,
                            'subject_id': line.subject_id.id,
                            'subject_ids': [(6, 0, [line.subject_id.id])],
                            'student_ids': target_students,
                            'day_of_week': line.day_of_week,
                            'period': line.period,
                            'specific_start_time': line.specific_start_time,
                            'start_time': line.start_time,
                            'end_time': line.end_time,
                            'start_datetime': s_dt,
                            'end_datetime': e_dt,
                            'room': line.room or self.class_id.room,
                            'notes': line.notes,
                        })

        # MODE 3: Single recurring slot
        elif self.mode == 'quick_slot':
            if not self.single_subject_id:
                raise UserError(_("Please select a Subject."))
            if not self.single_teacher_id:
                raise UserError(_("Please select a Teacher."))

            sub_name = self.single_subject_id.name or ""
            custom_title = f"{self.single_notes} - {target_name}" if self.single_notes else (f"{sub_name} - {target_name}" if target_name else sub_name)

            for w_num in target_weeks:
                week_monday = first_monday + timedelta(weeks=w_num - 1)
                t_date = week_monday + timedelta(days=int(self.single_day_of_week))
                if t_date in existing_holiday_dates:
                    continue
                s_dt = Timetable._local_to_utc(t_date, self.single_start_time)
                e_dt = Timetable._local_to_utc(t_date, self.single_end_time)
                vals_list.append({
                    'name': custom_title,
                    'term_id': self.term_id.id,
                    'class_id': self.class_id.id,
                    'week_number': w_num,
                    'teacher_id': self.single_teacher_id.id,
                    'subject_id': self.single_subject_id.id,
                    'subject_ids': [(6, 0, [self.single_subject_id.id])],
                    'student_ids': target_students,
                    'day_of_week': self.single_day_of_week,
                    'period': self.single_period,
                    'specific_start_time': self.single_specific_start_time,
                    'start_time': self.single_start_time,
                    'end_time': self.single_end_time,
                    'start_datetime': s_dt,
                    'end_datetime': e_dt,
                    'room': self.single_room or self.class_id.room,
                    'notes': self.single_notes,
                })

        created = Timetable.create(vals_list) if vals_list else Timetable.browse()

        # Link Class to Term
        if self.class_id not in self.term_id.class_ids:
            self.term_id.class_ids = [(4, self.class_id.id)]
        if self.term_id not in self.class_id.term_ids:
            self.class_id.term_ids = [(4, self.term_id.id)]
        if self.activate_target_term:
            if self.term_id.state == 'draft':
                self.term_id.action_start_term()
            self.class_id.current_term_id = self.term_id.id

        return {
            'name': _('Timetable - %s (%s)') % (self.class_id.name, self.term_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'domain': [('term_id', '=', self.term_id.id), ('class_id', '=', self.class_id.id)],
            'context': {
                'default_term_id': self.term_id.id,
                'default_class_id': self.class_id.id,
                'search_default_filter_mon_fri': 1,
            },
        }


class SchoolTermScheduleWizardLine(models.TransientModel):
    _name = 'school.term.schedule.wizard.line'
    _description = 'Term Schedule Wizard Session Line'
    _order = 'day_of_week, start_time'

    wizard_id = fields.Many2one('school.term.schedule.wizard', string='Wizard', ondelete='cascade', required=True)
    day_of_week = fields.Selection(DAY_SELECTION, string='Day of Week', default='0', required=True)
    period = fields.Selection(PERIOD_SELECTION, string='Period', default='p1', required=True)
    specific_start_time = fields.Selection(START_TIME_SELECTION, string='Start Hour')
    start_time = fields.Float(string='Start Time', default=8.0, required=True)
    end_time = fields.Float(string='End Time', default=9.0, required=True)
    is_holiday = fields.Boolean(string='Holiday', default=False)
    holiday_name = fields.Char(string='Holiday Reason')
    subject_id = fields.Many2one('school.subject', string='Subject', required=False)
    teacher_id = fields.Many2one('school.teacher', string='Teacher', required=False)
    room = fields.Char(string='Room / Location')
    notes = fields.Char(string='Notes / Topics')

    @api.onchange('is_holiday')
    def _onchange_is_holiday(self):
        if self.is_holiday:
            self.subject_id = False
            self.teacher_id = False
            self.room = False
            self.period = 'custom'
            self.start_time = 7.5
            self.end_time = 17.0
            self.specific_start_time = False
            if not self.holiday_name:
                self.holiday_name = _("Holiday")
        else:
            self.holiday_name = False

    @api.onchange('period')
    def _onchange_period(self):
        if self.period and self.period in PERIOD_PRESETS:
            s, e = PERIOD_PRESETS[self.period]
            self.start_time = s
            self.end_time = e
            matched = False
            for k, _ in START_TIME_SELECTION:
                if abs(s - float(k)) < 0.02:
                    matched = k
                    break
            self.specific_start_time = matched

    @api.onchange('specific_start_time')
    def _onchange_specific_start_time(self):
        if self.specific_start_time:
            val = float(self.specific_start_time)
            dur = (self.end_time - self.start_time) if (self.end_time and self.end_time > self.start_time) else 1.0
            self.start_time = val
            self.end_time = min(24.0, round(val + dur, 2))
            self.period = self._match_period(self.start_time, self.end_time)

    @api.onchange('start_time', 'end_time')
    def _onchange_start_end_time(self):
        if self.start_time is not None and self.end_time is not None:
            self.period = self._match_period(self.start_time, self.end_time)
            matched = False
            for k, _ in START_TIME_SELECTION:
                if abs(self.start_time - float(k)) < 0.02:
                    matched = k
                    break
            self.specific_start_time = matched

    def _match_period(self, s, e):
        for code, (ps, pe) in PERIOD_PRESETS.items():
            if abs(ps - s) < 0.05 and abs(pe - e) < 0.05:
                return code
        return 'custom'
