# Role & Permission Guide — School Management System

This guide explains how role-based access control (RBAC) and permissions work in the **School Management** system (`custom/school_management`), and provides step-by-step instructions on how to configure and assign user roles.

---

## 1. Security Architecture Overview

The system uses Odoo 19's multi-layered security architecture:

```
┌────────────────────────────────────────────────────────┐
│                   1. Security Groups                   │
│         (res.groups: Student, Teacher, Admin)          │
└───────────────────────────┬────────────────────────────┘
                            │
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌────────────────┐
│2. Model Access│   │3. Record Rules│   │ 4. UI / Menus  │
│(ir.model.access)  │   (ir.rule)   │   │  (menu & view) │
│  CRUD matrix  │   │ Row-level row │   │ Visible buttons│
│  per model    │   │  isolation    │   │   and screens  │
└───────────────┘   └───────────────┘   └────────────────┘
```

1. **Security Groups (`res.groups`)**: Defined in `security/school_security.xml`. Represents job functions (Student, Teacher, Administrator).
2. **Model Access Rights (`ir.model.access.csv`)**: Defines table-level permissions: **Create (C)**, **Read (R)**, **Write/Update (W)**, and **Unlink/Delete (D)**.
3. **Record Rules (`ir.rule`)**: Row-level filtering. Ensures students only see their own grades, attendance, certificates, and invoices, while teachers and admins see broader data.
4. **UI & Menu Restrictions (`groups="..."`)**: Controls which navigation menus, action buttons, and form fields are visible to which roles.

---

## 2. Role Hierarchy & Built-In Groups

The module defines 3 hierarchical groups:

```
  School / Administrator  (group_school_admin)
           ▲
           │ inherits
  School / Teacher        (group_school_teacher)
           ▲
           │ inherits
  School / Student        (group_school_student)
           ▲
           │ inherits
  Internal User           (base.group_user)
```

| Group XML ID | Group Name | Inherits (Implied Groups) | Assigned Users by Default |
|---|---|---|---|
| `school_management.group_school_student` | **School / Student** | `base.group_user` | None (created dynamically) |
| `school_management.group_school_teacher` | **School / Teacher** | `group_school_student` | None (created dynamically) |
| `school_management.group_school_admin` | **School / Administrator** | `group_school_teacher` | `base.user_root`, `base.user_admin` (`admin`) |

> **Note on Inheritance:** Because groups inherit upwards, an **Administrator** automatically has all rights of a **Teacher** and **Student**. A **Teacher** automatically has all basic rights of a **Student**.

---

## 3. Permissions Matrix

### 3.1 Model Access Rights (CRUD)

| Model | Model Name | Student | Teacher | Administrator |
|---|---|:---:|:---:|:---:|
| `school.student` | Student Profiles | R | R, W | **R, W, C, D** |
| `school.teacher` | Teacher Profiles | R | R | **R, W, C, D** |
| `school.class` | Classes / Classrooms | R | R | **R, W, C, D** |
| `school.subject` | Subjects / Courses | R | R | **R, W, C, D** |
| `school.attendance` | Attendance Records | R | **R, W, C** | **R, W, C, D** |
| `school.exam` | Examinations | R | **R, W, C** | **R, W, C, D** |
| `school.grade` | Exam Grades / Results | R | **R, W, C** | **R, W, C, D** |
| `school.certificate` | Certificates | R | R | **R, W, C, D** |
| `school.fee` | Fee Templates / Invoices | R | R | **R, W, C, D** |
| `school.student.year.payment` | Year Payments & Tuition | R | R | **R, W, C, D** |
| `school.enrollment` | Class Enrollments | R | R | **R, W, C, D** |
| `school.major` | Majors / Academic Programs| R | R | **R, W, C, D** |
| `school.major.enrollment` | Major Enrollments | R | R | **R, W, C, D** |
| `school.dashboard` | Dashboard Metrics | R | R | **R, W, C, D** |
| *Wizards* (Daily Attendance, Stop Study, Payment, Exams) | Wizards & Dialogs | — | R, W, C, D | **R, W, C, D** |

*Legend: **R** = Read, **W** = Write/Edit, **C** = Create, **D** = Delete (Unlink).*

---

### 3.2 Data Isolation & Record Rules (Row-Level Security)

Even if a user has **Read** access on a table, Record Rules filter *which rows* they are permitted to view:

| Target Model | Role | Record Rule Domain | Description |
|---|---|---|---|
| `school.student` | **Student** | `[('user_id', '=', user.id)]` | Student only sees **their own** profile. |
| | **Teacher** | `[(1, '=', 1)]` | Teacher can read and write all students. |
| | **Admin** | `[(1, '=', 1)]` | Admin has full unrestricted access. |
| `school.grade` | **Student** | `[('student_id.user_id', '=', user.id)]` | Student only sees **their own** grades. |
| | **Teacher** | `[(1, '=', 1)]` | Teacher can grade any student. |
| | **Admin** | `[(1, '=', 1)]` | Full access. |
| `school.attendance`| **Student** | `[('student_id.user_id', '=', user.id)]` | Student only sees **their own** attendance logs. |
| | **Teacher** | `[(1, '=', 1)]` | Teacher records/views all attendance. |
| | **Admin** | `[(1, '=', 1)]` | Full access. |
| `school.student.year.payment` | **Student** | `[('student_id.user_id', '=', user.id)]` | Student only views **their own** tuition and receipts. |
| | **Teacher** | `[(1, '=', 1)]` | Teacher has read-only view of payment status. |
| | **Admin** | `[(1, '=', 1)]` | Full management of payments and receipts. |
| `school.certificate` | **Student** | `[('student_id.user_id', '=', user.id)]` | Student only views **their own** certificates. |
| `school.class` | **Student** | `[('student_ids.user_id', '=', user.id)]` | Student only sees classes they are **enrolled in**. |
| `school.exam` | **Student** | `[('class_id.student_ids.user_id', '=', user.id)]` | Student only sees exams for their enrolled classes. |

---

### 3.3 Menu Navigation Access

Menu items in `views/menu.xml` are conditionally rendered based on group membership:

| Menu Item | Student | Teacher | Administrator |
|---|:---:|:---:|:---:|
| **Dashboard** | ❌ Hidden | ✅ Visible | ✅ Visible |
| **Students** (List & Kanban) | ✅ Filtered to Self | ✅ All Students | ✅ All Students |
| **Teachers** | ❌ Hidden | ✅ Visible | ✅ Visible |
| **Academics → Classes** | ✅ Enrolled Only | ✅ Visible | ✅ Visible |
| **Academics → Subjects** | ✅ Visible | ✅ Visible | ✅ Visible |
| **Academics → Majors** | ❌ Hidden | ❌ Hidden | ✅ Visible |
| **Academics → Major Enrollments** | ❌ Hidden | ❌ Hidden | ✅ Visible |
| **Examinations → Exams** | ✅ Enrolled Only | ✅ Visible | ✅ Visible |
| **Examinations → Grades** | ✅ Own Grades Only | ✅ Visible | ✅ Visible |
| **Attendance Records** | ✅ Own Attendance | ✅ Visible | ✅ Visible |
| **Certificates** | ✅ Own Certificates | ✅ Visible | ✅ Visible |
| **Fees** | ❌ Hidden | ❌ Hidden | ✅ Visible |
| **Student Year Payment** | ✅ Own Payments | ❌ Hidden | ✅ Visible |
| **Enrollments** | ❌ Hidden | ❌ Hidden | ✅ Visible |

---

## 4. How to Assign Roles to Users

There are 3 ways to assign roles in this system:

### Option A: Direct 1-Click Provisioning (Recommended for Daily Operations)

The `school_management` module includes automated provisioning buttons built directly into forms.

#### 1. Assigning a Student Role:
1. Log in as an Administrator (`admin`).
2. Navigate to **School → Students**.
3. Open any student's record (ensure the student has a valid **Email** set).
4. In the top header bar, click **"Create Login Account"**:
   - The system automatically creates a `res.users` account using the student's email as the login.
   - It sets the default password to `password123`.
   - It automatically assigns the **School / Student** security group.
   - It links the user account back to `student.user_id`.
5. If the student forgets their password, click **"Reset Password"** in the header to reset it back to `password123`.

#### 2. Assigning a Teacher Role:
1. Navigate to **School → Teachers**.
2. Open a teacher record (ensure their **Email** is populated).
3. In the top header bar, click **"Create User"**:
   - The system creates a user with `res.users` credentials.
   - It automatically attaches the **School / Teacher** security group.
   - It sets `teacher.user_id` to the created user.

---

### Option B: Via Standard Odoo Settings UI (Manual Assignment)

To manually create a user or change an existing user's role:

1. Log in as an Administrator (`admin`).
2. Go to **Settings** from the main app switcher.
3. Select **Users & Companies → Users**.
4. Click **New** (or select an existing user).
5. Enter user details:
   - **Name**: User's full name.
   - **Email Address / Login**: Their login handle.
6. Scroll down to the **Access Rights** tab:
   - Locate the **School** application section.
   - Select one of the roles:
     - `School / Student`
     - `School / Teacher`
     - `School / Administrator`
7. Click **Save**.
8. Set a password via the top **Action (gear icon) → Change Password**.

---

### Option C: Via Python / Odoo Shell (Automated Scripts)

To assign roles programmatically via script or the Odoo interactive shell:

```bash
# Start Odoo shell
.venv/Scripts/python.exe odoo-bin shell -c odoo.conf -d testing_db
```

```python
# In the Python shell:
# 1. Fetch group references
group_student = env.ref('school_management.group_school_student')
group_teacher = env.ref('school_management.group_school_teacher')
group_admin   = env.ref('school_management.group_school_admin')

# 2. Find the user
user = env['res.users'].search([('login', '=', 'teacher.jane@school.edu')], limit=1)

# 3. Assign the Teacher role
user.write({
    'groups_id': [(4, group_teacher.id)]
})

env.cr.commit()
print("Role successfully updated.")
```

---

## 5. Developer Guide: Modifying or Adding Roles

If you need to customize permissions or add a new role (e.g. `School / Accountant` or `School / Parent`):

### Step 1: Define the New Group in `security/school_security.xml`
```xml
<record id="group_school_accountant" model="res.groups">
    <field name="name">School / Accountant</field>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
</record>
```

### Step 2: Grant Model Access in `security/ir.model.access.csv`
Add lines specifying Read, Write, Create, and Delete rights:
```csv
access_accountant_fee,accountant.fee,model_school_fee,school_management.group_school_accountant,1,1,1,0
access_accountant_year_payment,accountant.payment,model_school_student_year_payment,school_management.group_school_accountant,1,1,1,0
```

### Step 3: Add Record Rules (If row filtering is required)
In `security/school_security.xml`:
```xml
<record id="rule_school_fee_accountant" model="ir.rule">
    <field name="name">Accountant: Manage All Fees</field>
    <field name="model_id" ref="model_school_fee"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('group_school_accountant'))]"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_unlink" eval="0"/>
</record>
```

### Step 4: Expose Menus or Buttons
In `views/menu.xml` or views:
```xml
<menuitem id="menu_school_fee" name="Fees"
          parent="menu_school_root"
          action="action_fee"
          groups="school_management.group_school_admin,school_management.group_school_accountant"
          sequence="60"/>
```

### Step 5: Upgrade the Module
Any modifications to XML, CSV, or Python require upgrading the module to take effect:
```powershell
.venv\Scripts\python.exe odoo-bin -c odoo.conf -d testing_db -u school_management --stop-after-init
```
Then restart the Odoo server.

---

## 6. Verification Checklist

When verifying user role configurations:

| Test Case | Expected Result |
|---|---|
| **Login as Student** | Cannot see Fees, Teachers, Enrollments, Majors, or Dashboard. Can only see own grades and attendance. |
| **Student Record Leak Check** | Navigating to `/web#action=school_management.action_student` shows only 1 row (the logged-in student's own record). |
| **Login as Teacher** | Sees Dashboard, Teachers, Students, Classes, Attendance, Grades. Cannot delete students, modify tuition settings, or manage system fees. |
| **Login as Administrator** | Full visibility to all menus, student stop/kick wizards, payment deadline wizards, and configuration. |

---

## 7. Key File Locations

- **Group Definitions & Record Rules**: `custom/school_management/security/school_security.xml`
- **Table / Model Access Lists**: `custom/school_management/security/ir.model.access.csv`
- **Menu Visibility Rules**: `custom/school_management/views/menu.xml`
- **Student User Provisioning Logic**: `custom/school_management/models/student.py` (`action_create_user`)
- **Teacher User Provisioning Logic**: `custom/school_management/models/teacher.py` (`action_create_user`)
