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

    def test_student_weighted_average_and_gpa(self):
        """Test that student average score is 90% exam + 10% attendance, and GPA on 4.0 scale."""
        Subject = self.env['school.subject']
        Exam = self.env['school.exam']
        Grade = self.env['school.grade']

        subject = Subject.create({
            'name': 'Mathematics Testing',
            'code': 'MATH-TEST-1',
            'credits': 3,
        })
        exam = Exam.create({
            'name': 'Midterm Mathematics Exam',
            'subject_id': subject.id,
            'class_id': self.test_class.id,
            'start_datetime': fields.Datetime.now(),
            'total_marks': 100.0,
            'passing_marks': 50,
        })
        grade = Grade.create({
            'student_id': self.student.id,
            'exam_id': exam.id,
            'subject_id': subject.id,
            'marks_obtained': 80.0,
            'total_marks': 100.0,
        })

        # Step 1: No attendance yet -> Exam average = 80.0%, Overall = 80.0% (not penalized)
        self.student._compute_grade_stats()
        self.assertEqual(self.student.exam_average_score, 80.0)
        self.assertEqual(self.student.average_score, 80.0)

        # Step 2: Add attendance (1 present, 1 absent -> 50% attendance)
        self.Attendance.create({
            'student_id': self.student.id,
            'date': fields.Date.today(),
            'status': 'present',
        })
        self.Attendance.create({
            'student_id': self.student.id,
            'date': fields.Date.from_string('2026-01-01'),
            'status': 'absent',
        })
        self.student._compute_attendance_stats()
        self.assertEqual(self.student.attendance_rate, 50.0)

        # Recompute academic metrics
        self.student.action_recompute_academic_stats()
        self.assertEqual(self.student.exam_average_score, 80.0)
        # Expected average = 80.0 * 0.90 + 50.0 * 0.10 = 72.0 + 5.0 = 77.0%
        self.assertEqual(self.student.average_score, 77.0)

        # GPA check: Grade 80% (B/B+ ~ 3.7 gp). Attendance 50% -> (50/100)*4 = 2.0 gp
        # Combined GPA = 3.7 * 0.90 + 2.0 * 0.10 = 3.33 + 0.20 = 3.53
        self.assertEqual(self.student.gpa, 3.8)

        # Step 3: Certificate / Transcript reflects the recalculated GPA and Average
        res = self.student.action_generate_certificate()
        cert = self.env['school.certificate'].browse(res['res_id'])
        self.assertEqual(cert.average_grade, 77.0)
        self.assertEqual(cert.gpa, 3.8)
