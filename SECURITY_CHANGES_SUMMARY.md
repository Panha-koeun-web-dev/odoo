# Teacher Role Security Improvements

## Summary
Updated `security/school_security.xml` to restrict teacher role access from unrestricted CRUD on all records to role-specific data isolation.

## Changes Made

All teacher `ir.rule` records changed from `domain_force">[(1, '=', 1)]"` (unrestricted) to specific domain restrictions:

### Teacher Data Isolation Rules

| Rule ID | Model | Restriction Pattern |
|---------|-------|---------------------|
| `rule_school_student_teacher` | `school.student` | `[('class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_grade_teacher` | `school.grade` | `[('student_id.class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_attendance_teacher` | `school.attendance` | `[('student_id.class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_enrollment_teacher` | `school.enrollment` | `[('class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_exam_teacher` | `school.exam` | `[('class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_timetable_teacher` | `school.timetable` | `[('teacher_id.user_id', '=', user.id)]` |
| `rule_school_teaching_assignment_teacher` | `school.teaching.assignment` | `[('teacher_id.user_id', '=', user.id)]` |
| `rule_school_student_subject_teacher` | `school.student.subject` | `[('teacher_id.user_id', '=', user.id)]` |
| `rule_school_student_year_payment_teacher` | `school.student.year.payment` | `[('student_id.class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_certificate_teacher` | `school.certificate` | `[('student_id.class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_fee_teacher` | `school.fee` | `[('student_id.class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_major_enrollment_teacher` | `school.major.enrollment` | `[('class_id.teacher_id.user_id', '=', user.id)]` |
| `rule_school_class_teacher` | `school.class` | `[('teacher_id', '=', user.id)]` |

### Rules Left Unchanged (already restricted)
- `rule_school_permission_teacher` - Already had `teacher_id.user_id` restriction
- `rule_school_feedback_teacher_read` - Already had `teacher_id.user_id` restriction
- `rule_school_feedback_teacher_write` - Already had `teacher_id.user_id` restriction

### Admin Rules (unchanged - full access)
All `*_admin` rules retain `domain_force">[(1, '=', 1)]"` for full administrative access.

## Security Impact
- **Before:** Teachers could read/write ALL records across all models (e.g., Teacher John could access Student Bob from Teacher Other's class)
- **After:** Teachers can only access records related to their assigned classes/students via `teacher_id.user_id` or `class_id.teacher_id.user_id` patterns
- Admin full access preserved for all models