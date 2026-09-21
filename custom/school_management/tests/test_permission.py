from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from odoo import fields


class TestSchoolPermission(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Student = cls.env['school.student']
        cls.Teacher = cls.env['school.teacher']
        cls.Permission = cls.env['school.permission']
        cls.Attendance = cls.env['school.attendance']
        cls.RejectWizard = cls.env['school.permission.reject.wizard']

        # 1. Create Student A
        cls.student_a = cls.Student.create({
            'name': 'Permission Student A',
            'student_id': 'STU_PERM_A',
            'gender': 'male',
            'date_of_birth': fields.Date.from_string('2006-05-15'),
            'email': 'student_perm_a@school.test',
        })
        cls.student_a.action_create_user()
        cls.student_user_a = cls.student_a.user_id

        # 2. Create Student B
        cls.student_b = cls.Student.create({
            'name': 'Permission Student B',
            'student_id': 'STU_PERM_B',
            'gender': 'female',
            'date_of_birth': fields.Date.from_string('2006-08-20'),
            'email': 'student_perm_b@school.test',
        })
        cls.student_b.action_create_user()
        cls.student_user_b = cls.student_b.user_id

        # 3. Create Teacher
        cls.teacher = cls.Teacher.create({
            'name': 'Permission Reviewer Teacher',
            'employee_id': 'TCH_PERM_1',
            'email': 'teacher_perm_1@school.test',
            'gender': 'male',
        })
        cls.teacher.action_create_user()
        cls.teacher_user = cls.teacher.user_id

        # 4. Admin user
        cls.admin_user = cls.env.ref('base.user_admin')

    def test_01_student_create_permission_request(self):
        """Student creates a permission request; verify initial values and auto-reference."""
        perm = self.Permission.with_user(self.student_user_a).create({
            'student_id': self.student_a.id,
            'permission_type': 'sick',
            'session_type': 'full_day',
            'start_date': date.today(),
            'end_date': date.today(),
            'reason': 'Severe flu and fever, visiting doctor.',
        })

        self.assertTrue(perm.name.startswith('PERM/'))
        self.assertEqual(perm.state, 'draft')
        self.assertEqual(perm.duration_days, 1.0)
        self.assertEqual(perm.student_id.id, self.student_a.id)

    def test_02_student_cannot_approve_request(self):
        """Student cannot approve their own permission request."""
        perm = self.Permission.with_user(self.student_user_a).create({
            'student_id': self.student_a.id,
            'permission_type': 'leave',
            'start_date': date.today(),
            'end_date': date.today(),
            'reason': 'Family gathering.',
        })

        with self.assertRaises(UserError):
            perm.with_user(self.student_user_a).action_approve()

    def test_03_teacher_approves_request(self):
        """Teacher approves request; status updates to 'approved' and auto-syncs excused attendance."""
        today = date.today()
        perm = self.Permission.with_user(self.student_user_a).create({
            'student_id': self.student_a.id,
            'permission_type': 'sick',
            'start_date': today,
            'end_date': today,
            'reason': 'Medical checkup.',
            'auto_update_attendance': True,
        })

        # Teacher approves
        perm.with_user(self.teacher_user).action_approve()

        self.assertEqual(perm.state, 'approved')
        self.assertEqual(perm.approved_by.id, self.teacher_user.id)
        self.assertEqual(perm.approver_role, 'teacher')
        self.assertTrue(perm.approval_date)

        # Verify attendance record created as excused
        att = self.Attendance.sudo().search([
            ('student_id', '=', self.student_a.id),
            ('date', '=', today),
        ], limit=1)
        self.assertTrue(att, "Attendance record should have been created.")
        self.assertEqual(att.status, 'excused')
        self.assertEqual(att.permission_id.id, perm.id)

    def test_04_admin_rejects_request_with_wizard(self):
        """Admin or teacher can reject request with a clear reason."""
        perm = self.Permission.with_user(self.student_user_a).create({
            'student_id': self.student_a.id,
            'permission_type': 'leave',
            'start_date': date.today() + timedelta(days=5),
            'end_date': date.today() + timedelta(days=6),
            'reason': 'Vacation trip.',
        })

        # Use reject wizard
        wizard = self.RejectWizard.with_user(self.admin_user).create({
            'permission_id': perm.id,
            'rejection_reason': 'Conflicts with scheduled mid-term exam week.',
        })
        wizard.action_confirm_reject()

        self.assertEqual(perm.state, 'rejected')
        self.assertEqual(perm.approved_by.id, self.admin_user.id)
        self.assertEqual(perm.rejection_reason, 'Conflicts with scheduled mid-term exam week.')

    def test_05_student_cannot_see_other_student_requests(self):
        """Student A cannot access Student B's permission requests."""
        perm_b = self.Permission.with_user(self.student_user_b).create({
            'student_id': self.student_b.id,
            'permission_type': 'sick',
            'start_date': date.today(),
            'end_date': date.today(),
            'reason': 'Dentist appointment.',
        })

        visible_perms = self.Permission.with_user(self.student_user_a).search([('id', '=', perm_b.id)])
        self.assertFalse(visible_perms, "Student A should not see Student B's permission request.")

    def test_06_student_can_cancel_draft(self):
        """Student can cancel their own draft permission request."""
        perm = self.Permission.with_user(self.student_user_a).create({
            'student_id': self.student_a.id,
            'permission_type': 'leave',
            'start_date': date.today() + timedelta(days=1),
            'end_date': date.today() + timedelta(days=1),
            'reason': 'Need to assist parents.',
        })
        perm.with_user(self.student_user_a).action_cancel()
        self.assertEqual(perm.state, 'cancel')

    def test_07_duration_days_computation(self):
        """Verify duration computation for various session types."""
        today = date.today()
        # Single full day
        perm1 = self.Permission.create({
            'student_id': self.student_a.id,
            'session_type': 'full_day',
            'start_date': today,
            'end_date': today,
            'reason': 'Test',
        })
        self.assertEqual(perm1.duration_days, 1.0)

        # Morning half day
        perm2 = self.Permission.create({
            'student_id': self.student_a.id,
            'session_type': 'morning',
            'start_date': today,
            'end_date': today,
            'reason': 'Test',
        })
        self.assertEqual(perm2.duration_days, 0.5)

        # 3 full days
        perm3 = self.Permission.create({
            'student_id': self.student_a.id,
            'session_type': 'full_day',
            'start_date': today,
            'end_date': today + timedelta(days=2),
            'reason': 'Test',
        })
        self.assertEqual(perm3.duration_days, 3.0)
