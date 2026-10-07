from datetime import datetime, timedelta, time
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import fields


class TestExamScheduleTimetable(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SchoolClass = cls.env['school.class']
        cls.Teacher = cls.env['school.teacher']
        cls.Subject = cls.env['school.subject']
        cls.Student = cls.env['school.student']
        cls.Exam = cls.env['school.exam']
        cls.Timetable = cls.env['school.timetable']
        cls.Term = cls.env['school.term']
        cls.Assignment = cls.env['school.teaching.assignment']
        cls.Grade = cls.env['school.grade']
        cls.ScheduleWizard = cls.env['school.exam.student.schedule.wizard']

        # Academic Term
        cls.term = cls.Term.create({
            'name': 'Semester 1 2026',
            'academic_year': '2025-2026',
            'term_number': 'term_1',
            'state': 'active',
            'date_start': fields.Date.today() - timedelta(days=30),
            'date_end': fields.Date.today() + timedelta(days=90),
        })

        # Teachers
        cls.teacher_main = cls.Teacher.create({
            'name': 'Master Yoda',
            'email': 'yoda@school.test',
            'employee_id': 'TCH-EXAM-01',
        })
        cls.teacher_sub = cls.Teacher.create({
            'name': 'Obi-Wan Kenobi',
            'email': 'obiwan@school.test',
            'employee_id': 'TCH-EXAM-02',
        })

        # Class
        cls.school_class = cls.SchoolClass.create({
            'name': 'Jedi Academy Grade 10',
            'code': 'JA-10',
            'room': 'Council Chamber 101',
            'current_term_id': cls.term.id,
            'teacher_id': cls.teacher_main.id,
        })

        # Subject
        cls.subject = cls.Subject.create({
            'name': 'Lightsaber Form IV',
            'code': 'LS-401',
            'credits': 4,
        })

        # Teaching assignment: Obi-Wan Kenobi teaches Lightsaber Form IV
        cls.teaching_asg = cls.Assignment.create({
            'class_id': cls.school_class.id,
            'subject_id': cls.subject.id,
            'teacher_id': cls.teacher_sub.id,
            'active': True,
        })

        # Students
        cls.student_1 = cls.Student.create({
            'name': 'Luke Skywalker',
            'gender': 'male',
            'date_of_birth': fields.Date.from_string('2008-01-10'),
            'student_id': 'STU-001',
            'class_id': cls.school_class.id,
        })
        cls.student_2 = cls.Student.create({
            'name': 'Leia Organa',
            'gender': 'female',
            'date_of_birth': fields.Date.from_string('2008-01-10'),
            'student_id': 'STU-002',
            'class_id': cls.school_class.id,
        })

    def test_01_auto_assignment_and_timetable_sync(self):
        """Test auto assignment of supervisor/room/term and automatic master timetable sync."""
        target_day = fields.Date.today() + timedelta(days=5)
        start = datetime.combine(target_day, time(2, 0))
        end = start + timedelta(hours=2)

        # Create exam without explicit teacher, room, term
        exam = self.Exam.create({
            'name': 'Midterm Lightsaber Mastery',
            'class_id': self.school_class.id,
            'subject_id': self.subject.id,
            'start_datetime': start,
            'end_datetime': end,
            'exam_type': 'midterm',
        })

        # Auto-assigned values
        self.assertEqual(exam.term_id, self.term, "Academic term should auto-populate from class.")
        self.assertEqual(exam.room, 'Council Chamber 101', "Room should auto-populate from class.")
        self.assertEqual(exam.teacher_id, self.teacher_sub, "Supervisor should auto-populate from teaching assignment.")

        # Timetable session auto-created
        self.assertTrue(exam.timetable_id, "Timetable session must be synchronized automatically.")
        timetable = exam.timetable_id
        self.assertTrue(timetable.is_exam, "Timetable session must have is_exam=True.")
        self.assertEqual(timetable.schedule_status, 'exam', "Timetable status must be 'exam'.")
        self.assertEqual(timetable.color, 9, "Exam timetable color should be 9.")
        self.assertIn('[EXAM]', timetable.display_name, "Timetable display name must include [EXAM] prefix.")
        self.assertEqual(timetable.teacher_id, self.teacher_sub)
        self.assertEqual(timetable.room, 'Council Chamber 101')

    def test_02_timetable_sync_lifecycle(self):
        """Test that updating exam time/room updates the timetable and cancelling removes it."""
        target_day = fields.Date.today() + timedelta(days=6)
        start = datetime.combine(target_day, time(2, 0))
        end = start + timedelta(hours=2)

        exam = self.Exam.create({
            'name': 'Final Strategy Exam',
            'class_id': self.school_class.id,
            'subject_id': self.subject.id,
            'teacher_id': self.teacher_main.id,
            'room': 'Main Auditorium',
            'start_datetime': start,
            'end_datetime': end,
        })

        timetable = exam.timetable_id
        self.assertTrue(timetable)
        self.assertEqual(timetable.room, 'Main Auditorium')

        # Update room and duration
        new_end = start + timedelta(hours=3)
        exam.write({
            'room': 'Simulation Room B',
            'end_datetime': new_end,
        })
        self.assertEqual(timetable.room, 'Simulation Room B')
        self.assertEqual(timetable.end_datetime, new_end)

        # Cancel exam -> Timetable session should be cleaned up
        exam.action_cancel_exam()
        self.assertFalse(exam.timetable_id, "Cancelling exam should remove timetable session.")

        # Reset to draft and scheduled -> Timetable session re-created
        exam.action_reset_draft()
        exam.action_set_scheduled()
        self.assertTrue(exam.timetable_id, "Re-scheduling exam must recreate master timetable session.")

    def test_03_conflict_prevention(self):
        """Test validation constraints preventing room, teacher, and class conflicts."""
        target_day = fields.Date.today() + timedelta(days=7)
        start1 = datetime.combine(target_day, time(2, 0))
        end1 = start1 + timedelta(hours=2)

        # Create base exam
        self.Exam.create({
            'name': 'Exam Alpha',
            'class_id': self.school_class.id,
            'subject_id': self.subject.id,
            'teacher_id': self.teacher_main.id,
            'room': 'Hall 100',
            'start_datetime': start1,
            'end_datetime': end1,
        })

        # Another class for room/teacher testing
        class_2 = self.SchoolClass.create({
            'name': 'Jedi Academy Grade 11',
            'code': 'JA-11',
        })

        overlap_start = start1 + timedelta(minutes=30)
        overlap_end = end1 + timedelta(minutes=30)

        # 1. Room collision
        with self.assertRaises(ValidationError):
            self.Exam.create({
                'name': 'Exam Beta - Room Conflict',
                'class_id': class_2.id,
                'subject_id': self.subject.id,
                'teacher_id': self.teacher_sub.id,
                'room': 'Hall 100',
                'start_datetime': overlap_start,
                'end_datetime': overlap_end,
            })

        # 2. Teacher supervisor collision
        with self.assertRaises(ValidationError):
            self.Exam.create({
                'name': 'Exam Gamma - Teacher Conflict',
                'class_id': class_2.id,
                'subject_id': self.subject.id,
                'teacher_id': self.teacher_main.id,
                'room': 'Different Hall 200',
                'start_datetime': overlap_start,
                'end_datetime': overlap_end,
            })

        # 3. Class collision
        with self.assertRaises(ValidationError):
            self.Exam.create({
                'name': 'Exam Delta - Class Conflict',
                'class_id': self.school_class.id,
                'subject_id': self.subject.id,
                'teacher_id': self.teacher_sub.id,
                'room': 'Different Hall 300',
                'start_datetime': overlap_start,
                'end_datetime': overlap_end,
            })

        # 4. Invalid datetimes (start >= end)
        with self.assertRaises(ValidationError):
            self.Exam.create({
                'name': 'Exam Epsilon - Bad Dates',
                'class_id': class_2.id,
                'subject_id': self.subject.id,
                'teacher_id': self.teacher_sub.id,
                'room': 'Different Hall 400',
                'start_datetime': end1,
                'end_datetime': start1,
            })

    def test_04_student_population_and_custom_slots(self):
        """Test populating students and applying specific custom time slots."""
        target_day = fields.Date.today() + timedelta(days=8)
        start = datetime.combine(target_day, time(1, 0))
        end = start + timedelta(hours=2)

        exam = self.Exam.create({
            'name': 'Physics Assessment',
            'class_id': self.school_class.id,
            'subject_id': self.subject.id,
            'teacher_id': self.teacher_sub.id,
            'room': 'Lab 1',
            'start_datetime': start,
            'end_datetime': end,
        })

        # Populate students
        exam.action_populate_students()
        self.assertEqual(len(exam.grade_ids), 2)
        self.assertIn(self.student_1.id, exam.grade_ids.mapped('student_id.id'))
        self.assertIn(self.student_2.id, exam.grade_ids.mapped('student_id.id'))

        # Timetable session enrolled students synced
        self.assertEqual(set(exam.timetable_id.student_ids.ids), {self.student_1.id, self.student_2.id})

        # Check teacher_id related field on grade lines
        grade_luke = exam.grade_ids.filtered(lambda g: g.student_id == self.student_1)
        self.assertEqual(grade_luke.teacher_id, self.teacher_sub)

        # Custom slot wizard for Luke Skywalker
        custom_start = start + timedelta(hours=3)
        custom_end = custom_start + timedelta(hours=2)
        wizard = self.ScheduleWizard.create({
            'exam_id': exam.id,
            'grade_ids': [(6, 0, grade_luke.ids)],
            'specific_start_datetime': custom_start,
            'specific_end_datetime': custom_end,
            'room': 'Private Lab B',
            'schedule_notes': 'Rescheduled for Jedi Knight Tournament',
        })
        wizard.action_apply_schedule()

        self.assertTrue(grade_luke.is_custom_schedule)
        self.assertEqual(grade_luke.exam_datetime, custom_start)
        self.assertEqual(grade_luke.room, 'Private Lab B')

        # Reset back to default exam schedule
        wizard.action_reset_to_exam_schedule()
        self.assertFalse(grade_luke.is_custom_schedule)
        self.assertEqual(grade_luke.exam_datetime, exam.start_datetime)
        self.assertEqual(grade_luke.room, exam.room)

    def test_05_teacher_and_student_perspectives(self):
        """Test supervisor duties count on teacher and scheduled exam count on student."""
        target_day = fields.Date.today() + timedelta(days=9)
        start = datetime.combine(target_day, time(2, 0))
        end = start + timedelta(hours=2)

        exam = self.Exam.create({
            'name': 'Galactic History Exam',
            'class_id': self.school_class.id,
            'subject_id': self.subject.id,
            'teacher_id': self.teacher_main.id,
            'start_datetime': start,
            'end_datetime': end,
        })
        exam.action_populate_students()

        # Teacher perspective
        self.teacher_main._compute_teacher_exam_stats()
        self.assertGreaterEqual(self.teacher_main.exam_count, 1)
        action_teacher = self.teacher_main.action_view_supervised_exams()
        self.assertEqual(action_teacher['res_model'], 'school.exam')
        self.assertEqual(action_teacher['domain'], [('teacher_id', '=', self.teacher_main.id)])

        # Student perspective
        self.student_1._compute_student_exam_stats()
        self.assertGreaterEqual(self.student_1.exam_count, 1)
        self.assertGreaterEqual(self.student_1.upcoming_exam_count, 1)
        action_student = self.student_1.action_view_student_exams()
        self.assertEqual(action_student['res_model'], 'school.grade')
        self.assertEqual(action_student['domain'], [('student_id', '=', self.student_1.id)])
