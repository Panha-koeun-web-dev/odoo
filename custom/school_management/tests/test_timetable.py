from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import fields
from datetime import datetime, timedelta
import pytz


class TestSchoolTimetable(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SchoolClass = cls.env['school.class']
        cls.Teacher = cls.env['school.teacher']
        cls.Subject = cls.env['school.subject']
        cls.Student = cls.env['school.student']
        cls.Timetable = cls.env['school.timetable']

        cls.class_a = cls.SchoolClass.create({
            'name': 'Grade 10-A',
            'code': 'G10-A',
            'payment_year': '2025-2026',
        })
        cls.class_b = cls.SchoolClass.create({
            'name': 'Grade 10-B',
            'code': 'G10-B',
            'payment_year': '2025-2026',
        })

        cls.teacher_1 = cls.Teacher.create({
            'name': 'Dr. Alan Turing',
            'email': 'alan.turing@school.example.com',
            'employee_id': 'TCH-001',
        })
        cls.teacher_2 = cls.Teacher.create({
            'name': 'Prof. Ada Lovelace',
            'email': 'ada.lovelace@school.example.com',
            'employee_id': 'TCH-002',
        })

        cls.subject_math = cls.Subject.create({
            'name': 'Mathematics',
            'code': 'MATH-101',
        })
        cls.subject_physics = cls.Subject.create({
            'name': 'Physics',
            'code': 'PHYS-101',
        })

        cls.student = cls.Student.create({
            'name': 'Grace Hopper',
            'student_id': 'STU-GH-001',
            'date_of_birth': fields.Date.from_string('2008-05-15'),
            'class_id': cls.class_a.id,
            'gender': 'female',
        })

    def test_01_timetable_creation_and_autocalc(self):
        """Test creating a timetable record with period preset computes correct times and datetimes."""
        slot = self.Timetable.create({
            'class_id': self.class_a.id,
            'subject_id': self.subject_math.id,
            'teacher_id': self.teacher_1.id,
            'day_of_week': '0',  # Monday
            'period': 'p1',      # 08:00 - 09:00
            'room': 'Lab 101',
        })

        self.assertTrue(slot.id)
        self.assertEqual(slot.start_time, 8.0)
        self.assertEqual(slot.end_time, 9.0)
        self.assertEqual(slot.period_short, 'Period 1')
        self.assertEqual(slot.time_display, '08:00 - 09:00')
        self.assertTrue(slot.start_datetime)
        self.assertTrue(slot.end_datetime)
        self.assertTrue(slot.start_datetime < slot.end_datetime)
        self.assertIn('Mathematics', slot.name)
        self.assertIn('Grade 10-A', slot.name)

    def test_02_calendar_drag_sync(self):
        """Test modifying start_datetime and end_datetime updates day_of_week, start_time, and end_time."""
        # Assume UTC anchor for testing
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        now = datetime.now(tz)
        # Find next Tuesday at 10:00 AM
        days_ahead = (1 - now.weekday()) % 7  # 1 is Tuesday
        tuesday = (now + timedelta(days=days_ahead)).replace(hour=10, minute=0, second=0, microsecond=0)
        start_utc = tz.localize(tuesday.replace(tzinfo=None)).astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = start_utc + timedelta(hours=1, minutes=30)

        slot = self.Timetable.create({
            'class_id': self.class_b.id,
            'subject_id': self.subject_physics.id,
            'teacher_id': self.teacher_2.id,
            'start_datetime': start_utc,
            'end_datetime': end_utc,
            'room': 'Room 202',
        })

        self.assertEqual(slot.day_of_week, '1')  # Tuesday
        self.assertAlmostEqual(slot.start_time, 10.0, places=1)
        self.assertAlmostEqual(slot.end_time, 11.5, places=1)

    def test_03_teacher_conflict_prevention(self):
        """Test teacher collision constraint prevents assigning the same teacher to two classes at the same time."""
        self.Timetable.create({
            'class_id': self.class_a.id,
            'subject_id': self.subject_math.id,
            'teacher_id': self.teacher_1.id,
            'day_of_week': '2',  # Wednesday
            'period': 'p2',      # 09:45 - 11:15
            'room': 'Room 101',
        })

        # Teacher 1 cannot teach Class B at the same time
        with self.assertRaises(ValidationError):
            self.Timetable.create({
                'class_id': self.class_b.id,
                'subject_id': self.subject_physics.id,
                'teacher_id': self.teacher_1.id,
                'day_of_week': '2',  # Wednesday
                'period': 'p2',      # 09:45 - 11:15
                'room': 'Room 102',
            })

    def test_04_class_conflict_prevention(self):
        """Test class collision constraint prevents assigning two teachers/subjects to the same class at the same time."""
        self.Timetable.create({
            'class_id': self.class_a.id,
            'subject_id': self.subject_math.id,
            'teacher_id': self.teacher_1.id,
            'day_of_week': '3',  # Thursday
            'period': 'p3',      # 11:30 - 13:00
            'room': 'Room 101',
        })

        # Class A cannot have Teacher 2 / Physics at the same time
        with self.assertRaises(ValidationError):
            self.Timetable.create({
                'class_id': self.class_a.id,
                'subject_id': self.subject_physics.id,
                'teacher_id': self.teacher_2.id,
                'day_of_week': '3',  # Thursday
                'period': 'p3',      # 11:30 - 13:00
                'room': 'Room 102',
            })

    def test_05_room_conflict_prevention(self):
        """Test room collision constraint prevents two classes from using the same room at the same time."""
        self.Timetable.create({
            'class_id': self.class_a.id,
            'subject_id': self.subject_math.id,
            'teacher_id': self.teacher_1.id,
            'day_of_week': '4',  # Friday
            'period': 'p4',      # 13:30 - 15:00
            'room': 'Auditorium A',
        })

        # Class B cannot use Auditorium A at the same time
        with self.assertRaises(ValidationError):
            self.Timetable.create({
                'class_id': self.class_b.id,
                'subject_id': self.subject_physics.id,
                'teacher_id': self.teacher_2.id,
                'day_of_week': '4',  # Friday
                'period': 'p4',      # 13:30 - 15:00
                'room': 'Auditorium A',
            })

    def test_06_smart_relations_and_actions(self):
        """Test Class, Teacher, and Student smart actions and timetable navigation."""
        slot = self.Timetable.create({
            'class_id': self.class_a.id,
            'subject_id': self.subject_math.id,
            'teacher_id': self.teacher_1.id,
            'day_of_week': '5',  # Saturday
            'period': 'p1',
            'room': 'Room 101',
        })

        # Class stat & action
        self.class_a._compute_timetable_count()
        self.assertGreaterEqual(self.class_a.timetable_count, 1)
        class_action = self.class_a.action_view_timetable()
        self.assertEqual(class_action['res_model'], 'school.timetable')
        self.assertIn(('class_id', '=', self.class_a.id), class_action['domain'])

        # Teacher stat & action
        self.teacher_1._compute_timetable_count()
        self.assertGreaterEqual(self.teacher_1.timetable_count, 1)
        teacher_action = self.teacher_1.action_view_timetable()
        self.assertEqual(teacher_action['res_model'], 'school.timetable')
        self.assertIn(('teacher_id', '=', self.teacher_1.id), teacher_action['domain'])

        # Student timetable navigation action
        student_action = self.student.action_view_class_timetable()
        self.assertEqual(student_action['res_model'], 'school.timetable')
        self.assertIn(('class_id', '=', self.class_a.id), student_action['domain'])

        # Timetable to class students action
        class_students_action = slot.action_view_class_students()
        self.assertEqual(class_students_action['res_model'], 'school.student')
        self.assertIn(('class_id', '=', self.class_a.id), class_students_action['domain'])
