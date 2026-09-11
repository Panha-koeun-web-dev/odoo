from odoo import models, fields, api, _


class SchoolStudentAttendance(models.Model):
    _inherit = 'school.student'

    attendance_ids = fields.One2many('school.attendance', 'student_id', string='Attendance')
    attendance_count = fields.Integer(string='Total Attendance', compute='_compute_attendance_stats', store=True)
    absent_count = fields.Integer(string='Absent Days', compute='_compute_attendance_stats', store=True)
    present_count = fields.Integer(string='Present Days', compute='_compute_attendance_stats', store=True)
    late_count = fields.Integer(string='Late Days', compute='_compute_attendance_stats', store=True)
    excused_count = fields.Integer(string='Excused Days', compute='_compute_attendance_stats', store=True)
    attendance_rate = fields.Float(string='Attendance Rate (%)', compute='_compute_attendance_stats', digits=(5, 1), store=True)
    today_attendance_status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('not_marked', 'Not Marked'),
    ], string="Today's Attendance", compute='_compute_today_attendance')
    today_attendance_id = fields.Many2one('school.attendance', string="Today's Attendance Record", compute='_compute_today_attendance')

    @api.depends('attendance_ids.status')
    def _compute_attendance_stats(self):
        for rec in self:
            attendances = rec.attendance_ids
            total = len(attendances)
            present = sum(1 for a in attendances if a.status == 'present')
            absent = sum(1 for a in attendances if a.status == 'absent')
            late = sum(1 for a in attendances if a.status == 'late')
            excused = sum(1 for a in attendances if a.status == 'excused')
            attended = present + late + excused

            rec.attendance_count = total
            rec.present_count = present
            rec.absent_count = absent
            rec.late_count = late
            rec.excused_count = excused
            rec.attendance_rate = round((attended / total * 100), 1) if total else 0.0

    def _compute_today_attendance(self):
        today = fields.Date.today()
        for rec in self:
            today_record = rec.attendance_ids.filtered(lambda a: a.date == today)[:1]
            if today_record:
                rec.today_attendance_id = today_record.id
                rec.today_attendance_status = today_record.status
            else:
                rec.today_attendance_id = False
                rec.today_attendance_status = 'not_marked'

    def _mark_today_attendance(self, status):
        today = fields.Date.today()
        attendance_model = self.env['school.attendance']
        for rec in self:
            record = attendance_model.search([
                ('student_id', '=', rec.id),
                ('date', '=', today),
            ], limit=1)
            if record:
                record.status = status
            else:
                attendance_model.create({
                    'student_id': rec.id,
                    'date': today,
                    'status': status,
                })

    def action_mark_present_today(self):
        self._mark_today_attendance('present')

    def action_mark_absent_today(self):
        self._mark_today_attendance('absent')

    def action_mark_late_today(self):
        self._mark_today_attendance('late')

    def action_mark_excused_today(self):
        self._mark_today_attendance('excused')

    def open_attendance(self):
        action = self._open_records('attendance', [('student_id', '=', self.id)])
        action['context'] = {
            'default_student_id': self.id,
            'default_class_id': self.class_id.id if self.class_id else False,
        }
        return action

    def open_absent_attendance(self):
        action = self._open_records('attendance', [
            ('student_id', '=', self.id),
            ('status', '=', 'absent'),
        ])
        action['name'] = _('Absent Days - %s') % (self.name or '')
        action['context'] = {
            'default_student_id': self.id,
            'default_status': 'absent',
            'default_class_id': self.class_id.id if self.class_id else False,
        }
        return action
