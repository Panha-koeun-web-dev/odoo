from odoo.tests.common import TransactionCase
from odoo import fields


class TestSchoolStudent(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Student = cls.env['school.student']
        cls.Attendance = cls.env['school.attendance']
        cls.SchoolClass = cls.env['school.class']

        cls.test_class = cls.SchoolClass.create({
            'name': 'Test Class 101',
            'code': 'TC-101',
            'payment_year': '2025-2026',
        })

        cls.student = cls.Student.create({
            'name': 'Test Student One',
            'student_id': 'STU_TEST_001',
            'date_of_birth': fields.Date.from_string('2008-05-15'),
            'gender': 'male',
            'email': 'test.student.one@example.com',
            'class_id': cls.test_class.id,
        })

    def test_student_creation(self):
        """Test student record is created with expected attributes."""
        self.assertTrue(self.student.id)
        self.assertEqual(self.student.name, 'Test Student One')
        self.assertEqual(self.student.class_id.id, self.test_class.id)
        self.assertTrue(self.student.age > 0)

    def test_student_attendance_stats(self):
        """Test student attendance calculation."""
        self.Attendance.create({
            'student_id': self.student.id,
            'date': fields.Date.from_string('2026-01-10'),
            'status': 'present',
        })
        self.Attendance.create({
            'student_id': self.student.id,
            'date': fields.Date.from_string('2026-01-11'),
            'status': 'absent',
        })
        self.student._compute_attendance_stats()
        self.assertEqual(self.student.attendance_count, 2)
        self.assertEqual(self.student.present_count, 1)
        self.assertEqual(self.student.absent_count, 1)
        self.assertEqual(self.student.attendance_rate, 50.0)

    def test_action_generate_certificate(self):
        """Test transcript generation action."""
        res = self.student.action_generate_certificate()
        self.assertEqual(res.get('res_model'), 'school.certificate')
        self.assertTrue(res.get('res_id'))
