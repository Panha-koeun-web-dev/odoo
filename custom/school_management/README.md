# School Management — Code Explanation & Project Workflow

This document explains the Odoo `school_management` module step by step, so you can
understand how the code works and how the whole project comes together.

> This is a **beginner-friendly** walkthrough. It assumes you know a little code but
> are new to Odoo.

---

## Table of Contents

1. [Big Picture: What is an Odoo Module?](#1-big-picture-what-is-an-odoo-module)
2. [Project / Folder Structure](#2-project--folder-structure)
3. [The Manifest — the module "ID card" (`__manifest__.py`)](#3-the-manifest)
4. [Models — the data layer](#4-models)
5. [Security — who can see what](#5-security)
6. [Views — the UI layer](#6-views)
7. [Menus — navigation](#7-menus)
8. [Demo Data — sample records](#8-demo-data)
9. [How I Improved the UI (badges, kanban, progress bars)](#9-ui-improvements)
10. [The Full Project Workflow](#10-the-full-project-workflow)
11. [How to Run / Install / Update](#11-how-to-run--install--update)
12. [FAQ / Common gotchas](#12-faq--common-gotchas)

---

## 1. Big Picture: What is an Odoo Module?

Odoo is a **modular ERP**. Everything is a "module" — a self-contained folder that adds
features to the system. A module is basically a bundle of:

- **Models** (Python classes) → define what data we store and how we store it.
- **Views** (XML files) → define how that data is displayed (lists, forms, kanban…).
- **Security files** → define who can access the data.
- **Menus** → define where the user finds it in the navigation bar.
- **Data files** → optional sample/default records.

A module is just a folder with a correct structure and a `__manifest__.py` that tells
Odoo how to load everything.

---

## 2. Project / Folder Structure

```
odoo/
│
├── odoo/                     # The Odoo core framework (don't edit)
├── addons/                   # Standard Odoo built-in modules
├── custom/                   # <-- OUR modules live here
│   └── school_management/    # <-- the module we are working on
│       ├── __init__.py           # imports the models package
│       ├── __manifest__.py       # module declaration (name, deps, files)
│       ├── models/               # Python data models
│       │   ├── __init__.py
│       │   ├── student.py
│       │   ├── teacher.py
│       │   ├── school_class.py
│       │   ├── subject.py
│       │   ├── attendance.py
│       │   ├── exam.py
│       │   ├── grade.py
│       │   └── fee.py
│       ├── security/             # access rules
│       │   ├── school_security.xml
│       │   └── ir.model.access.csv
│       ├── data/                 # sample/demo data
│       │   └── demo_data.xml
│       ├── views/                # the UI (XML)
│       │   ├── menu.xml
│       │   ├── student_views.xml
│       │   ├── teacher_views.xml
│       │   ├── class_views.xml
│       │   ├── subject_views.xml
│       │   ├── attendance_views.xml
│       │   ├── exam_views.xml
│       │   ├── grade_views.xml
│       │   └── fee_views.xml
│       └── README.md             # this file :)
│
├── odoo-bin                    # script that starts/updates Odoo
├── odoo.conf                   # database + ports + addons_path config
└── SCHOOL_MANAGEMENT_SYSTEM.md # your original run guide
```

---

## 3. The Manifest

**File:** `__manifest__.py`

```python
{
    'name': 'School Management',       # human friendly name
    'version': '19.0.1.0.0',           # Odoo 19, module version 1.0.0
    'summary': 'Manage students, teachers, classes, exams and fees',
    'description': 'Complete school management system for Odoo 19',
    'author': 'Panha Koeun',
    'category': 'School',
    'depends': ['base'],               # modules it needs before it can run
    'data': [                          # ORDER MATTERS — loaded top to bottom
        'security/school_security.xml',
        'security/ir.model.access.csv',
        'data/demo_data.xml',
        'views/student_views.xml',
        'views/teacher_views.xml',
        'views/class_views.xml',
        'views/subject_views.xml',
        'views/attendance_views.xml',
        'views/exam_views.xml',
        'views/grade_views.xml',
        'views/fee_views.xml',
        'views/menu.xml',              # menus go last (they reference actions from views)
    ],
    'demo': ['data/demo_data.xml'],   # loaded only if "Load demo data" is checked
    'installable': True,
    'application': True,               # shows as an App in the Apps menu
    'license': 'LGPL-3',
}
```

**Key ideas:**
- `data` is the list of files Odoo reads when the module installs/updates.
  Order is critical: security **before** data, views before menus.
- `demo` is separate from `data`. Because `demo_data.xml` is listed in both, it is
  loaded as normal data AND as demo data — a small quirk worth knowing.
- `application: True` makes it appear as a full app with an icon.

---

## 4. Models

Models are Python classes that create database tables. Every model sets at least:

- `_name` → the technical id used across Odoo (e.g. `school.student`).
- `_description` → human text for logs/errors.
- fields → columns of the table (Char, Integer, Date, Selection, Many2one…).
- computed methods → calculate values on the fly.

### 4.1 Student — `models/student.py`

```python
from odoo import models, fields, api, _

class SchoolStudent(models.Model):
    _name = 'school.student'
    _description = 'School Student'
    _order = 'name'                 # default sort by name

    name = fields.Char(string='Full Name', required=True)
    student_id = fields.Char(string='Student ID', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', required=True)
    ...
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    photo = fields.Image(string='Photo')
    ...
    attendance_ids = fields.One2many('school.attendance', 'student_id', string='Attendance')
    grade_ids = fields.One2many('school.grade', 'student_id', string='Grades')
    fee_ids = fields.One2many('school.fee', 'student_id', string='Fees')

    @api.depends('date_of_birth')
    def _compute_age(self):
        for rec in self:
            if rec.date_of_birth:
                today = fields.Date.today()
                rec.age = today.year - rec.date_of_birth.year - (
                    (today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day)
                )
            else:
                rec.age = 0
```

**Field types cheat-sheet:**
- `Char` — text (name, phone…)
- `Integer` — whole number (age)
- `Float` — decimal (marks, amount)
- `Date` — a calendar date
- `Selection` — dropdown from a fixed list (gender, status)
- `Many2one` — "belongs to one" other record (student → class)
- `One2many` — "has many" of another record (student → his fees)
- `Many2many` — many-to-many (teacher ↔ subject)
- `Image` / `Binary` — files/images
- `Boolean` — true/false (active)

**Computed fields:** `age` is not stored by the user — Odoo calculates it from
`date_of_birth`. The `@api.depends` decorator tells Odoo: *"recalculate age whenever
date_of_birth changes."* `store=True` means we also save it into the database
(speeds up searching/sorting).

**Methods I added for the UI stat buttons:**
```python
def open_attendance(self):
    return _open_records(self, 'attendance', [('student_id', '=', self.id)])

def open_grades(self):
    return _open_records(self, 'grade', [('student_id', '=', self.id)])

def open_fees(self):
    return _open_records(self, 'fee', [('student_id', '=', self.id)])
```
A helper function `_open_records` opens the relevant action window already filtered
to the current student. This is what makes the stat buttons in the form work.

### 4.2 Class — `models/school_class.py` (with the field I added)

```python
class SchoolClass(models.Model):
    _name = 'school.class'
    ...
    student_count = fields.Integer(string='Students', compute='_compute_student_count')
    capacity = fields.Integer(string='Capacity', default=40)
    room = fields.Char(string='Room Number')
    active = fields.Boolean(default=True)

    # NEW: percentage of the room already filled -> used for progress bars
    capacity_progress = fields.Float(string='Capacity %', compute='_compute_capacity_progress')

    def _compute_capacity_progress(self):
        for rec in self:
            rec.capacity_progress = (rec.student_count / rec.capacity * 100) if rec.capacity else 0

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = self.env['school.student'].search_count([
                ('class_id', '=', rec.id)
            ])
```

`capacity_progress` is a **computed Float** = students ÷ capacity × 100. I added it so
the kanban card and form can draw a "Capacity" progress bar.

### 4.3 attendance / exam / grade / fee

These follow the same pattern. One especially useful example is **grade**:

```python
@api.depends('marks_obtained', 'total_marks')
def _compute_percentage(self):
    for rec in self:
        rec.percentage = (rec.marks_obtained / rec.total_marks * 100) if rec.total_marks else 0
```

- `total_marks` is a `related` field — it borrows the value from the exam
  (`related='exam_id.total_marks'`), so you don't retype it.
- `percentage`, `grade_letter`, `result` are all computed from other fields — this is
  how the UI can show `A+`, `Pass`, and a colored progress bar without anyone typing them.

---

## 5. Security

Two files control access.

**`security/school_security.xml`** — defines *groups* (roles/users categories):
```xml
<record id="group_school_admin" model="res.groups">
    <field name="name">School Administrator</field>
</record>
<record id="group_school_teacher" model="res.groups">
    <field name="name">School Teacher</field>
</record>
<record id="group_school_student" model="res.groups">
    <field name="name">School Student</field>
</record>
```

**`security/ir.model.access.csv`** — grants permissions (create/read/write/delete) to
those groups on each model. One line per model per group:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
```

> Note: the menu in this module currently lists no `groups=...` attribute, so everyone
> can see it. If you later want only admins/teachers to see menus, add `groups=...`
> to the `<menuitem>`.

---

## 6. Views

Views are XML that describe the UI. Each one is a `<record>` with `model="ir.ui.view"`.

### 6.1 List view (a table of rows)

```xml
<record id="view_student_tree" model="ir.ui.view">
    <field name="name">school.student.list</field>
    <field name="model">school.student</field>
    <field name="arch" type="xml">
        <list decoration-info="age &lt; 13" decoration-muted="not active">
            <field name="student_id"/>
            <field name="name"/>
            <field name="class_id"/>
            <field name="gender" widget="badge"/>      <!-- badge instead of plain text -->
            <field name="age" optional="hide"/>
            ...
        </list>
    </field>
</record>
```

- `&lt;` is just the XML-escaped `<`. So `decoration-info="age < 13"` means:
  *colour the row if the student is younger than 13.*
- `decoration-danger/success/info/muted...` colour entire rows.
- `widget="badge"` renders a small pill instead of plain text.
- `optional="show/hide"` lets the user toggle columns.

### 6.2 Kanban view (cards)

```xml
<kanban class="o_kanban_mobile">
    <field name="photo"/>                    <!-- fields must be listed for use in template -->
    <field name="gender"/>
    ...
    <templates>
        <t t-name="kanban-box">
            <div class="oe_kanban_global_click">   <!-- whole card is clickable -->
                <div class="o_kanban_image">
                    <img t-if="record.photo.raw" t-att-src="'data:image/png;base64,'+record.photo.raw"
                         class="o_image_64_cover"/>
                    <span t-else="" class="o_kanban_avatar">
                        <span class="o_kanban_avatar_letter">S</span>
                    </span>
                </div>
                ...
                <field name="gender" widget="badge" bg_color="..."/>
            </div>
        </t>
    </templates>
</kanban>
```

- Kanban is **card-based** — great for contacts/students.
- `t-` directives (QWeb templating): `t-if` (condition), `t-else`, `t-att-src`
  (dynamic attribute), `t-esc` (escaped text).
- `record.photo.raw` is the raw Base64 of the image; we wrap it in a `data:image/png`
  URI so the browser can show it.
- `bg_color` here works (unlike in list views — see Gotchas).
- `default_group_by="status"` on the kanban shows cards automatically grouped into
  columns (e.g. attendance by status).

### 6.3 Form view

```xml
<form>
    <sheet>
        <div class="oe_button_box">                 <!-- stat buttons on the right -->
            <button name="open_attendance" type="object" class="oe_stat_button" icon="fa-calendar-check-o">
                <div class="o_stat_info"><span class="o_stat_text">Attendance</span></div>
            </button>
        </div>
        <div class="row">                            <!-- Bootstrap grid -->
            <div class="col-2"><field name="photo" widget="image" class="oe_avatar"/></div>
            <div class="col-10">
                <div class="oe_title"><h1><field name="name"/></h1></div>
                <field name="gender" widget="badge" bg_color="..."/>
            </div>
        </div>
        <group>                                      <!-- two-column layout -->
            <group>...</group>
            <group>...</group>
        </group>
        <notebook>                                   <!-- tabbed pages -->
            <page string="Fees"><field name="fee_ids"/></page>
        </notebook>
    </sheet>
</form>
```

- `<header>` can hold action buttons (e.g. `Mark as Paid` in fees).
- `oe_button_box`/`oe_stat_button` creates the little count buttons.
- `widget="progressbar"` draws a bar from a numeric value.

### 6.4 Search view

```xml
<search>
    <field name="name"/>
    <filter name="filter_male" string="Male" domain="[('gender','=','male')]"/>
    <separator/>
    <filter string="Class" name="group_class" domain="[]" context="{'group_by':'class_id'}"/>
</search>
```
A `filter` with a `domain` filters records; a filter with `context.group_by` becomes a
"Group By" option.

---

## 7. Menus — `views/menu.xml`

```xml
<menuitem id="menu_school_root" name="School" web_icon="..." sequence="20"/>
<menuitem id="menu_school_student_parent" name="Students" parent="menu_school_root" sequence="10"/>
<menuitem id="menu_school_student" name="All Students" parent="menu_school_student_parent"
          action="action_student" sequence="10"/>
```

- `parent` builds the tree (School → Students → All Students).
- `action` points to a window action defined in the view files (e.g. `action_student`),
  which decides which model + view modes to show.
- Menus must be loaded **after** the actions they reference — hence `menu.xml` last.

---

## 8. Demo Data — `data/demo_data.xml`

```xml
<record id="student_1" model="school.student">
    <field name="name">Dara Randy</field>
    <field name="student_id">S001</field>
    <field name="gender">male</field>
    <field name="date_of_birth">2008-05-15</field>
    <field name="class_id" ref="class_1"/>   <!-- reference another record by XML id -->
</record>
```
- Records are created by `<record>` with a unique `id` and the `model`.
- `ref=` links to another record defined in the same data (class_1, teacher_1…).
- `noupdate="1"` on `<data>` means these are set once and not overwritten on upgrade.

---

## 9. UI Improvements

Here is **exactly what I changed** and why it looks better:

| Area | Before | After |
|------|--------|-------|
| Student/Teacher list | plain fields | `widget="badge"` genders, row colours, optional columns |
| All major models | list + form only | added **kanban** cards with photos/avatars, icons, badges |
| Students form | simple two-group layout | photo next to title, **stat buttons** (Attendance/Grades/Fees), colour badge |
| Teachers form | simple two-group layout | photo next to title, employee/category badge |
| Classes | plain list | kanban with capacity **progress bar**, new `capacity_progress` field |
| Attendance/Grades/Fees | plain lists | kanban grouped by status, colour-coded badges, progress bar for score |
| Fees | list with a button | list keeps "Mark Paid"; form gets a **header button** |
| Search | few filters | more filters + group-by pills everywhere |
| Menu | default | `web_icon` on the root School app |

### Why these look good (the "ingredients")
- **Color communicates state**: green = good (paid/pass/present), red = bad
  (overdue/fail/absent), yellow = caution (pending/late), blue = info.
- **Badges** (`widget="badge"` + `bg_color`) turn plain text into pills.
- **Progress bars** (`widget="progressbar"`) visualise percentages (score, capacity).
- **Kanban cards** make browsing people feel like a real app instead of a spreadsheet.
- **Avatars/photos** humanise student & teacher records.
- **Decorations** on list rows keep things readable even in table view.

---

## 10. The Full Project Workflow

This is how the pieces work together from code to screen.

```
 student_views.xml (kanban/list/form)
        │  "show this model this way"
        ▼
 action_student  (ir.actions.act_window)
        │  "open school.student as kanban,list,form"
        ▼
 menu.xml  (School → Students → All Students)
        │
        ▼
 User clicks → Odoo reads archive from DB → renders view
        ▲
        │ data model
 school.student (models/student.py)  +  security rules
```

**Step-by-step lifecycle of a feature (e.g. Students):**

1. **Define the model** (`models/student.py`) — the "shape" of a student.
2. **Define access rules** (`security/...) — who may see/edit students.
3. **Define views** (`views/student_views.xml`) — list, kanban, form, search.
4. **Define an action** — bundles the views together (also in the view file).
5. **Define a menu** (`views/menu.xml`) — links the action into navigation.
6. **Register everything** in `__manifest__.py` `data` list so Odoo loads them.
7. **Install/upgrade** the module → Odoo creates tables, loads views, adds menus.

**When you change code, you must tell Odoo to reload it:**
- New/changed **Python** → restart the server (or use `-u`).
- New/changed **XML** → open an Odoo shell / upgrade the module (`-u`).

---

## 11. How to Run / Install / Update

Use the **virtual environment** Python (plain `python` may lack deps).

```powershell
# Upgrade the module (picks up your XML + Python changes)
.venv\Scripts\python.exe odoo-bin -c odoo.conf -d testing_db -u school_management --stop-after-init

# Start the server normally
.venv\Scripts\python.exe odoo-bin -c odoo.conf
```

Then open **http://localhost:8069** and log in with `admin` / `admin`.

> If the server is *already running*, `-u` with `--stop-after-init` will update the
> database and the running instance picks up the changes via a registry reload signal.

---

## 12. FAQ / Common Gotchas

**1. "Invalid attribute `bg_color` / `progress` / `expand`"**
This Odoo build has **stricter** XML schemas (in `odoo/addons/base/rng/`) than stock
Odoo. They do NOT allow:
- `bg_color` on a `<field>` in a **list view** (use `decoration-*` on the `<list>` instead).
- `progress` on a `progressbar` field in a **list view**.
- `expand="0"` / group-wrapped filters in **search views** (put filters flat under `<search>`).

These DO work in **form** and **kanban** views (those aren't checked by the RNG), which
is why the colourful styling lives there.

**2. Why is my XML erroring during install?**
Almost always a schema issue or the wrong file `<record>` structure. Run the
`-u school_management` command and read the `ParseError` — it tells you the exact file
and line.

**3. Two fields with same label "Students"?**
That's a pre-existing harmless warning — `student_count` and `student_ids` on
`school.class` both have the string "Students". You could rename one's `string=` to
silence it.

**4. Where do computed values get their data?**
From other fields via `@api.depends`. Change the source → Odoo recomputes → UI updates.

**5. I added a field, why don't I see it?**
You must (a) add it to the model, (b) restart/upgrade, and (c) add it to a view. All
three are required.

---

*Happy building! If a step is still unclear, point me at the exact file/line and I'll
walk through it in even more detail.*
