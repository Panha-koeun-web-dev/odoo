from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields


class TestTranscriptSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Certificate = cls.env['school.certificate']
        cls.Student = cls.env['school.student']

        cls.student = cls.Student.create({
            'name': 'Enrolled Student A',
            'student_id': 'STU_SEC_A',
            'gender': 'male',
            'date_of_birth': fields.Date.from_string('2007-01-01'),
            'email': 'student_sec_test_a@example.com',
        })
        cls.student.action_create_user()
        cls.student_user = cls.student.user_id

        cls.other_student = cls.Student.create({
            'name': 'Enrolled Student B',
            'student_id': 'STU_SEC_B',
            'gender': 'female',
            'date_of_birth': fields.Date.from_string('2007-02-02'),
            'email': 'student_sec_test_b@example.com',
        })
        cls.other_student.action_create_user()
        cls.other_user = cls.other_student.user_id

        cls.admin_cert = cls.Certificate.create({
            'student_id': cls.student.id,
            'certificate_type': 'transcript',
            'term': 'semester_1',
            'academic_year': '2025-2026',
            'status': 'issued',
        })

    def test_student_cannot_create_transcript(self):
        """Ensure students are blocked from creating transcripts."""
        with self.assertRaises(UserError):
            self.Certificate.with_user(self.student_user).create({
                'student_id': self.student.id,
                'certificate_type': 'transcript',
                'term': 'semester_2',
            })

    def test_student_cannot_write_transcript(self):
        """Ensure students are blocked from modifying transcripts."""
        with self.assertRaises(UserError):
            self.admin_cert.with_user(self.student_user).write({
                'status': 'draft',
                'notes': 'Unauthorized update',
            })

    def test_student_cannot_delete_transcript(self):
        """Ensure students are blocked from deleting transcripts."""
        with self.assertRaises(UserError):
            self.admin_cert.with_user(self.student_user).unlink()

    def test_student_cannot_view_other_student_transcript(self):
        """Ensure student record rules prevent seeing other students' transcripts."""
        other_cert = self.Certificate.create({
            'student_id': self.other_student.id,
            'certificate_type': 'transcript',
            'term': 'semester_1',
            'academic_year': '2025-2026',
            'status': 'issued',
        })

        visible_certs = self.Certificate.with_user(self.student_user).search([('id', '=', other_cert.id)])
        self.assertFalse(visible_certs, "Student A should not see Student B's transcript record!")

    def test_student_cannot_print_id_card_directly(self):
        """Restricted students cannot directly print official student ID cards without admin."""
        student_as_user = self.student.with_user(self.student_user)
        with self.assertRaises(UserError) as cm:
            student_as_user.action_print_id_card()
        self.assertIn('School Administrator', str(cm.exception))

    def test_print_approval_workflow(self):
        """Test complete workflow for requesting and approving document printing."""
        cert = self.admin_cert
        student_cert = cert.with_user(self.student_user)

        # 1. Initially not requested -> cannot print
        self.assertEqual(cert.print_state, 'not_requested')
        with self.assertRaises(UserError) as cm:
            student_cert.action_print_transcript()
        self.assertIn('submit a request to the admin and wait for approval', str(cm.exception))

        # 2. Student requests print permission
        res = student_cert.action_request_print()
        self.assertEqual(cert.print_state, 'pending')
        self.assertTrue(cert.print_requested_date)
        self.assertIn('admin', res['params']['message'].lower())

        # 3. Still cannot print while pending
        with self.assertRaises(UserError):
            student_cert.action_print_transcript()

        # 4. Admin reviews and approves request
        cert.action_approve_print()
        self.assertEqual(cert.print_state, 'approved')
        self.assertTrue(cert.print_approval_date)

        # 5. Student can now print
        action = student_cert.action_print_transcript()
        self.assertIn('report_name', action)

    def test_print_rejection_workflow(self):
        """Test workflow when admin declines the print request."""
        cert = self.admin_cert
        student_cert = cert.with_user(self.student_user)

        # Student requests print
        student_cert.action_request_print()
        self.assertEqual(cert.print_state, 'pending')

        # Admin declines with reason
        reason = 'Tuition balance remains outstanding.'
        cert.action_reject_print(reason=reason)

        self.assertEqual(cert.print_state, 'rejected')
        self.assertEqual(cert.print_rejection_reason, reason)

        # Student is blocked from printing
        with self.assertRaises(UserError):
            student_cert.action_print_transcript()
