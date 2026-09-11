# School Management — Diagrams, Structure & Workflow

A visual + plain-English guide to **what's in the project, how it works,
what each piece is, and why we need it.**

> Great for self-study. Every diagram below is written in **Mermaid**, which
> GitHub (and many Markdown viewers) render as a picture automatically.

---

## Table of Contents

1. [The Big Picture — What is this project?](#1-the-big-picture)
2. [Project Folder Tree](#2-project-folder-tree)
3. [Module Load Pipeline (what happens at install)](#3-module-load-pipeline)
4. [Data Flow — Model → View → Menu → Screen](#4-data-flow)
5. [Model Relationships (the school's data map)](#5-model-relationships)
6. ["What is it & Why do we need it" — Cheat Table](#6-what-is-it--why)
7. [How the UI Parts Work Together](#7-how-the-ui-parts-work-together)
8. [The Fix We Just Made (kanban `card`)](#8-the-kanban-card-fix)
9. [Lifecycle: A Feature From Idea to Screen](#9-lifecycle)

---

## 1. The Big Picture

This is an **Odoo module** that turns a generic Odoo install into a **School
Management System**. A "module" is just a folder of code that adds features.
Odoo itself is the engine; modules are the features.

```mermaid
flowchart TB
    subgraph "Odoo (the car engine)"
        O[Odoo Core Framework]
    end

    subgraph "Our Module (the car body/features)"
        M[school_management]
    end

    U[Users: admin, teachers]
    DB[(PostgreSQL Database)]

    U -->|click menus / fill forms| O
    O -->|loads & runs| M
    M -->|reads & writes records| DB
    O -->|saves everything| DB
```

**Why a module?**
- Keeps our code separate from the core (so we don't break Odoo).
- Easy to install/uninstall/share.
- Odoo handles security, menus, forms, database — we just describe what we want.

---

## 2. Project Folder Tree

```mermaid
flowchart TD
    ROOT[custom/school_management/]
    ROOT --> INIT[__init__.py]
    ROOT --> MANIFEST[__manifest__.py]
    ROOT --> MODELS[models/]
    ROOT --> SEC[security/]
    ROOT --> DATA[data/]
    ROOT --> VIEWS[views/]

    MODELS --> MI[__init__.py]
    MODELS --> ST[student.py]
    MODELS --> TE[teacher.py]
    MODELS --> CL[school_class.py]
    MODELS --> SU[subject.py]
    MODELS --> AT[attendance.py]
    MODELS --> EX[exam.py]
    MODELS --> GR[grade.py]
    MODELS --> FE[fee.py]

    SEC --> SX[school_security.xml]
    SEC --> CSV[ir.model.access.csv]

    DATA --> DD[demo_data.xml]

    VIEWS --> STV[student_views.xml]
    VIEWS --> TEV[teacher_views.xml]
    VIEWS --> CLV[class_views.xml]
    VIEWS --> SUV[subject_views.xml]
    VIEWS --> ATV[attendance_views.xml]
    VIEWS --> EXV[exam_views.xml]
    VIEWS --> GRV[grade_views.xml]
    VIEWS --> FEV[fee_views.xml]
    VIEWS --> MENU[menu.xml]

    MANIFEST -.->|"lists every file above"| VIEWS
```

| Folder | What it holds | Why we need it |
|--------|--------------|----------------|
| `__manifest__.py` | The module's ID card + file list | Odoo reads this first to know what to load. |
| `models/` | Python classes = database tables | Defines *what data* we store. |
| `security/` | Groups + access rules | Controls who can see/edit what. |
| `data/` | Sample "demo" records | Pre-fills example data so the UI isn't empty. |
| `views/` | XML = the user interface | Defines *how* data is shown/edited. |

---

## 3. Module Load Pipeline

When you install or upgrade, Odoo follows the `data` list **in order**:

```mermaid
sequenceDiagram
    participant O as Odoo
    participant MAN as __manifest__.py
    participant SEC as security files
    participant DATA as demo_data.xml
    participant VIEW as view files
    participant MENU as menu.xml
    participant DB as Database

    O->>MAN: Read the manifest
    O->>SEC: 1. Create groups + access rights
    O->>DB: create tables (from models/)
    O->>DATA: 2. Insert sample records
    O->>VIEW: 3. Create list/form/kanban/search views
    O->>MENU: 4. Create menus (last, they use the views)
    O->>DB: Save everything
```

**Why this order matters:** Menus point to "actions" defined inside view files,
so views must load **before** menus. Security must load before data so access
rules exist first.

---

## 4. Data Flow

How a click becomes a screen:

```mermaid
flowchart LR
    M[<b>menu.xml</b><br/>School → Students → All Students] --> A[<b>action_student</b><br/>ir.actions.act_window<br/>"show school.student as kanban,list,form"]
    A --> V[<b>view files</b><br/>kanban + list + form + search]
    A --> MO[<b>model</b><br/>school.student (Python)]
    MO --> F[<b>fields</b><br/>name, class_id, photo...]
    F --> DB[(Database table<br/>school_student)]
    V --> SCREEN[User sees the page]
    DB --> V
```

```mermaid
flowchart TB
    userClick[User clicks a menu] --> action[Odoo finds the action]
    action --> turns[Action names the model + view modes]
    turns --> view[Odoo loads the XML views for it]
    view --> read[Views read data from the model]
    model --> table[Model reads/writes the DB table]
    view --> screen[Browser renders the page]
```

**Simple version:** Menu → Action → Views → Model → Database → back to screen.

---

## 5. Model Relationships

Here is how the 8 models connect (the "data map" of the school):

```mermaid
erDiagram
    SCHOOL_CLASS ||--o{ SCHOOL_STUDENT : "has students"
    SCHOOL_CLASS }o--|| SCHOOL_TEACHER : "class teacher"
    SCHOOL_CLASS ||--o{ SCHOOL_ATTENDANCE : "for"
    SCHOOL_CLASS ||--o{ SCHOOL_EXAM : "takes"
    SCHOOL_CLASS ||--o{ SCHOOL_FEE : "pays"

    SCHOOL_STUDENT ||--o{ SCHOOL_ATTENDANCE : "has attendance"
    SCHOOL_STUDENT ||--o{ SCHOOL_GRADE : "gets grades"
    SCHOOL_STUDENT ||--o{ SCHOOL_FEE : "pays fees"

    SCHOOL_TEACHER }o--o{ SCHOOL_SUBJECT : "teaches"
    SCHOOL_CLASS }o--o{ SCHOOL_SUBJECT : "studies"

    SCHOOL_EXAM ||--o{ SCHOOL_GRADE : "has grades"
    SCHOOL_SUBJECT ||--o{ SCHOOL_EXAM : "exam for"
    SCHOOL_SUBJECT ||--o{ SCHOOL_GRADE : "grade for"

    SCHOOL_EXAM ||--o{ SCHOOL_GRADE : "produce"
```

**In plain words:**
- A **Class** has many **Students**, one **Teacher**, many **Subjects**.
- A **Student** belongs to one **Class**, has many **Attendances**, **Grades**, **Fees**.
- A **Teacher** teaches many **Subjects** and is the teacher of many Classes.
- An **Exam** belongs to a **Subject** + **Class** and produces many **Grades**.
- A **Grade** links a Student + Exam + Subject.

| Relation type | Odoo field | Example |
|---------------|-----------|---------|
| One-to-many (one class → many students) | `One2many` / `Many2one` | `class_id` on student |
| Many-to-many (teacher ↔ subject) | `Many2many` | `subject_ids` on teacher |

---

## 6. "What is it & Why"

| Part | What it is | Why we need it |
|------|-----------|----------------|
| **Model** (`models/*.py`) | A Python class that becomes a DB table | The "shape" of our data; without it there's nothing to store. |
| **Field** (`fields.Char`, `fields.Many2one`...) | A column of the table | Defines one piece of info (name, date, amount...). |
| **Computed field** | A column calculated from other fields | e.g. `age`, `percentage`, `capacity_progress` — no one types them. |
| **Relation field** | `Many2one`/`One2many`/`Many2many` | Connects records (student→class, teacher→subject). |
| **View** (`views/*.xml`) | XML describing a screen | Tells Odoo how to *display* the data. |
| **List view** | A table of rows | Quick scan/edit many records. |
| **Form view** | One record, full detail | Create/edit a single record. |
| **Kanban view** | Cards (like a board) | Nice visual browsing of records/photos. |
| **Search view** | Search bar + filters | Find records fast. |
| **Action** (`ir.actions.act_window`) | A "go here and show this" bundle | Fasoules model + view modes into one clickable target for menus. |
| **Menu** (`views/menu.xml`) | Navigation item | Lets users *find* the feature. |
| **Security group** | A named role | e.g. "School Administrator" — controls access. |
| **Access rule (CSV)** | Permissions (read/write/create/delete) | Stops people seeing/editing what they shouldn't. |
| **Demo data** (`data/demo_data.xml`) | Sample records | Fills the UI so you can see it working. |

---

## 7. How the UI Parts Work Together

```mermaid
flowchart LR
    subgraph OneModel["school.student"]
        L1[List: table of students]
        K1[Kanban: cards with photo + badges]
        F1[Form: full edit + stat buttons]
        S1[Search: search bar + filters]
    end

    A1[action_student] --> L1
    A1 --> K1
    A1 --> F1
    A1 --> S1

    K1 -->|click card| F1
```

Every model typically gets 4 views + 1 action. The action decides the order
(`kanban,list,form`). Menus point to the action.

---

## 8. The Kanban Card Fix

Remember the `Missing 'card' template` error? Here's the visual:

```mermaid
flowchart TD
    BAD["<b>WRONG</b> (older Odoo guides)<br/><t t-name='kanban-box'>"] --> P[KanbanArchParser<br/>looks for templateDocs['card']]
    P --> MISSING["templateDocs['card'] = undefined"]
    MISSING --> ERROR["🚨 Error: Missing 'card' template."]

    GOOD["<b>CORRECT</b> (Odoo 19)<br/><t t-name='card'>"] --> P2[KanbanArchParser<br/>finds templateDocs['card']]
    P2 --> WORKS["✅ Card renders"]
```

**Rule:** On this Odoo version, the card template **must** be named
`t-name="card"` (not `kanban-box`). Every field used inside the template must
also be listed at the top of `<kanban>`.

---

## 9. Lifecycle: A Feature From Idea to Screen

Let's trace one feature — **"view student photos in cards"**:

```mermaid
flowchart TD
    STEP1[1. Add photo field to model<br/>photo = fields.Image] --> STEP2
    STEP2[2. Add photo to kanban field list<br/>field name='photo'] --> STEP3
    STEP3[3. Use it in the card template<br/>img t-if='record.photo.raw' t-attf-src=...] --> STEP4
    STEP4[4. Action includes kanban mode<br/>view_mode='kanban,list,form'] --> STEP5
    STEP5[5. Menu points to that action] --> STEP6
    STEP6[6. Re-load module -u school_management] --> STEP7
    STEP7[7. Hard-refresh browser<br/>Ctrl+Shift+R] --> DONE["✅ Users see photo cards"]
```

**The golden rule:** to see any change you need ALL of
(1) edit model, (2) edit view, (3) reload module, (4) refresh browser.

---

## Quick Recap

- **Model** = what data we store (Python).
- **View** = how we show it (XML).
- **Action** = bundles a model + its views for a menu.
- **Menu** = where users find it.
- **Security** = who's allowed.
- **Demo data** = sample content.
- To change anything: **edit → `-u module` → hard-refresh**.

---

*Want a different diagram (e.g. sequence of a specific page, or an entity
diagram with real field names)? Just ask which one and I'll add it.*
