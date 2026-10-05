import os

def update_timetable():
    p = 'custom/school_management/models/timetable.py'
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update default_get
    old_def = """            if 'start_datetime' in fields_list or 'end_datetime' in fields_list:
                term_obj = self.env['school.term'].browse(res['term_id']) if res.get('term_id') else False
                w_num = res.get('week_number', 1)"""

    new_def = """            if 'start_datetime' in fields_list or 'end_datetime' in fields_list:
                effective_term_id = res.get('term_id') or self.env.context.get('default_term_id')
                term_obj = self.env['school.term'].browse(effective_term_id) if effective_term_id else False
                w_num = res.get('week_number', 1)"""

    if old_def in content:
        content = content.replace(old_def, new_def, 1)
        print("Updated default_get in timetable.py")

    # 2. Update _inverse_specific_start_time
    old_inv = """    def _inverse_specific_start_time(self):
        for rec in self:
            if rec.specific_start_time:
                val = float(rec.specific_start_time)
                duration = (rec.end_time - rec.start_time) if (rec.end_time and rec.end_time > rec.start_time) else 1.0
                rec.start_time = val
                rec.end_time = min(24.0, round(val + duration, 2))
                rec.period = rec._match_period(rec.start_time, rec.end_time)"""

    new_inv = """    def _inverse_specific_start_time(self):
        for rec in self:
            if rec.specific_start_time:
                val = float(rec.specific_start_time)
                if abs(rec.start_time - val) > 0.001:
                    duration = (rec.end_time - rec.start_time) if (rec.end_time and rec.end_time > rec.start_time) else 1.0
                    rec.start_time = val
                    rec.end_time = min(24.0, round(val + duration, 2))
                    rec.period = rec._match_period(rec.start_time, rec.end_time)"""

    if old_inv in content:
        content = content.replace(old_inv, new_inv, 1)
        print("Updated _inverse_specific_start_time in timetable.py")

    # 3. Add action_open_master_timetable
    method_code = '''
    @api.model
    def action_open_master_timetable(self):
        """Open master timetable calendar dynamically anchored to the active term's start date."""
        active_term = self.env['school.term'].search([('state', '=', 'active')], limit=1)
        if not active_term:
            active_term = self.env['school.term'].search([], order='date_start desc', limit=1)
        ctx = {
            'search_default_filter_active_term': 1,
            'search_default_filter_mon_fri': 1,
        }
        if active_term and active_term.date_start:
            ctx['default_term_id'] = active_term.id
            today = fields.Date.context_today(self)
            if active_term.date_end and (today < active_term.date_start or today > active_term.date_end):
                ctx['initial_date'] = active_term.date_start.isoformat()
            else:
                ctx['initial_date'] = today.isoformat()

        action = self.env.ref('school_management.action_timetable').read()[0]
        action['context'] = ctx
        return action
'''
    if 'def action_open_master_timetable' not in content:
        content = content.rstrip() + '\n' + method_code
        print("Added action_open_master_timetable in timetable.py")

    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)


def update_assign_wizard():
    p = 'custom/school_management/wizards/assign_subject_wizard.py'
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()

    old_slot = """                slot = self.env['school.timetable'].create({
                    'term_id': effective_term.id if effective_term else False,
                    'class_id': self.class_id.id,
                    'subject_id': subject.id,
                    'teacher_id': self.teacher_id.id,
                    'day_of_week': self.day_of_week,
                    'period': period_val,
                    'start_time': self.start_time,
                    'end_time': self.end_time,
                    'room': self.room or self.class_id.room,
                    'notes': self.notes,
                })"""

    new_slot = """                slot_vals = {
                    'term_id': effective_term.id if effective_term else False,
                    'class_id': self.class_id.id,
                    'week_number': 1,
                    'subject_id': subject.id,
                    'teacher_id': self.teacher_id.id,
                    'day_of_week': self.day_of_week,
                    'period': period_val,
                    'start_time': self.start_time,
                    'end_time': self.end_time,
                    'room': self.room or self.class_id.room,
                    'notes': self.notes,
                }
                if effective_term and effective_term.date_start:
                    first_mon = effective_term.date_start - timedelta(days=effective_term.date_start.weekday())
                    t_date = first_mon + timedelta(days=int(self.day_of_week or 0))
                    s_dt = self.env['school.timetable']._local_to_utc(t_date, self.start_time)
                    e_dt = self.env['school.timetable']._local_to_utc(t_date, self.end_time)
                    slot_vals['start_datetime'] = s_dt
                    slot_vals['end_datetime'] = e_dt
                slot = self.env['school.timetable'].create(slot_vals)"""

    if old_slot in content:
        content = content.replace(old_slot, new_slot, 1)
        print("Updated assign_subject_wizard.py slot creation")
        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)


def update_school_class():
    p = 'custom/school_management/models/school_class.py'
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()

    old_action = """    def action_view_master_timetable(self):
        self.ensure_one()
        return {
            'name': _('Master Timetable & Calendar'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'context': {'search_default_filter_mon_fri': 1},
        }"""

    new_action = """    def action_view_master_timetable(self):
        self.ensure_one()
        ctx = {
            'search_default_filter_mon_fri': 1,
            'search_default_filter_active_term': 1,
        }
        if self.current_term_id:
            ctx['search_default_term_id'] = self.current_term_id.id
            if self.current_term_id.date_start:
                ctx['initial_date'] = self.current_term_id.date_start.isoformat()
        return {
            'name': _('Master Timetable & Calendar'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,kanban,form',
            'context': ctx,
        }"""

    if old_action in content:
        content = content.replace(old_action, new_action, 1)
        print("Updated action_view_master_timetable in school_class.py")
        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)


if __name__ == '__main__':
    update_timetable()
    update_assign_wizard()
    update_school_class()
    print("All Python updates applied successfully.")
