from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import fields
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


class TestSchoolTermSchedule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Term = cls.env['school.term']
        cls.SchoolClass = cls.env['school.class']
        cls.Teacher = cls.env['school.teacher']
        cls.Subject = cls.env['school.subject']
        cls.Student = cls.env['school.student']
        cls.Timetable = cls.env['school.timetable']
        cls.Wizard = cls.env['school.term.schedule.wizard']
        cls.TeachingAssignment = cls.env['school.teaching.assignment']

        cls.teacher_1 = cls.Teacher.create({
            'name': 'Prof. John von Neumann',
            'email': 'john.vonneumann@school.example.com',
            'employee_id': 'TCH-JVN-01',
        })
        cls.teacher_2 = cls.Teacher.create({
            'name': 'Prof. Claude Shannon',
            'email': 'claude.shannon@school.example.com',
            'employee_id': 'TCH-CSH-02',
        })

        cls.subject_math = cls.Subject.create({
            'name': 'Advanced Mathematics',
            'code': 'MATH-201',
        })
        cls.subject_physics = cls.Subject.create({
            'name': 'Applied Physics',
            'code': 'PHYS-201',
        })

        cls.class_alpha = cls.SchoolClass.create({
            'name': 'Year 1 - Section Alpha',
            'code': 'Y1-A',
            'room': 'Hall 101',
            'teacher_id': cls.teacher_1.id,
            'payment_year': '2026-2027',
        })

        cls.student_1 = cls.Student.create({
            'name': 'Katherine Johnson',
            'student_id': 'STU-KJ-01',
            'date_of_birth': date(2007, 8, 26),
            'class_id': cls.class_alpha.id,
            'gender': 'female',
        })

        # Set up teaching assignments
        cls.asg_math = cls.TeachingAssignment.create({
            'teacher_id': cls.teacher_1.id,
            'class_id': cls.class_alpha.id,
            'subject_id': cls.subject_math.id,
            'weekly_hours': 4.0,
            'weekly_sessions': 2,
        })
        cls.asg_physics = cls.TeachingAssignment.create({
            'teacher_id': cls.teacher_2.id,
            'class_id': cls.class_alpha.id,
            'subject_id': cls.subject_physics.id,
            'weekly_hours': 3.0,
            'weekly_sessions': 1,
        })

    def test_01_term_lifecycle_and_autocalc(self):
        """Test term creation: 3-month duration auto-calculation, transitions, and auto-creating next term."""
        term_1 = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
        })

        # Check date_end auto-calculated to 3 months (2026-11-30)
        self.assertEqual(term_1.date_end, date(2026, 11, 30))
        self.assertAlmostEqual(term_1.duration_months, 3.0, places=1)
        self.assertEqual(term_1.state, 'draft')

        # Activate term
        term_1.action_start_term()
        self.assertEqual(term_1.state, 'active')

        # Finish term
        term_1.action_finish_term()
        self.assertEqual(term_1.state, 'finished')

        # Auto-create next term (Term 2)
        res = term_1.action_create_next_term()
        next_term_id = res.get('res_id')
        term_2 = self.Term.browse(next_term_id)

        self.assertTrue(term_2.exists())
        self.assertEqual(term_2.term_number, 'term_2')
        self.assertEqual(term_2.academic_year, '2026-2027')
        self.assertEqual(term_2.date_start, date(2026, 12, 1))
        self.assertEqual(term_2.date_end, date(2027, 2, 28))
        self.assertEqual(term_1.next_term_id, term_2)
        self.assertEqual(term_2.previous_term_id, term_1)

    def test_02_term_schedule_wizard_batch_creation(self):
        """Test planning a full term schedule for a class using pre-fill from curriculum."""
        term_1 = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
            'date_end': date(2026, 11, 30),
            'state': 'active',
        })

        # Launch wizard for Class Alpha and Term 1
        wizard = self.Wizard.create({
            'term_id': term_1.id,
            'class_id': self.class_alpha.id,
            'mode': 'create_slots',
            'schedule_scope': 'single_week',
        })

        # Pre-fill lines from curriculum
        wizard.action_prefill_from_class_curriculum()
        self.assertTrue(len(wizard.line_ids) >= 2, "Should pre-fill lines from teaching assignments")

        # Apply schedule
        action_res = wizard.action_apply_schedule()
        self.assertTrue(action_res)

        # Verify timetable records created
        slots = self.Timetable.search([
            ('term_id', '=', term_1.id),
            ('class_id', '=', self.class_alpha.id),
        ])
        self.assertTrue(len(slots) >= 2)
        self.assertEqual(self.class_alpha.current_term_id, term_1)
        self.assertIn(self.class_alpha, term_1.class_ids)

    def test_03_term_rollover_copy_mode(self):
        """Test rolling over timetable from Term 1 to Term 2 in 1 click."""
        term_1 = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
            'date_end': date(2026, 11, 30),
            'state': 'finished',
        })

        term_2 = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_2',
            'date_start': date(2026, 12, 1),
            'date_end': date(2027, 2, 28),
            'state': 'draft',
            'previous_term_id': term_1.id,
        })

        # Create Term 1 slot
        slot_t1 = self.Timetable.create({
            'term_id': term_1.id,
            'class_id': self.class_alpha.id,
            'teacher_id': self.teacher_1.id,
            'subject_id': self.subject_math.id,
            'subject_ids': [(6, 0, [self.subject_math.id])],
            'day_of_week': '0',  # Monday
            'period': 'p1',
            'start_time': 8.0,
            'end_time': 9.0,
            'room': 'Room 101',
        })

        # Run Wizard in copy_term mode
        wizard = self.Wizard.create({
            'term_id': term_2.id,
            'class_id': self.class_alpha.id,
            'mode': 'copy_term',
            'source_term_id': term_1.id,
            'activate_target_term': True,
            'schedule_scope': 'single_week',
        })
        wizard._onchange_source_term()
        self.assertEqual(wizard.source_session_count, 1)

        wizard.action_apply_schedule()

        # Check Term 2 slots
        slots_t2 = self.Timetable.search([
            ('term_id', '=', term_2.id),
            ('class_id', '=', self.class_alpha.id),
        ])
        self.assertEqual(len(slots_t2), 1)
        self.assertEqual(slots_t2.teacher_id, self.teacher_1)
        self.assertEqual(slots_t2.subject_id, self.subject_math)
        self.assertEqual(slots_t2.day_of_week, '0')
        self.assertEqual(slots_t2.start_time, 8.0)

        # Check Term 2 activated and class current_term updated
        self.assertEqual(term_2.state, 'active')
        self.assertEqual(self.class_alpha.current_term_id, term_2)

    def test_04_scoped_conflict_checking_across_terms(self):
        """Test that identical timetable slots in different 3-month terms do NOT conflict, but same term DOES conflict."""
        term_1 = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
            'date_end': date(2026, 11, 30),
            'state': 'finished',
        })
        term_2 = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_2',
            'date_start': date(2026, 12, 1),
            'date_end': date(2027, 2, 28),
            'state': 'active',
        })

        # Term 1 slot: Monday 8:00-9:00 with Teacher 1
        slot_t1 = self.Timetable.create({
            'term_id': term_1.id,
            'class_id': self.class_alpha.id,
            'teacher_id': self.teacher_1.id,
            'subject_id': self.subject_math.id,
            'subject_ids': [(6, 0, [self.subject_math.id])],
            'day_of_week': '0',
            'period': 'p1',
            'start_time': 8.0,
            'end_time': 9.0,
        })

        # Term 2 slot: Exact same day and time with Teacher 1 - MUST SUCCEED (no false collision)
        slot_t2 = self.Timetable.create({
            'term_id': term_2.id,
            'class_id': self.class_alpha.id,
            'teacher_id': self.teacher_1.id,
            'subject_id': self.subject_math.id,
            'subject_ids': [(6, 0, [self.subject_math.id])],
            'day_of_week': '0',
            'period': 'p1',
            'start_time': 8.0,
            'end_time': 9.0,
        })
        self.assertTrue(slot_t2.exists())

        # Attempt to create conflicting slot within the SAME Term (Term 2) for Teacher 1 - MUST FAIL
        with self.assertRaises(ValidationError):
            self.Timetable.create({
                'term_id': term_2.id,
                'class_id': self.class_alpha.id,
                'teacher_id': self.teacher_1.id,
                'subject_id': self.subject_physics.id,
                'subject_ids': [(6, 0, [self.subject_physics.id])],
                'day_of_week': '0',
                'period': 'p1',
                'start_time': 8.3,
                'end_time': 9.3,
            })

    def test_05_exam_and_certificate_term_integration(self):
        """Test exam and certificate integration with school.term."""
        term_1 = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
            'date_end': date(2026, 11, 30),
            'state': 'active',
        })
        self.class_alpha.current_term_id = term_1

        # Create exam for Class Alpha
        exam = self.env['school.exam'].create({
            'name': 'Midterm Exam - Mathematics',
            'class_id': self.class_alpha.id,
            'subject_id': self.subject_math.id,
            'start_datetime': datetime(2026, 10, 15, 9, 0, 0),
            'total_marks': 100,
        })
        # Check term_id linked to class current_term_id
        self.assertEqual(exam.term_id, term_1)

        # Create certificate with term_id
        cert = self.env['school.certificate'].create({
            'student_id': self.student_1.id,
            'certificate_type': 'transcript',
            'term_id': term_1.id,
            'issue_date': date(2026, 11, 30),
        })
        cert._onchange_term_id()
        self.assertEqual(cert.term, 'term_1')
        self.assertEqual(cert.academic_year, '2026-2027')

    def test_06_monday_to_friday_schedule_generator(self):
        """Test generating full Monday until Friday schedule for a term."""
        term = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
            'date_end': date(2026, 11, 30),
            'state': 'active',
        })

        wizard = self.Wizard.create({
            'term_id': term.id,
            'class_id': self.class_alpha.id,
            'mode': 'create_slots',
            'mon_fri_periods': '4_morning',
            'include_mon': True,
            'include_tue': True,
            'include_wed': True,
            'include_thu': True,
            'include_fri': True,
            'distribute_subjects': True,
        })

        # Generate Monday - Friday schedule
        wizard.action_generate_monday_to_friday()

        # 5 days * 4 periods = 20 sessions
        self.assertEqual(len(wizard.line_ids), 20)

        # Check all 5 weekdays (0, 1, 2, 3, 4) are covered
        days_covered = set(wizard.line_ids.mapped('day_of_week'))
        self.assertEqual(days_covered, {'0', '1', '2', '3', '4'})

        # Check periods are p1, p2, p3, p4
        periods_covered = set(wizard.line_ids.mapped('period'))
        self.assertEqual(periods_covered, {'p1', 'p2', 'p3', 'p4'})

        # Check subjects distributed from class curriculum
        subjects_assigned = wizard.line_ids.mapped('subject_id')
        self.assertIn(self.subject_math, subjects_assigned)
        self.assertIn(self.subject_physics, subjects_assigned)

    def test_07_copy_monday_to_all_weekdays(self):
        """Test duplicating Monday sessions across Tuesday to Friday."""
        term = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
            'date_end': date(2026, 11, 30),
            'state': 'active',
        })

        wizard = self.Wizard.create({
            'term_id': term.id,
            'class_id': self.class_alpha.id,
            'mode': 'create_slots',
            'line_ids': [
                (0, 0, {
                    'day_of_week': '0',  # Monday
                    'period': 'p1',
                    'start_time': 8.0,
                    'end_time': 9.0,
                    'subject_id': self.subject_math.id,
                    'teacher_id': self.teacher_1.id,
                    'room': 'Hall 101',
                }),
                (0, 0, {
                    'day_of_week': '0',  # Monday
                    'period': 'p2',
                    'start_time': 9.25,
                    'end_time': 10.25,
                    'subject_id': self.subject_physics.id,
                    'teacher_id': self.teacher_2.id,
                    'room': 'Hall 101',
                }),
            ]
        })

        wizard.action_copy_monday_to_all_weekdays()

        # Monday had 2 sessions. Duplicating to Tue, Wed, Thu, Fri (+8 sessions) -> total 10 sessions
        self.assertEqual(len(wizard.line_ids), 10)
        days_covered = set(wizard.line_ids.mapped('day_of_week'))
        self.assertEqual(days_covered, {'0', '1', '2', '3', '4'})

    def test_08_clear_all_lines(self):
        """Test clearing all session lines."""
        term = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
            'date_end': date(2026, 11, 30),
        })

        wizard = self.Wizard.create({
            'term_id': term.id,
            'class_id': self.class_alpha.id,
            'mode': 'create_slots',
            'line_ids': [
                (0, 0, {
                    'day_of_week': '0',
                    'period': 'p1',
                    'start_time': 8.0,
                    'end_time': 9.0,
                    'subject_id': self.subject_math.id,
                    'teacher_id': self.teacher_1.id,
                })
            ]
        })
        self.assertEqual(len(wizard.line_ids), 1)

        wizard.action_clear_all_lines()
        self.assertEqual(len(wizard.line_ids), 0)

    def test_09_full_term_multi_week_generation_and_student_stats(self):
        """Test full 3-month calendar generation populates all weeks and integrates with student schedule."""
        term = self.Term.create({
            'academic_year': '2026-2027',
            'term_number': 'term_1',
            'date_start': date(2026, 9, 1),
            'date_end': date(2026, 11, 30),
            'state': 'active',
        })

        # Generate Mon-Fri schedule for Alpha across all weeks of the 3-month term
        wizard = self.Wizard.create({
            'term_id': term.id,
            'class_id': self.class_alpha.id,
            'mode': 'create_slots',
            'schedule_scope': 'all_term_weeks',
            'overwrite_existing': True,
            'mon_fri_periods': '4_morning',
            'include_mon': True,
            'include_tue': True,
            'include_wed': True,
            'include_thu': True,
            'include_fri': True,
            'distribute_subjects': True,
        })
        wizard.action_generate_monday_to_friday()
        self.assertEqual(len(wizard.line_ids), 20)

        # Apply schedule for the whole 3 months (~13 weeks * 20 sessions)
        action_res = wizard.action_apply_schedule()
        self.assertTrue(action_res)

        all_sessions = self.Timetable.search([
            ('term_id', '=', term.id),
            ('class_id', '=', self.class_alpha.id),
        ])
        self.assertTrue(len(all_sessions) > 200, "Should generate > 200 sessions across 13 weeks of the term")

        # Verify student timetable count and action
        self.student_1._compute_timetable_count()
        self.assertEqual(self.student_1.timetable_count, len(all_sessions))

        student_action = self.student_1.action_view_timetable()
        self.assertEqual(student_action.get('res_model'), 'school.timetable')
        self.assertEqual(student_action.get('view_mode'), 'calendar,list,kanban,form')

        # Test overwrite_existing replaces sessions without errors
        wizard_repeat = self.Wizard.create({
            'term_id': term.id,
            'class_id': self.class_alpha.id,
            'mode': 'create_slots',
            'schedule_scope': 'single_week',
            'overwrite_existing': True,
            'line_ids': [
                (0, 0, {
                    'day_of_week': '0',
                    'period': 'p1',
                    'start_time': 8.0,
                    'end_time': 9.0,
                    'subject_id': self.subject_math.id,
                    'teacher_id': self.teacher_1.id,
                })
            ]
        })
        wizard_repeat.action_apply_schedule()

        new_sessions = self.Timetable.search([
            ('term_id', '=', term.id),
            ('class_id', '=', self.class_alpha.id),
        ])
        self.assertEqual(len(new_sessions), 1)
