# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import date
from odoo import fields


class TestTeacherStudentVisibility(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_admin = cls.env.ref('school_management.group_school_admin')
        cls.group_teacher = cls.env.ref('school_management.group_school_teacher')
        cls.group_internal = cls.env.ref('base.group_user')

        # Create Teacher User & Teacher Record
        cls.teacher_user = cls.env['res.users'].create({
            'name': 'Teacher John Doe',
            'login': 'teacher_john_doe@school.com',
            'email': 'teacher_john_doe@school.com',
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_teacher.id])],
        })

        cls.teacher = cls.env['school.teacher'].create({
            'name': 'Teacher John Doe',
            'employee_id': 'TCH-999',
            'email': 'teacher_john_doe@school.com',
            'user_id': cls.teacher_user.id,
        })

        # Create Other Teacher
        cls.other_teacher_user = cls.env['res.users'].create({
            'name': 'Teacher Other',
            'login': 'teacher_other@school.com',
            'email': 'teacher_other@school.com',
            'group_ids': [(6, 0, [cls.group_internal.id, cls.group_teacher.id])],
        })
        cls.other_teacher = cls.env['school.teacher'].create({
            'name': 'Teacher Other',
            'employee_id': 'TCH-888',
            'email': 'teacher_other@school.com',
            'user_id': cls.other_teacher_user.id,
        })

        # Create Subjects
        cls.subject_math = cls.env['school.subject'].create({
            'name': 'Mathematics 101',
            'code': 'MATH101',
        })
        cls.subject_science = cls.env['school.subject'].create({
            'name': 'Science 101',
            'code': 'SCI101',
        })

        # Create Classes
        cls.class_a = cls.env['school.class'].create({
            'name': 'Class 10-A',
            'teacher_id': cls.teacher.id,  # John is class teacher
        })
        cls.class_b = cls.env['school.class'].create({
            'name': 'Class 10-B',
            'teacher_id': cls.other_teacher.id,  # Other is class teacher
        })

        # Create Students
        cls.student_a = cls.env['school.student'].create({
            'name': 'Alice Smith',
            'student_id': 'STU-001',
            'gender': 'female',
            'date_of_birth': date(2008, 1, 15),
            'class_id': cls.class_a.id,
            'study_status': 'studying',
        })

        cls.student_b = cls.env['school.student'].create({
            'name': 'Bob Jones',
            'student_id': 'STU-002',
            'gender': 'male',
            'date_of_birth': date(2008, 5, 20),
            'class_id': cls.class_b.id,
            'study_status': 'studying',
        })

        cls.student_c = cls.env['school.student'].create({
            'name': 'Charlie Brown',
            'student_id': 'STU-003',
            'gender': 'male',
            'date_of_birth': date(2008, 8, 10),
            'class_id': cls.class_b.id,
            'study_status': 'studying',
        })

        cls.student_unrelated = cls.env['school.student'].create({
            'name': 'Daisy Unrelated',
            'student_id': 'STU-004',
            'gender': 'female',
            'date_of_birth': date(2008, 12, 1),
            'class_id': cls.class_b.id,
            'study_status': 'studying',
        })

    def test_01_taught_students_aggregation_all_sources(self):
        """Verify teacher aggregates students from class, assignment, timetable, and study subject."""
        # 1. student_a is in class_a where teacher is class teacher
        taught_ids = self.teacher._get_all_taught_student_ids()
        self.assertIn(self.student_a.id, taught_ids)
        self.assertNotIn(self.student_b.id, taught_ids)

        # 2. Teaching assignment for Class B
        asg = self.env['school.teaching.assignment'].create({
            'teacher_id': self.teacher.id,
            'subject_id': self.subject_math.id,
            'class_id': self.class_b.id,
            'weekly_hours': 4.0,
            'weekly_sessions': 2,
        })
        taught_ids = self.teacher._get_all_taught_student_ids()
        self.assertIn(self.student_a.id, taught_ids)
        self.assertIn(self.student_b.id, taught_ids)
        self.assertIn(self.student_c.id, taught_ids)

        # Deactivate assignment
        asg.active = False
        taught_ids = self.teacher._get_all_taught_student_ids()
        self.assertNotIn(self.student_b.id, taught_ids)
        asg.unlink()

        # 3. Timetable session with student_b directly
        tt = self.env['school.timetable'].create({
            'teacher_id': self.teacher.id,
            'subject_id': self.subject_science.id,
            'student_id': self.student_b.id,
            'day_of_week': '0',
            'start_time': 9.0,
            'end_time': 10.5,
        })
        taught_ids = self.teacher._get_all_taught_student_ids()
        self.assertIn(self.student_b.id, taught_ids)
        self.assertNotIn(self.student_c.id, taught_ids)
        tt.unlink()

        # 4. Student subject for student_c
        ss = self.env['school.student.subject'].create({
            'student_id': self.student_c.id,
            'subject_id': self.subject_science.id,
            'teacher_id': self.teacher.id,
            'weekly_hours': 3.0,
            'weekly_sessions': 2,
            'study_status': 'active',
        })
        taught_ids = self.teacher._get_all_taught_student_ids()
        self.assertIn(self.student_c.id, taught_ids)
        self.assertNotIn(self.student_unrelated.id, taught_ids)
        ss.unlink()

    def test_02_teacher_search_filter_is_taught_by_current_teacher(self):
        """Verify search filter [('is_taught_by_current_teacher', '=', True)] returns only taught students."""
        # Setup: teacher teaches student_a (via class) and student_b (via study subject)
        ss = self.env['school.student.subject'].create({
            'student_id': self.student_b.id,
            'subject_id': self.subject_math.id,
            'teacher_id': self.teacher.id,
            'weekly_hours': 2.0,
            'weekly_sessions': 1,
            'study_status': 'active',
        })

        StudentAsTeacher = self.env['school.student'].with_user(self.teacher_user)
        taught_students = StudentAsTeacher.search([('is_taught_by_current_teacher', '=', True)])

        self.assertIn(self.student_a, taught_students)
        self.assertIn(self.student_b, taught_students)
        self.assertNotIn(self.student_c, taught_students)
        self.assertNotIn(self.student_unrelated, taught_students)

        not_taught_students = StudentAsTeacher.search([('is_taught_by_current_teacher', '=', False)])
        self.assertNotIn(self.student_a, not_taught_students)
        self.assertNotIn(self.student_b, not_taught_students)
        self.assertIn(self.student_c, not_taught_students)
        self.assertIn(self.student_unrelated, not_taught_students)

        ss.unlink()

    def test_03_teacher_can_read_all_student_data(self):
        """Verify teacher user can read all student fields including payments, attendance, grades, and subjects."""
        # Create year payment
        payment = self.env['school.student.year.payment'].create({
            'student_id': self.student_a.id,
            'year': '2026-2027',
            'year_start': date(2026, 9, 1),
            'year_end': date(2027, 6, 30),
            'installment_1_amount': 500.0,
            'installment_1_paid_amount': 500.0,
            'installment_2_amount': 500.0,
            'installment_2_paid_amount': 0.0,
        })

        # Create attendance
        attendance = self.env['school.attendance'].create({
            'student_id': self.student_a.id,
            'date': date.today(),
            'status': 'present',
        })

        # Create grade
        exam = self.env['school.exam'].create({
            'name': 'Midterm Exam 2026',
            'start_datetime': fields.Datetime.now(),
            'class_id': self.class_a.id,
            'subject_id': self.subject_math.id,
            'total_marks': 100,
            'passing_marks': 50,
        })
        grade = self.env['school.grade'].create({
            'student_id': self.student_a.id,
            'exam_id': exam.id,
            'marks_obtained': 88.0,
        })

        # Read as teacher
        student_as_teacher = self.student_a.with_user(self.teacher_user)

        # 1. Profile information
        self.assertEqual(student_as_teacher.name, 'Alice Smith')
        self.assertEqual(student_as_teacher.student_id, 'STU-001')
        self.assertEqual(student_as_teacher.study_status, 'studying')

        # 2. Attendance information
        self.assertGreater(student_as_teacher.attendance_count, 0)
        self.assertIn(attendance, student_as_teacher.attendance_ids)

        # 3. Grade information
        self.assertGreater(student_as_teacher.grade_count, 0)
        self.assertIn(grade, student_as_teacher.grade_ids)
        self.assertAlmostEqual(student_as_teacher.average_score, 89.2)
        self.assertAlmostEqual(student_as_teacher.exam_average_score, 88.0)
        self.assertGreater(student_as_teacher.gpa, 0.0)

        # 4. Financial & Year Payment information
        self.assertIn(payment, student_as_teacher.year_payment_ids)
        self.assertEqual(student_as_teacher.total_year_amount, 1000.0)
        self.assertEqual(student_as_teacher.total_year_paid, 500.0)
        self.assertEqual(student_as_teacher.total_year_balance, 500.0)

        # Verify teacher can read year payment record directly
        payment_as_teacher = payment.with_user(self.teacher_user)
        self.assertEqual(payment_as_teacher.total_amount, 1000.0)
        self.assertEqual(payment_as_teacher.total_balance, 500.0)

    def test_04_teacher_stat_buttons_and_actions(self):
        """Verify teacher actions return correct views and student domains."""
        self.teacher._compute_teaching_stats()
        action_taught = self.teacher.action_view_students_taught()
        self.assertIn(self.student_a.id, action_taught['domain'][0][2])

        action_students = self.teacher.action_view_students()
        self.assertIn(self.student_a.id, action_students['domain'][0][2])
