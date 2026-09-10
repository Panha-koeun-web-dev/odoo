from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SchoolExamSelectStudentWizard(models.TransientModel):
    _name = 'school.exam.select.student.wizard'
    _description = 'Select Students for Examination'

    exam_id = fields.Many2one(
        'school.exam',
        string='Examination',
        required=True,
        domain="[('state', 'not in', ('completed', 'cancelled'))]"
    )
    class_id = fields.Many2one(
        'school.class',
        string='Class',
        related='exam_id.class_id',
        readonly=True
    )
    subject_id = fields.Many2one(
        'school.subject',
        string='Subject',
        related='exam_id.subject_id',
        readonly=True
    )
    exam_start_datetime = fields.Datetime(
        string='Exam Start',
        related='exam_id.start_datetime',
        readonly=True
    )
    exam_end_datetime = fields.Datetime(
        string='Exam End',
        related='exam_id.end_datetime',
        readonly=True
    )
    exam_room = fields.Char(
        string='Exam Venue',
        related='exam_id.room',
        readonly=True
    )

    student_ids = fields.Many2many(
        'school.student',
        'school_exam_select_student_rel',
        'wizard_id',
        'student_id',
        string='Students to Exam'
    )
    student_count = fields.Integer(
        string='Selected Students Count',
        compute='_compute_student_count'
    )

    # Schedule Options for selected students
    schedule_mode = fields.Selection([
        ('standard', 'Use General Exam Timing & Venue'),
        ('custom', 'Set Specific Custom Timeslot / Room'),
    ], string='Schedule Mode', default='standard', required=True)

    specific_start_datetime = fields.Datetime(
        string='Specific Start Date & Time',
        default=fields.Datetime.now
    )
    specific_end_datetime = fields.Datetime(
        string='Specific End Date & Time'
    )
    room = fields.Char(string='Specific Room / Seat / Link')
    attendance_status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('present', 'Present / Attended'),
        ('absent', 'Absent'),
        ('excused', 'Excused / Rescheduled'),
    ], string='Attendance Status', default='scheduled')
    schedule_notes = fields.Char(
        string='Timeslot Reason / Notes'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        exam_id = res.get('exam_id') or self.env.context.get('default_exam_id')
        pre_student_ids = self.env.context.get('default_student_ids')

        if exam_id:
            exam = self.env['school.exam'].browse(exam_id)
            if 'specific_start_datetime' in fields_list and not res.get('specific_start_datetime'):
                res['specific_start_datetime'] = exam.start_datetime
            if 'specific_end_datetime' in fields_list and not res.get('specific_end_datetime'):
                res['specific_end_datetime'] = exam.end_datetime
            if 'room' in fields_list and not res.get('room'):
                res['room'] = exam.room

            existing_student_ids = set(exam.grade_ids.mapped('student_id.id'))

            if pre_student_ids:
                # Pre-selected from student view
                chosen = [sid for sid in pre_student_ids if sid not in existing_student_ids]
                res['student_ids'] = [(6, 0, chosen)]
            else:
                # Populate available students from the exam's class
                domain = [('active', '=', True), ('study_status', '!=', 'stopped')]
                if exam.class_id:
                    domain.append(('class_id', '=', exam.class_id.id))
                students = self.env['school.student'].search(domain, order='name')
                eligible = [s.id for s in students if s.id not in existing_student_ids]
                res['student_ids'] = [(6, 0, eligible)]

        elif pre_student_ids:
            res['student_ids'] = [(6, 0, pre_student_ids)]

        return res

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    @api.onchange('exam_id')
    def _onchange_exam_id(self):
        if not self.exam_id:
            return
        if not self.specific_start_datetime:
            self.specific_start_datetime = self.exam_id.start_datetime
        if not self.specific_end_datetime:
            self.specific_end_datetime = self.exam_id.end_datetime
        if not self.room:
            self.room = self.exam_id.room

        existing_student_ids = set(self.exam_id.grade_ids.mapped('student_id.id'))
        domain = [('active', '=', True), ('study_status', '!=', 'stopped')]
        if self.exam_id.class_id:
            domain.append(('class_id', '=', self.exam_id.class_id.id))
        students = self.env['school.student'].search(domain, order='name')
        eligible = [s.id for s in students if s.id not in existing_student_ids]
        self.student_ids = [(6, 0, eligible)]

    def action_populate_class_students(self):
        """Populate all available students from the exam class."""
        self.ensure_one()
        if not self.exam_id:
            raise UserError(_("Please select an exam first."))
        existing_student_ids = set(self.exam_id.grade_ids.mapped('student_id.id'))
        domain = [('active', '=', True), ('study_status', '!=', 'stopped')]
        if self.exam_id.class_id:
            domain.append(('class_id', '=', self.exam_id.class_id.id))
        students = self.env['school.student'].search(domain, order='name')
        eligible = [s.id for s in students if s.id not in existing_student_ids]
        self.student_ids = [(6, 0, eligible)]
        return {'type': 'ir.actions.do_nothing'}

    def action_populate_all_students(self):
        """Populate all active students across all classes."""
        self.ensure_one()
        if not self.exam_id:
            raise UserError(_("Please select an exam first."))
        existing_student_ids = set(self.exam_id.grade_ids.mapped('student_id.id'))
        students = self.env['school.student'].search([('active', '=', True), ('study_status', '!=', 'stopped')], order='name')
        eligible = [s.id for s in students if s.id not in existing_student_ids]
        self.student_ids = [(6, 0, eligible)]
        return {'type': 'ir.actions.do_nothing'}

    def action_clear_selection(self):
        """Clear currently selected students."""
        self.ensure_one()
        self.student_ids = [(5, 0, 0)]
        return {'type': 'ir.actions.do_nothing'}

    def action_add_students_to_exam(self):
        """Add selected students into the exam's grade_ids."""
        self.ensure_one()
        if not self.exam_id:
            raise UserError(_("Please select an exam first."))

        if not self.student_ids:
            raise UserError(_("Please select at least one student to add to this exam."))

        existing_student_ids = set(self.exam_id.grade_ids.mapped('student_id.id'))
        new_students = self.student_ids.filtered(lambda s: s.id not in existing_student_ids)

        if not new_students:
            raise UserError(_("All selected students are already scheduled for this exam."))

        is_custom = (self.schedule_mode == 'custom')
        if is_custom and self.specific_end_datetime and self.specific_start_datetime:
            if self.specific_end_datetime < self.specific_start_datetime:
                raise ValidationError(_("Specific End Time cannot be earlier than Start Time!"))

        start_dt = self.specific_start_datetime if (is_custom and self.specific_start_datetime) else self.exam_id.start_datetime
        end_dt = self.specific_end_datetime if (is_custom and self.specific_end_datetime) else self.exam_id.end_datetime
        venue = self.room if (is_custom and self.room) else self.exam_id.room

        vals_list = []
        for student in new_students:
            vals_list.append({
                'exam_id': self.exam_id.id,
                'student_id': student.id,
                'is_custom_schedule': is_custom,
                'exam_datetime': start_dt,
                'exam_end_datetime': end_dt,
                'room': venue,
                'attendance_status': self.attendance_status or 'scheduled',
                'schedule_notes': self.schedule_notes if is_custom else False,
            })

        self.env['school.grade'].create(vals_list)

        msg = _("Successfully added %d student(s) to exam '%s'.") % (len(vals_list), self.exam_id.name)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Students Added to Exam'),
                'message': msg,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
