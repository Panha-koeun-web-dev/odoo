# School Management — Improvement Plan

Ideas for what to improve next in the Odoo `school_management` module
(and the project around it), based on a review of the current code.

---

## 1. Security / Access Control (biggest priority)

The module defines 3 groups (`group_school_admin`, `group_school_teacher`,
`group_school_student`) but **never actually uses them**:

- `security/school_security.xml` only creates the groups.
- `security/ir.model.access.csv` gives **every internal user** full
  create/read/write/unlink on every model via `base.group_user`.
- No `groups=` attribute on any `<menuitem>` or action.

**What to do:**
- Grant access per-group (admin = all, teacher = students/grades/attendance only,
  student = read-only own records).
- Attach `groups=` to menus and actions so teachers/students only see relevant screens.
- Add `record rules` so a teacher only sees their own classes, a student only sees
  their own data (e.g. `student_id.user_id == user.id`).
- Create sample users + assign groups in demo data so access is actually testable.

---

## 2. Testing

There are **no automated tests** anywhere in the module.

**What to do:**
- Add `tests/` with `tests/__init__.py` and `tests/test_school.py`.
- Unit-test the computed fields (age, percentage, grade_letter, pass/fail, balance)
  and methods (`action_mark_paid`, `open_*` actions).
- Add tests for the `_unique_attendance` constraint and the fee status logic.
- Use Odoo's `TransactionCase` and run with
  `odoo-bin -c odoo.conf -d testing_db -i school_management --test-enable --stop-after-init`.

---

## 3. Code quality & consistency

Several small but worthwhile cleanups:

- **`_rec_name` / duplicate labels:** `student_count` vs `student_ids` on
  `school.class` both translate to "Students" (known warning). Rename one `string=`.
- **`depends` key missing in manifest**: README lists `'depends': ['base']` but the
  real manifest has `['base', 'web']` — keep docs in sync.
- **Demo vs data duplication:** `data/demo_data.xml` is listed in BOTH `data` and
  `demo` in the manifest — move it to `demo` only (or `data` only).
- **`_open_records` helper** is defined in `models/student.py` but used by student
  only — consider moving to a reusable mixin/`models/__init__.py` util if reused.
- Add `_sql_constraints`/`Constraint` to enforce uniqueness:
  - teacher `employee_id` unique
  - subject `code` unique
  - student `student_id` unique
- Add `index=True` on frequently-filtered fields (`class_id`, `student_id`, `date`).
- Run `ruff` / the repo's `ruff.toml` over the custom module.

---

## 4. Missing business features

Natural next modules/features:

- **Fee payments as a real flow:** a `school.payment` model with installments,
  receipts auto-numbered, refunds, and a wizard "Register Payment" instead of the
  single `action_mark_paid` button.
- **Attendances in bulk:** a wizard "Mark attendance for class/date" so teachers
  don't create records one-by-one (grid of students × status).
- **Student report cards / transcript:** a printable PDF report per student
  (grades per subject, GPA, attendance, remarks) via QWeb report.
- **Report cards by class** batch print.
- **Timetable / scheduling** model (class × subject × day × period) for teachers.
- **Parent / guardian portal:** log in as parent, see child's grades, fees, attendance.
- **Academic year / term / session** support — most school data is period-based and
  currently has no term scoping.
- **Alumni tracking**, **library module**, **transport routes**, **hostel/boarding**.

---

## 5. Dashboard & reporting improvements

The dashboard is already impressive. Ideas to push further:

- **Add date-range filters** (term, month) so the dashboard gives historical views,
  not just a current snapshot.
- **Drill-down on charts** — click a donut segment / bar to open the filtered list
  (some cards already link to actions; add context filters).
- **Top/bottom performers** tables (best/worst students by percentage).
- **Teacher workload** chart (subjects + students per teacher).
- **Fee aging** breakdown (how long overdue).
- Export the dashboard as PDF.

---

## 6. UX / polish

- **`_rec_name` on fee/attendance/grade** is `student_id`; add meaningful
  `display_name` computed fields (e.g. "S001 — Tuition Fee — Overdue").
- **Smart buttons / stat buttons** on Teacher (subjects, classes) and Class
  (students, exams) forms, not just on Student.
- **Default filters + grouped kanban** everywhere (e.g. fees by status by default).
- **Email integration:** notify parents/students automatically (fee reminders,
  low-attendance warnings, exam results) via the `mail` module.
- **Progress per student** on the student form (average %, attendance rate, fees paid).

---

## 7. Data & localization

- Add **constraints/defaults** in demo data (all teachers/classes have users).
- Add **translations** (`.po` files) for the module strings.
- Move hard-coded strings in `dashboard.py` into `_()` for translatability
  (a lot are currently hard-coded English).

---

## 8. Project / repo hygiene

- Remove stray local files that aren't part of the module: `demo.md`, `fix.md`,
  `SCHOOL_MANAGEMENT_SYSTEM.md` at repo root, and the `.claude/` work dir.
- The repo is a fork of core Odoo (`git log` shows upstream commits). Consider a
  cleaner project layout: keep the module separate from `odoo/` core so it's
  portable (e.g. as its own repo / `addons_path`).
- Add a proper `CHANGELOG` and semantic versioning for the module.
- **CI:** a GitHub Action that installs the module against a fresh DB and runs the
  tests / ruff on PRs.

---

### Suggested order of work

1. **Security & record rules** (foundation — should be first).
2. **Automated tests** (makes everything else safe to change).
3. **Code quality cleanups** (small, low risk).
4. **Feature: fee payment flow + attendance bulk-entry wizard** (highest value).
5. **Feature: report cards / PDF reports**.
6. **Dashboard date filters + drill-down**.
7. **Email notifications**.
8. **CI + repo hygiene.**
