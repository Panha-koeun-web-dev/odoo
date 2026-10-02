from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from ..models.timetable import DAY_SELECTION, PERIOD_SELECTION, PERIOD_PRESETS, START_TIME_SELECTION


class SchoolAssignSubjectWizard(models.TransientModel):
    _name = 'school.assign.subject.wizard'
    _description = 'Assign Subjects, Teachers and Schedules Wizard'

    mode = fields.Selection([
        ('teacher_assign', 'Assign Teacher to Teach Class & Students'),
        ('student_enroll', 'Enroll Students in Weekly Subjects'),
        ('schedule_quick', 'Fast Timetable Session Scheduler'),
    ], string='Assignment Mode', default='teacher_assign', required=True)

    # Academic Term Integration
    term_id = fields.Many2one(
        'school.term',
        string='Academic Term',
        help="Academic term (defaults to active term if unspecified)."
    )

    # Core relations
    teacher_id = fields.Many2one('school.teacher', string='Teacher')
    class_id = fields.Many2one('school.class', string='Class')
    student_id = fields.Many2one('school.student', string='Specific Student')
    student_ids = fields.Many2many('school.student', string='Target Students')

    subject_id = fields.Many2one('school.subject', string='Subject')
    subject_ids = fields.Many2many('school.subject', string='Subjects to Enroll')

    # Workload parameters
    weekly_hours = fields.Float(string='Weekly Target Hours', default=4.0)
    weekly_sessions = fields.Integer(string='Sessions per Week', default=2)
    subject_type = fields.Selection([
        ('core', 'Core Subject'),
        ('elective', 'Elective Course'),
        ('extra', 'Remedial / Extra Tutoring'),
    ], string='Subject Type', default='core')
    study_status = fields.Selection([
        ('active', 'Active Studying'),
        ('exempt', 'Exempt'),
    ], string='Study Status', default='active')

    # Optional Timetable Generation
    create_timetable_slots = fields.Boolean(string='Also Create Weekly Timetable Slot', default=False)
    day_of_week = fields.Selection(DAY_SELECTION, string='Day of Week', default='0')
    period = fields.Selection(PERIOD_SELECTION, string='Period', default='p1')
    specific_start_time = fields.Selection(
        START_TIME_SELECTION,
        string='Specific Start Hour',
        help="Quickly set a specific start time from 12 AM to 11 PM"
    )
    start_time = fields.Float(string='Start Time', default=8.0)
    end_time = fields.Float(string='End Time', default=9.0)
    room = fields.Char(string='Classroom / Room')
    notes = fields.Text(string='Notes / Instructions')

    # -------------------------------------------------------------------------
    # ONCHANGES
    # -------------------------------------------------------------------------
    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            if not self.term_id and self.class_id.current_term_id:
                self.term_id = self.class_id.current_term_id
            if not self.room and self.class_id.room:
                self.room = self.class_id.room
            if not self.teacher_id and self.class_id.teacher_id:
                self.teacher_id = self.class_id.teacher_id
            if self.mode == 'student_enroll' and not self.student_ids:
                self.student_ids = self.class_id.student_ids

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            if self.student_id.class_id and not self.class_id:
                self.class_id = self.student_id.class_id

    @api.onchange('teacher_id')
    def _onchange_teacher_id(self):
        if self.teacher_id and not self.subject_id:
            assignments = self.teacher_id.teaching_assignment_ids.filtered(lambda a: a.active)
            if assignments:
                self.subject_id = assignments[0].subject_id
            elif self.teacher_id.subject_ids:
                self.subject_id = self.teacher_id.subject_ids[0]

    @api.onchange('period')
    def _onchange_period(self):
        if self.period and self.period in PERIOD_PRESETS:
            s_time, e_time = PERIOD_PRESETS[self.period]
            self.start_time = s_time
            self.end_time = e_time
            matched = False
            for k, _ in START_TIME_SELECTION:
                if abs(s_time - float(k)) < 0.02:
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
            matched_p = 'custom'
            for p_key, (ps, pe) in PERIOD_PRESETS.items():
                if abs(self.start_time - ps) < 0.02 and abs(self.end_time - pe) < 0.02:
                    matched_p = p_key
                    break
            self.period = matched_p

    @api.onchange('start_time', 'end_time')
    def _onchange_timing(self):
        matched = False
        if self.start_time is not None:
            for k, _ in START_TIME_SELECTION:
                if abs(self.start_time - float(k)) < 0.02:
                    matched = k
                    break
            self.specific_start_time = matched
        for p_key, (p_start, p_end) in PERIOD_PRESETS.items():
            if abs(self.start_time - p_start) < 0.02 and abs(self.end_time - p_end) < 0.02:
                self.period = p_key
                return
        self.period = 'custom'

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        if self.mode == 'teacher_assign':
            return self._apply_teacher_assign()
        elif self.mode == 'student_enroll':
            return self._apply_student_enroll()
        elif self.mode == 'schedule_quick':
            return self._apply_quick_schedule()

    def _apply_teacher_assign(self):
        if not self.teacher_id:
            raise UserError(_("Please select a Teacher."))
        if not self.class_id:
            raise UserError(_("Please select a Class."))
        subjects = self.subject_ids or (self.subject_id if self.subject_id else False)
        if not subjects:
            raise UserError(_("Please select at least one Subject to assign."))

        Assignment = self.env['school.teaching.assignment']
        StudentSubject = self.env['school.student.subject']
        target_students = self.class_id.student_ids.filtered(lambda s: s.active and s.study_status == 'studying')

        slot_created = False
        synced_count = 0

        for subject in subjects:
            # 1. Upsert SchoolTeachingAssignment
            asg = Assignment.search([
                ('teacher_id', '=', self.teacher_id.id),
                ('class_id', '=', self.class_id.id),
                ('subject_id', '=', subject.id),
            ], limit=1)
            if not asg:
                asg = Assignment.create({
                    'teacher_id': self.teacher_id.id,
                    'class_id': self.class_id.id,
                    'subject_id': subject.id,
                    'weekly_hours': self.weekly_hours,
                    'weekly_sessions': self.weekly_sessions,
                    'active': True,
                })
            else:
                asg.write({
                    'weekly_hours': self.weekly_hours,
                    'weekly_sessions': self.weekly_sessions,
                    'active': True,
                })

            # Ensure teacher's subject_ids has this subject
            if subject not in self.teacher_id.subject_ids:
                self.teacher_id.subject_ids = [(4, subject.id)]
            # Ensure class's subject_ids has this subject
            if subject not in self.class_id.subject_ids:
                self.class_id.subject_ids = [(4, subject.id)]

            # 2. Sync to all enrolled students in the class
            for student in target_students:
                rec = StudentSubject.search([
                    ('student_id', '=', student.id),
                    ('subject_id', '=', subject.id),
                    ('teacher_id', '=', self.teacher_id.id),
                ], limit=1)
                vals = {
                    'student_id': student.id,
                    'class_id': self.class_id.id,
                    'subject_id': subject.id,
                    'teacher_id': self.teacher_id.id,
                    'subject_type': self.subject_type,
                    'weekly_hours': self.weekly_hours,
                    'weekly_sessions': self.weekly_sessions,
                    'study_status': self.study_status,
                    'active': True,
                }
                if rec:
                    rec.write(vals)
                else:
                    StudentSubject.create(vals)
                synced_count += 1

            # 3. Optionally create weekly timetable slot for the first/single subject
            if self.create_timetable_slots and not slot_created:
                effective_term = self.term_id or self.class_id.current_term_id
                if not effective_term:
                    effective_term = self.env['school.term'].search([('state', '=', 'active')], limit=1)
                period_val = self.period
                if self.start_time is not None and self.end_time is not None:
                    if period_val in PERIOD_PRESETS:
                        ps, pe = PERIOD_PRESETS[period_val]
                        if abs(self.start_time - ps) > 0.02 or abs(self.end_time - pe) > 0.02:
                            period_val = 'custom'
                            for p_key, (pps, ppe) in PERIOD_PRESETS.items():
                                if abs(self.start_time - pps) < 0.02 and abs(self.end_time - ppe) < 0.02:
                                    period_val = p_key
                                    break
                slot = self.env['school.timetable'].create({
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
                })
                slot_created = bool(slot)

        sub_names = ', '.join(subjects.mapped('name'))
        msg = _(
            "Teaching Assignment Configured!\n"
            "• Teacher: %(teacher)s\n"
            "• Subject(s): %(subjects)s\n"
            "• Class: %(class_name)s (%(students)d student-subject entries registered)\n"
            "• Weekly Load: %(hours)sh / %(sessions)d sessions per subject\n"
            "%(slot_info)s"
        ) % {
            'teacher': self.teacher_id.name,
            'subjects': sub_names,
            'class_name': self.class_id.name,
            'students': synced_count,
            'hours': self.weekly_hours,
            'sessions': self.weekly_sessions,
            'slot_info': "• Timetable schedule slot generated!" if slot_created else "",
        }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Assignment Successful'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }

    def _apply_student_enroll(self):
        students = self.student_ids
        if not students and self.student_id:
            students = self.student_id
        if not students and self.class_id:
            students = self.class_id.student_ids.filtered(lambda s: s.active and s.study_status == 'studying')

        if not students:
            raise UserError(_("Please select at least one Student or a Class with active students."))

        subjects = self.subject_ids or (self.subject_id if self.subject_id else False)
        if not subjects:
            raise UserError(_("Please select at least one Subject to enroll."))

        StudentSubject = self.env['school.student.subject']
        Assignment = self.env['school.teaching.assignment']
        total_registered = 0

        for student in students:
            c_id = student.class_id.id if student.class_id else (self.class_id.id if self.class_id else False)
            for subject in subjects:
                assigned_teacher = self.teacher_id
                if not assigned_teacher and c_id:
                    asg = Assignment.search([
                        ('class_id', '=', c_id),
                        ('subject_id', '=', subject.id),
                        ('active', '=', True),
                    ], limit=1)
                    if asg:
                        assigned_teacher = asg.teacher_id

                rec = StudentSubject.search([
                    ('student_id', '=', student.id),
                    ('subject_id', '=', subject.id),
                ], limit=1)

                vals = {
                    'student_id': student.id,
                    'class_id': c_id,
                    'subject_id': subject.id,
                    'teacher_id': assigned_teacher.id if assigned_teacher else False,
                    'subject_type': self.subject_type,
                    'weekly_hours': self.weekly_hours,
                    'weekly_sessions': self.weekly_sessions,
                    'study_status': self.study_status,
                    'active': True,
                }
                if rec:
                    rec.write(vals)
                else:
                    StudentSubject.create(vals)
                total_registered += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Enrolled Successfully'),
                'message': _("%(count)d student-subject study registrations processed.") % {'count': total_registered},
                'type': 'success',
                'sticky': False,
            }
        }

    def _apply_quick_schedule(self):
        if not self.teacher_id:
            raise UserError(_("Please select a Teacher."))
        subjects = self.subject_ids or self.subject_id
        if not subjects:
            raise UserError(_("Please select at least one Subject."))
        if not self.class_id and not self.student_id and not self.student_ids:
            raise UserError(_("Please select either a Class, a specific Student, or Assigned Students."))

        effective_term = self.term_id
        if not effective_term and self.class_id and self.class_id.current_term_id:
            effective_term = self.class_id.current_term_id
        if not effective_term:
            effective_term = self.env['school.term'].search([('state', '=', 'active')], limit=1)

        period_val = self.period
        if self.start_time is not None and self.end_time is not None:
            if period_val in PERIOD_PRESETS:
                ps, pe = PERIOD_PRESETS[period_val]
                if abs(self.start_time - ps) > 0.02 or abs(self.end_time - pe) > 0.02:
                    period_val = 'custom'
                    for p_key, (pps, ppe) in PERIOD_PRESETS.items():
                        if abs(self.start_time - pps) < 0.02 and abs(self.end_time - ppe) < 0.02:
                            period_val = p_key
                            break

        vals = {
            'term_id': effective_term.id if effective_term else False,
            'class_id': self.class_id.id if self.class_id else False,
            'student_id': self.student_id.id if self.student_id else False,
            'teacher_id': self.teacher_id.id,
            'subject_ids': [(6, 0, subjects.ids)],
            'subject_id': subjects[0].id,
            'day_of_week': self.day_of_week,
            'period': period_val,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'room': self.room or (self.class_id.room if self.class_id else ''),
            'notes': self.notes,
        }
        if self.student_ids:
            vals['student_ids'] = [(6, 0, self.student_ids.ids)]

        slot = self.env['school.timetable'].create(vals)

        # Return action to open calendar with new slot highlighted
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timetable Calendar'),
            'res_model': 'school.timetable',
            'view_mode': 'calendar,list,form',
            'res_id': slot.id,
            'target': 'current',
        }
