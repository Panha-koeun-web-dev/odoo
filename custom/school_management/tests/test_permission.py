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
        cls.Class = cls.env['school.class']
        cls.Subject = cls.env['school.subject']
        cls.Timetable = cls.env['school.timetable']
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

        # 3. Create Teacher 1
        cls.teacher_1 = cls.Teacher.create({
            'name': 'Permission Reviewer Teacher',
            'employee_id': 'TCH_PERM_1',
            'email': 'teacher_perm_1@school.test',
            'gender': 'male',
        })
        cls.teacher_1.action_create_user()
        cls.teacher_user_1 = cls.teacher_1.user_id

        # 4. Create Teacher 2
        cls.teacher_2 = cls.Teacher.create({
            'name': 'Second Faculty Teacher',
            'employee_id': 'TCH_PERM_2',
            'email': 'teacher_perm_2@school.test',
            'gender': 'female',
        })
        cls.teacher_2.action_create_user()
        cls.teacher_user_2 = cls.teacher_2.user_id

        # 5. Admin user
        cls.admin_user = cls.env.ref('base.user_admin')

    def test_01_student_create_permission_request(self):
        """Student creates a permission request; verify initial values and auto-reference."""
        perm = self.Permission.with_user(self.student_user_a).create({
            'applicant_type': 'student',
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
        self.assertEqual(perm.applicant_type, 'student')
        self.assertEqual(perm.applicant_name, self.student_a.name)

    def test_02_student_cannot_approve_request(self):
        """Student cannot approve their own permission request."""
        perm = self.Permission.with_user(self.student_user_a).create({
            'applicant_type': 'student',
            'student_id': self.student_a.id,
            'permission_type': 'leave',
            'start_date': date.today(),
            'end_date': date.today(),
            'reason': 'Family gathering.',
        })

        with self.assertRaises(UserError):
            perm.with_user(self.student_user_a).action_approve()

    def test_03_teacher_approves_student_request(self):
        """Teacher approves student request; status updates to 'approved' and auto-syncs excused attendance."""
        today = date.today()
        perm = self.Permission.with_user(self.student_user_a).create({
            'applicant_type': 'student',
            'student_id': self.student_a.id,
            'permission_type': 'sick',
            'start_date': today,
            'end_date': today,
            'reason': 'Medical checkup.',
            'auto_update_attendance': True,
        })

        # Teacher approves student request
        perm.with_user(self.teacher_user_1).action_approve()

        self.assertEqual(perm.state, 'approved')
        self.assertEqual(perm.approved_by.id, self.teacher_user_1.id)
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
        """Admin can reject student request with a clear reason."""
        perm = self.Permission.with_user(self.student_user_a).create({
            'applicant_type': 'student',
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
            'applicant_type': 'student',
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
            'applicant_type': 'student',
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
        # Single full day (same day start and end)
        perm1 = self.Permission.create({
            'applicant_type': 'student',
            'student_id': self.student_a.id,
            'session_type': 'full_day',
            'start_date': today,
            'end_date': today,
            'reason': 'Test',
        })
        self.assertEqual(perm1.duration_days, 1.0)

        # 1 day difference (e.g. Sep 22 to Sep 23)
        perm1_diff = self.Permission.create({
            'applicant_type': 'student',
            'student_id': self.student_a.id,
            'session_type': 'full_day',
            'start_date': today,
            'end_date': today + timedelta(days=1),
            'reason': 'Test Diff 1 Day',
        })
        self.assertEqual(perm1_diff.duration_days, 1.0)

        # Morning half day
        perm2 = self.Permission.create({
            'applicant_type': 'student',
            'student_id': self.student_a.id,
            'session_type': 'morning',
            'start_date': today,
            'end_date': today,
            'reason': 'Test',
        })
        self.assertEqual(perm2.duration_days, 0.5)

        # 3 full days difference (e.g. today to today + 3 days)
        perm3 = self.Permission.create({
            'applicant_type': 'student',
            'student_id': self.student_a.id,
            'session_type': 'full_day',
            'start_date': today,
            'end_date': today + timedelta(days=3),
            'reason': 'Test',
        })
        self.assertEqual(perm3.duration_days, 3.0)

    def test_08_teacher_create_permission_request(self):
        """Teacher creates a permission request to admin; verify fields and teacher profile link."""
        perm = self.Permission.with_user(self.teacher_user_1).create({
            'applicant_type': 'teacher',
            'teacher_id': self.teacher_1.id,
            'permission_type': 'leave',
            'session_type': 'full_day',
            'start_date': date.today() + timedelta(days=3),
            'end_date': date.today() + timedelta(days=5),
            'reason': 'Attending National Education Conference as guest speaker.',
        })

        self.assertTrue(perm.name.startswith('PERM/'))
        self.assertEqual(perm.state, 'draft')
        self.assertEqual(perm.applicant_type, 'teacher')
        self.assertEqual(perm.applicant_name, self.teacher_1.name)
        self.assertEqual(perm.duration_days, 2.0)
        self.assertIn(perm.id, self.teacher_1.permission_ids.ids)
        self.assertGreaterEqual(self.teacher_1.permission_count, 1)

    def test_09_teacher_cannot_approve_teacher_permission(self):
        """Teachers cannot approve teacher permission requests. Only School Administrator can."""
        perm = self.Permission.with_user(self.teacher_user_1).create({
            'applicant_type': 'teacher',
            'teacher_id': self.teacher_1.id,
            'permission_type': 'sick',
            'start_date': date.today() + timedelta(days=1),
            'end_date': date.today() + timedelta(days=1),
            'reason': 'Undergoing minor surgery.',
        })

        # Self-approval by the applicant teacher must fail
        with self.assertRaises(UserError):
            perm.with_user(self.teacher_user_1).action_approve()

        # Approval by another teacher must also fail (only admin can approve teacher requests)
        with self.assertRaises(UserError):
            perm.with_user(self.teacher_user_2).action_approve()

    def test_10_admin_approves_teacher_permission(self):
        """School Admin approves teacher permission request."""
        perm = self.Permission.with_user(self.teacher_user_1).create({
            'applicant_type': 'teacher',
            'teacher_id': self.teacher_1.id,
            'permission_type': 'leave',
            'start_date': date.today() + timedelta(days=2),
            'end_date': date.today() + timedelta(days=4),
            'reason': 'Personal academic leave.',
        })

        # Admin approves
        perm.with_user(self.admin_user).action_approve()

        self.assertEqual(perm.state, 'approved')
        self.assertEqual(perm.approved_by.id, self.admin_user.id)
        self.assertEqual(perm.approver_role, 'admin')
        self.assertTrue(perm.approval_date)

    def test_11_teacher_cannot_see_other_teacher_permission(self):
        """Teacher 2 cannot view Teacher 1's private permission/leave request."""
        perm_1 = self.Permission.with_user(self.teacher_user_1).create({
            'applicant_type': 'teacher',
            'teacher_id': self.teacher_1.id,
            'permission_type': 'sick',
            'start_date': date.today() + timedelta(days=2),
            'end_date': date.today() + timedelta(days=2),
            'reason': 'Confidential medical leave.',
        })

        visible_perms = self.Permission.with_user(self.teacher_user_2).search([('id', '=', perm_1.id)])
        self.assertFalse(visible_perms, "Teacher 2 should not see Teacher 1's leave request.")

    def test_12_teacher_affected_timetable_computation(self):
        """When teacher has scheduled timetables during leave period, affected sessions are computed."""
        # Create test class & subject
        test_class = self.Class.create({'name': 'Class Perm Test', 'room': 'Room 101'})
        test_subject = self.Subject.create({'name': 'Science Perm Test', 'code': 'SCI_PT'})

        # Find day of week for tomorrow
        target_date = date.today() + timedelta(days=1)
        target_day_str = str(target_date.weekday())

        # Create timetable slot for teacher_1 on that day
        slot = self.Timetable.create({
            'class_id': test_class.id,
            'teacher_id': self.teacher_1.id,
            'subject_id': test_subject.id,
            'day_of_week': target_day_str,
            'period': 'p1',
            'start_time': 8.0,
            'end_time': 9.0,
            'room': 'Lab 1',
        })

        perm = self.Permission.with_user(self.teacher_user_1).create({
            'applicant_type': 'teacher',
            'teacher_id': self.teacher_1.id,
            'permission_type': 'leave',
            'start_date': target_date,
            'end_date': target_date,
            'reason': 'Family emergency.',
        })

        self.assertIn(slot.id, perm.affected_timetable_ids.ids)
        self.assertGreaterEqual(perm.affected_timetable_count, 1)

    def test_13_admin_rejects_teacher_permission(self):
        """Admin can reject teacher permission request with wizard and reason."""
        perm = self.Permission.with_user(self.teacher_user_1).create({
            'applicant_type': 'teacher',
            'teacher_id': self.teacher_1.id,
            'permission_type': 'leave',
            'start_date': date.today() + timedelta(days=7),
            'end_date': date.today() + timedelta(days=8),
            'reason': 'Conference attendance.',
        })

        wizard = self.RejectWizard.with_user(self.admin_user).create({
            'permission_id': perm.id,
            'rejection_reason': 'Exam period, coverage unavailable for classes.',
        })
        wizard.action_confirm_reject()

        self.assertEqual(perm.state, 'rejected')
        self.assertEqual(perm.approved_by.id, self.admin_user.id)
        self.assertEqual(perm.rejection_reason, 'Exam period, coverage unavailable for classes.')
