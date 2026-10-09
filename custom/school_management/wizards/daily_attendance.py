from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolDailyAttendanceWizard(models.TransientModel):
    _name = 'school.daily.attendance.wizard'
    _description = 'Take Daily Student Attendance'

    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    class_id = fields.Many2one('school.class', string='Class')
    line_ids = fields.One2many(
        'school.daily.attendance.line.wizard',
        'wizard_id',
        string='Attendance Lines',
    )
    total_students = fields.Integer(string='Total Students', compute='_compute_summary')
    present_count = fields.Integer(string='Present', compute='_compute_summary')
    absent_count = fields.Integer(string='Absent', compute='_compute_summary')
    late_count = fields.Integer(string='Late', compute='_compute_summary')
    excused_count = fields.Integer(string='Excused', compute='_compute_summary')

    @api.depends('line_ids.status')
    def _compute_summary(self):
        for rec in self:
            lines = rec.line_ids
            rec.total_students = len(lines)
            rec.present_count = sum(1 for l in lines if l.status == 'present')
            rec.absent_count = sum(1 for l in lines if l.status == 'absent')
            rec.late_count = sum(1 for l in lines if l.status == 'late')
            rec.excused_count = sum(1 for l in lines if l.status == 'excused')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        class_id = res.get('class_id') or self.env.context.get('default_class_id')
        date_val = res.get('date') or fields.Date.today()
        if 'line_ids' in fields_list:
            domain = [('active', '=', True), ('study_status', '=', 'studying')]
            if class_id:
                domain.append(('class_id', '=', class_id))
            students = self.env['school.student'].search(domain, order='name')
            
            existing_records = {
                a.student_id.id: a
                for a in self.env['school.attendance'].search([
                    ('date', '=', date_val),
                    ('student_id', 'in', students.ids),
                ])
            }
            
            lines = []
            for student in students:
                att = existing_records.get(student.id)
                lines.append((0, 0, {
                    'student_id': student.id,
                    'class_id': student.class_id.id if student.class_id else False,
                    'status': att.status if att else 'present',
                    'notes': att.notes if att else False,
                }))
            res['line_ids'] = lines
        return res

    @api.onchange('class_id', 'date')
    def _onchange_filter(self):
        self._populate_students()

    def _populate_students(self):
        domain = [('active', '=', True), ('study_status', '=', 'studying')]
        if self.class_id:
            domain.append(('class_id', '=', self.class_id.id))
        students = self.env['school.student'].search(domain, order='name')

        existing_records = {
            a.student_id.id: a
            for a in self.env['school.attendance'].search([
                ('date', '=', self.date),
                ('student_id', 'in', students.ids),
            ])
        }

        self.line_ids = [(5, 0, 0)] + [
            (0, 0, {
                'student_id': student.id,
                'class_id': student.class_id.id if student.class_id else False,
                'status': existing_records[student.id].status if student.id in existing_records else 'present',
                'notes': existing_records[student.id].notes if student.id in existing_records else False,
            })
            for student in students
        ]

    def action_mark_all_present(self):
        self.line_ids.write({'status': 'present'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_mark_all_absent(self):
        self.line_ids.write({'status': 'absent'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_save_attendance(self):
        self.ensure_one()
        valid_lines = self.line_ids.filtered(lambda l: l.student_id)
        if not valid_lines:
            raise UserError(_('No students found to record attendance.'))

        attendance_model = self.env['school.attendance']
        for line in valid_lines:
            existing = attendance_model.search([
                ('student_id', '=', line.student_id.id),
                ('date', '=', self.date),
            ], limit=1)
            if existing:
                existing.write({
                    'status': line.status,
                    'notes': line.notes or '',
                })
            else:
                attendance_model.create({
                    'student_id': line.student_id.id,
                    'date': self.date,
                    'status': line.status,
                    'notes': line.notes or '',
                })

        action = self.env['ir.actions.act_window'].sudo()._for_xml_id('school_management.action_attendance')
        action['domain'] = [('date', '=', self.date)]
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Attendance Saved'),
                'message': _('Daily attendance for %s has been recorded.') % self.date,
                'sticky': False,
                'type': 'success',
                'next': action,
            }
        }


class SchoolDailyAttendanceLineWizard(models.TransientModel):
    _name = 'school.daily.attendance.line.wizard'
    _description = 'Take Daily Student Attendance Line'

    wizard_id = fields.Many2one('school.daily.attendance.wizard', required=True, ondelete='cascade')
    student_id = fields.Many2one('school.student', string='Student')
    student_code = fields.Char(related='student_id.student_id', string='Student ID', readonly=True)
    class_id = fields.Many2one('school.class', string='Class', readonly=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ], string='Status', required=True, default='present')
    notes = fields.Char(string='Notes / Reason')
