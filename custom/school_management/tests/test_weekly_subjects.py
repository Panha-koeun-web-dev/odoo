from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestWeeklySubjects(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.teacher_math = cls.env['school.teacher'].create({
            'name': 'Dr. Alan Turing',
            'employee_id': 'TCH-ALAN-01',
            'email': 'alan.turing@school.edu',
        })

        cls.teacher_phys = cls.env['school.teacher'].create({
            'name': 'Dr. Marie Curie',
            'employee_id': 'TCH-MARIE-01',
            'email': 'marie.curie@school.edu',
        })

        cls.sub_math = cls.env['school.subject'].create({
            'name': 'Advanced Mathematics',
            'code': 'MATH301',
            'department': 'mathematics',
        })

        cls.sub_phys = cls.env['school.subject'].create({
            'name': 'Quantum Physics',
            'code': 'PHYS301',
            'department': 'science',
        })

        cls.school_class = cls.env['school.class'].create({
            'name': 'Grade 11 - Science A',
            'code': 'G11-SCI-A',
            'room': 'Lab 101',
            'capacity': 30,
        })

        cls.student = cls.env['school.student'].create({
            'name': 'Bobby Fischer',
            'student_id': 'STU-BOBBY-01',
            'gender': 'male',
            'date_of_birth': '2008-03-09',
            'class_id': cls.school_class.id,
            'study_status': 'studying',
        })

    def test_01_teaching_assignment_and_workload(self):
        """Test teacher assignment creation, weekly load calculation and class analytics."""
        asg = self.env['school.teaching.assignment'].create({
            'teacher_id': self.teacher_math.id,
            'subject_id': self.sub_math.id,
            'class_id': self.school_class.id,
            'weekly_hours': 4.0,
            'weekly_sessions': 2,
        })

        self.assertEqual(asg.schedule_status, 'not_scheduled')
        self.assertEqual(self.teacher_math.teaching_assignment_count, 1)
        self.assertEqual(self.teacher_math.total_weekly_teaching_hours, 4.0)
        self.assertEqual(self.teacher_math.total_weekly_teaching_sessions, 2)
        self.assertEqual(self.school_class.total_weekly_class_hours, 4.0)
        self.assertIn(self.student, asg.student_ids)
        self.assertEqual(asg.student_count, 1)

    def test_02_student_subject_auto_sync_and_workload(self):
        """Test auto-sync from class curriculum to student study subjects."""
        # 1. Assign math and physics to class
        self.env['school.teaching.assignment'].create({
            'teacher_id': self.teacher_math.id,
            'subject_id': self.sub_math.id,
            'class_id': self.school_class.id,
            'weekly_hours': 4.0,
            'weekly_sessions': 2,
        })
        self.env['school.teaching.assignment'].create({
            'teacher_id': self.teacher_phys.id,
            'subject_id': self.sub_phys.id,
            'class_id': self.school_class.id,
            'weekly_hours': 3.0,
            'weekly_sessions': 2,
        })

        # 2. Sync subjects to enrolled students via class action
        self.school_class.action_sync_subjects_to_students()

        self.assertEqual(len(self.student.study_subject_ids), 2)
        self.assertEqual(self.student.study_subject_count, 2)
        self.assertEqual(self.student.total_weekly_study_hours, 7.0)
        self.assertEqual(self.student.total_weekly_study_sessions, 4)

        math_study = self.student.study_subject_ids.filtered(lambda s: s.subject_id == self.sub_math)
        self.assertEqual(math_study.teacher_id, self.teacher_math)
        self.assertEqual(math_study.weekly_hours, 4.0)

    def test_03_timetable_integration_with_study_and_teaching(self):
        """Test how timetable slots update scheduled hours and status for both teacher and student."""
        asg = self.env['school.teaching.assignment'].create({
            'teacher_id': self.teacher_math.id,
            'subject_id': self.sub_math.id,
            'class_id': self.school_class.id,
            'weekly_hours': 4.0,
            'weekly_sessions': 2,
        })
        self.school_class.action_sync_subjects_to_students()
        stu_sub = self.student.study_subject_ids.filtered(lambda s: s.subject_id == self.sub_math)

        # Before scheduling
        self.assertEqual(asg.scheduled_hours, 0.0)
        self.assertEqual(asg.schedule_status, 'not_scheduled')
        self.assertEqual(stu_sub.schedule_status, 'not_scheduled')

        # Add slot 1 (Monday 08:00 - 10:00 -> 2 hours)
        slot1 = self.env['school.timetable'].create({
            'class_id': self.school_class.id,
            'subject_id': self.sub_math.id,
            'teacher_id': self.teacher_math.id,
            'day_of_week': '0',
            'period': 'custom',
            'start_time': 8.0,
            'end_time': 10.0,
        })

        asg._compute_timetable_stats()
        stu_sub._compute_timetable_stats()
        self.assertEqual(asg.scheduled_hours, 2.0)
        self.assertEqual(asg.schedule_status, 'under_scheduled')
        self.assertEqual(stu_sub.scheduled_hours, 2.0)
        self.assertEqual(stu_sub.schedule_status, 'under_scheduled')

        # Add slot 2 (Wednesday 08:00 - 10:00 -> 2 hours)
        slot2 = self.env['school.timetable'].create({
            'class_id': self.school_class.id,
            'subject_id': self.sub_math.id,
            'teacher_id': self.teacher_math.id,
            'day_of_week': '2',
            'period': 'custom',
            'start_time': 8.0,
            'end_time': 10.0,
        })

        asg._compute_timetable_stats()
        stu_sub._compute_timetable_stats()
        self.assertEqual(asg.scheduled_hours, 4.0)
        self.assertEqual(asg.schedule_status, 'fully_scheduled')
        self.assertEqual(stu_sub.scheduled_hours, 4.0)
        self.assertEqual(stu_sub.schedule_status, 'fully_scheduled')

        # Unlink one slot
        slot2.unlink()
        asg._compute_timetable_stats()
        stu_sub._compute_timetable_stats()
        self.assertEqual(asg.scheduled_hours, 2.0)
        self.assertEqual(asg.schedule_status, 'under_scheduled')

    def test_04_workload_validation_constraints(self):
        """Test validation constraints on hours and sessions."""
        with self.assertRaises(ValidationError):
            self.env['school.teaching.assignment'].create({
                'teacher_id': self.teacher_math.id,
                'subject_id': self.sub_math.id,
                'class_id': self.school_class.id,
                'weekly_hours': 0.0,
            })

        with self.assertRaises(ValidationError):
            self.env['school.student.subject'].create({
                'student_id': self.student.id,
                'subject_id': self.sub_math.id,
                'weekly_hours': -2.0,
            })

    def test_05_assign_subject_wizard(self):
        """Test Assign Subject Wizard for teacher assignment, student enrollment, and quick scheduling."""
        Wizard = self.env['school.assign.subject.wizard']

        # Mode 1: teacher_assign with timetable slot creation
        wiz1 = Wizard.create({
            'mode': 'teacher_assign',
            'teacher_id': self.teacher_phys.id,
            'subject_id': self.sub_phys.id,
            'class_id': self.school_class.id,
            'weekly_hours': 4.0,
            'weekly_sessions': 2,
            'create_timetable_slots': True,
            'day_of_week': '1',  # Tuesday
            'start_time': 10.0,
            'end_time': 12.0,
            'room': 'Physics Lab',
        })
        res1 = wiz1.action_apply()
        self.assertEqual(res1['type'], 'ir.actions.client')

        # Verify teaching assignment created
        asg = self.env['school.teaching.assignment'].search([
            ('teacher_id', '=', self.teacher_phys.id),
            ('subject_id', '=', self.sub_phys.id),
            ('class_id', '=', self.school_class.id),
        ])
        self.assertTrue(asg)
        self.assertEqual(asg.weekly_hours, 4.0)

        # Verify student enrolled
        stu_sub = self.env['school.student.subject'].search([
            ('student_id', '=', self.student.id),
            ('subject_id', '=', self.sub_phys.id),
        ])
        self.assertTrue(stu_sub)
        self.assertEqual(stu_sub.teacher_id, self.teacher_phys)

        # Verify timetable slot created
        slot = self.env['school.timetable'].search([
            ('teacher_id', '=', self.teacher_phys.id),
            ('subject_id', '=', self.sub_phys.id),
            ('class_id', '=', self.school_class.id),
            ('day_of_week', '=', '1'),
        ])
        self.assertTrue(slot)
        self.assertEqual(slot.room, 'Physics Lab')

        # Mode 2: student_enroll
        wiz2 = Wizard.create({
            'mode': 'student_enroll',
            'student_ids': [(6, 0, [self.student.id])],
            'subject_ids': [(6, 0, [self.sub_math.id])],
            'teacher_id': self.teacher_math.id,
            'weekly_hours': 5.0,
        })
        wiz2.action_apply()
        stu_sub_math = self.env['school.student.subject'].search([
            ('student_id', '=', self.student.id),
            ('subject_id', '=', self.sub_math.id),
        ])
        self.assertTrue(stu_sub_math)
        self.assertEqual(stu_sub_math.weekly_hours, 5.0)

    def test_06_model_wizard_actions(self):
        """Test header wizard action helpers on teacher, student, class, and assignment."""
        t_action = self.teacher_math.action_open_assign_wizard()
        self.assertEqual(t_action['res_model'], 'school.assign.subject.wizard')
        self.assertEqual(t_action['context']['default_teacher_id'], self.teacher_math.id)

        s_action = self.student.action_open_assign_wizard()
        self.assertEqual(s_action['res_model'], 'school.assign.subject.wizard')

        c_action = self.school_class.action_open_assign_wizard()
        self.assertEqual(c_action['res_model'], 'school.assign.subject.wizard')

    def test_07_teacher_many_subjects_and_student_many_teachers(self):
        """Test teacher teaching multiple subjects, and student studying with multiple teachers and subjects."""
        # 1. Create a 3rd subject (Chemistry)
        sub_chem = self.env['school.subject'].create({
            'name': 'Chemistry',
            'code': 'CHEM-101',
        })

        # 2. Teacher teaches multiple subjects: Math AND Chemistry
        wiz = self.env['school.assign.subject.wizard'].create({
            'mode': 'teacher_assign',
            'teacher_id': self.teacher_math.id,
            'subject_ids': [(6, 0, [self.sub_math.id, sub_chem.id])],
            'class_id': self.school_class.id,
            'weekly_hours': 3.0,
            'weekly_sessions': 2,
        })
        wiz.action_apply()

        # Check teacher has both subjects in catalog
        self.assertIn(self.sub_math, self.teacher_math.subject_ids)
        self.assertIn(sub_chem, self.teacher_math.subject_ids)

        # 3. Student studies multiple subjects with different teachers:
        # Math with teacher_math, Physics with teacher_phys
        self.env['school.student.subject'].create({
            'student_id': self.student.id,
            'subject_id': self.sub_phys.id,
            'teacher_id': self.teacher_phys.id,
            'weekly_hours': 4.0,
            'weekly_sessions': 2,
        })

        # Also student studies Math tutoring with teacher_phys
        stu_math_tutoring = self.env['school.student.subject'].create({
            'student_id': self.student.id,
            'subject_id': self.sub_math.id,
            'teacher_id': self.teacher_phys.id,
            'weekly_hours': 1.0,
            'weekly_sessions': 1,
            'subject_type': 'extra',
        })
        self.assertTrue(stu_math_tutoring)

        # 4. Verify student stats
        self.student._compute_study_stats()
        self.assertIn(self.teacher_math, self.student.study_teacher_ids)
        self.assertIn(self.teacher_phys, self.student.study_teacher_ids)
        self.assertEqual(self.student.study_teacher_count, 2)
        self.assertIn(self.sub_math, self.student.study_subject_all_ids)
        self.assertIn(self.sub_phys, self.student.study_subject_all_ids)

        # Test action views
        t_action = self.student.action_view_study_teachers()
        self.assertEqual(t_action['res_model'], 'school.teacher')
        sched_action = self.student.action_view_student_timetable()
        self.assertEqual(sched_action['res_model'], 'school.timetable')

    def test_08_multi_student_session_and_conflicts(self):
        """Test timetable session with multiple students and collision prevention."""
        # Create a second student
        student2 = self.env['school.student'].create({
            'name': 'Student Two',
            'student_id': 'STU-TEST-002',
            'gender': 'female',
            'date_of_birth': '2006-05-15',
            'class_id': self.school_class.id,
        })

        # Create multi-student schedule session (e.g. Wednesday 10:00 - 11:30)
        session = self.env['school.timetable'].create({
            'subject_id': self.sub_math.id,
            'teacher_id': self.teacher_math.id,
            'student_ids': [(6, 0, [self.student.id, student2.id])],
            'day_of_week': '2',  # Wednesday
            'start_time': 10.0,
            'end_time': 11.5,
            'room': 'Lab 1',
        })
        self.assertTrue(session)
        self.assertEqual(len(session.student_ids), 2)

        # Attempt to schedule student2 in another session at the same time -> should raise ValidationError
        with self.assertRaises(ValidationError):
            self.env['school.timetable'].create({
                'subject_id': self.sub_phys.id,
                'teacher_id': self.teacher_phys.id,
                'student_id': student2.id,
                'day_of_week': '2',
                'start_time': 10.5,
                'end_time': 12.0,
                'room': 'Lab 2',
            })

    def test_09_multi_subject_timetable_session(self):
        """Test creating timetable session with multiple subjects and verify stats integration."""
        # 1. Create a session with multiple subjects (Math and Physics) for school_class
        session = self.env['school.timetable'].create({
            'class_id': self.school_class.id,
            'teacher_id': self.teacher_math.id,
            'subject_ids': [(6, 0, [self.sub_math.id, self.sub_phys.id])],
            'day_of_week': '3',  # Thursday
            'start_time': 14.0,
            'end_time': 16.0,  # 2.0 hours
            'room': 'STEM Center',
        })

        self.assertTrue(session)
        # Verify subject_ids has both
        self.assertEqual(set(session.subject_ids.ids), {self.sub_math.id, self.sub_phys.id})
        # Verify primary subject_id is auto-computed
        self.assertEqual(session.subject_id, self.sub_math)
        # Verify subjects_display contains both subject names
        self.assertIn('Mathematics', session.subjects_display)
        self.assertIn('Physics', session.subjects_display)
        # Verify both subjects auto-linked to teacher
        self.assertIn(self.sub_math, self.teacher_math.subject_ids)
        self.assertIn(self.sub_phys, self.teacher_math.subject_ids)

        # 2. Create teaching assignments for both subjects if not already present
        asg_math = self.env['school.teaching.assignment'].search([
            ('teacher_id', '=', self.teacher_math.id),
            ('class_id', '=', self.school_class.id),
            ('subject_id', '=', self.sub_math.id),
        ], limit=1)
        if asg_math:
            asg_math._compute_timetable_stats()
            self.assertGreaterEqual(asg_math.scheduled_hours, 2.0)

        # 3. Create or check student study plan for both subjects
        stu_sub_math = self.env['school.student.subject'].search([
            ('student_id', '=', self.student.id),
            ('subject_id', '=', self.sub_math.id),
        ], limit=1)
        if stu_sub_math:
            stu_sub_math._compute_timetable_stats()
            self.assertGreaterEqual(stu_sub_math.scheduled_hours, 2.0)

    def test_10_student_timetable_full_integration(self):
        """Test student timetable full integration: computed fields, views, actions, and auto-sync."""
        # 1. Verify student timetable_ids computation
        self.student._compute_timetable_ids()
        initial_sessions = len(self.student.timetable_ids)

        # 2. Create a new timetable session for the student's class
        session = self.env['school.timetable'].create({
            'class_id': self.school_class.id,
            'teacher_id': self.teacher_math.id,
            'subject_ids': [(6, 0, [self.sub_math.id])],
            'day_of_week': '4',  # Friday
            'start_time': 9.0,
            'end_time': 11.0,  # 2.0 hours
            'room': 'Hall 101',
        })
        self.assertTrue(session)

        # 3. Student timetable_ids should now include the session
        self.student._compute_timetable_ids()
        self.assertIn(session, self.student.timetable_ids)
        self.assertGreaterEqual(self.student.timetable_count, initial_sessions + 1)

        # 4. Student study subject for Math should be auto-ensured and scheduled hours updated
        stu_sub = self.env['school.student.subject'].search([
            ('student_id', '=', self.student.id),
            ('subject_id', '=', self.sub_math.id),
        ], limit=1)
        self.assertTrue(stu_sub, "StudentSubject should be automatically present")
        self.assertGreaterEqual(stu_sub.scheduled_hours, 2.0)
        self.student._compute_study_stats()
        self.assertGreaterEqual(self.student.total_scheduled_study_hours, 2.0)

        # 5. Verify action_view_student_timetable
        act_tt = self.student.action_view_student_timetable()
        self.assertEqual(act_tt['res_model'], 'school.timetable')
        self.assertIn('calendar', act_tt['view_mode'])

        # 6. Verify subject-level action_view_timetable
        act_sub_tt = stu_sub.action_view_timetable()
        self.assertEqual(act_sub_tt['res_model'], 'school.timetable')

        # 7. Unlink session and verify stats update
        session.unlink()
        self.student._compute_timetable_ids()
        self.assertNotIn(session, self.student.timetable_ids)

    def test_11_student_account_timetable_visibility(self):
        """Test that when admin assigns schedules to a student (1-on-1, group, or whole-class),
        the student can view and access the schedule in their own account without error,
        while remaining isolated from other students' private sessions."""
        # 1. Create a portal/internal user for the student with group_school_student
        group_student = self.env.ref('school_management.group_school_student')
        student_user = self.env['res.users'].create({
            'name': 'Bobby Fischer User',
            'login': 'bobby.fischer@testschool.edu',
            'email': 'bobby.fischer@testschool.edu',
            'group_ids': [(6, 0, [group_student.id, self.env.ref('base.group_user').id])],
        })
        self.student.write({'user_id': student_user.id})

        # 2. Create another student and their class
        other_class = self.env['school.class'].create({
            'name': 'Grade 12 - Arts B',
            'code': 'G12-ART-B',
        })
        other_student = self.env['school.student'].create({
            'name': 'Garry Kasparov',
            'student_id': 'STU-GARRY-01',
            'gender': 'male',
            'date_of_birth': '2007-01-01',
            'class_id': other_class.id,
            'study_status': 'studying',
        })

        # Admin assigns Session A: 1-on-1 directly to Bobby (student_id)
        sess_individual = self.env['school.timetable'].create({
            'name': 'Bobby 1-on-1 Math Mentoring',
            'student_id': self.student.id,
            'teacher_id': self.teacher_math.id,
            'subject_ids': [(6, 0, [self.sub_math.id])],
            'day_of_week': '0',  # Monday
            'start_time': 14.0,
            'end_time': 15.0,
            'room': 'Office 1',
        })

        # Admin assigns Session B: Group session with Bobby (student_ids)
        sess_group = self.env['school.timetable'].create({
            'name': 'Advanced Math Olympiad Group',
            'student_ids': [(6, 0, [self.student.id, other_student.id])],
            'teacher_id': self.teacher_math.id,
            'subject_ids': [(6, 0, [self.sub_math.id])],
            'day_of_week': '1',  # Tuesday
            'start_time': 15.0,
            'end_time': 16.0,
            'room': 'Lab 101',
        })

        # Admin assigns Session C: Class-wide session for Grade 11 - Science A
        sess_class = self.env['school.timetable'].create({
            'name': 'Grade 11 Physics Lecture',
            'class_id': self.school_class.id,
            'teacher_id': self.teacher_phys.id,
            'subject_ids': [(6, 0, [self.sub_phys.id])],
            'day_of_week': '2',  # Wednesday
            'start_time': 10.0,
            'end_time': 11.0,
            'room': 'Physics Lab',
        })

        # Admin assigns Session D: 1-on-1 private tutoring for Garry Kasparov ONLY
        sess_other = self.env['school.timetable'].create({
            'name': 'Garry Private Tutoring',
            'student_id': other_student.id,
            'teacher_id': self.teacher_phys.id,
            'subject_ids': [(6, 0, [self.sub_phys.id])],
            'day_of_week': '3',  # Thursday
            'start_time': 14.0,
            'end_time': 15.0,
            'room': 'Office 2',
        })

        # 3. Read timetable sessions as Bobby Fischer (student user)
        student_tt_env = self.env['school.timetable'].with_user(student_user)
        visible_sessions = student_tt_env.search([])

        # Bobby MUST see: individual session, group session, and class session
        self.assertIn(sess_individual.id, visible_sessions.ids, "Student must see individual session assigned by admin")
        self.assertIn(sess_group.id, visible_sessions.ids, "Student must see group session assigned by admin")
        self.assertIn(sess_class.id, visible_sessions.ids, "Student must see whole-class session assigned by admin")

        # Bobby MUST NOT see Garry's private session
        self.assertNotIn(sess_other.id, visible_sessions.ids, "Student must not see another student's private session")

        # 4. Student can read session details without AccessError
        my_session = student_tt_env.browse(sess_individual.id)
        read_data = my_session.read(['name', 'teacher_id', 'subject_ids', 'start_time', 'end_time', 'room'])
        self.assertTrue(read_data)
        self.assertEqual(read_data[0]['name'], 'Bobby 1-on-1 Math Mentoring')

        # 5. Check student profile timetable_ids as student user
        student_profile = self.student.with_user(student_user)
        self.assertIn(sess_individual, student_profile.timetable_ids)
        self.assertIn(sess_group, student_profile.timetable_ids)
        self.assertIn(sess_class, student_profile.timetable_ids)
        self.assertNotIn(sess_other, student_profile.timetable_ids)
