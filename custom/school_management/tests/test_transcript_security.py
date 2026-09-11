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
