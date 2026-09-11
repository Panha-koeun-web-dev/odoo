# Fix Guide — "Missing 'card' template" OwlError

**Where:** `custom/school_management/views/*_views.xml`
**Symptoms:** Clicking a School menu page (Students, Teachers, Classes,
Attendance, Grades, Fees) opens a kanban view and the browser shows:

```
OwlError: An error occured in the owl lifecycle
Caused by: Error: Missing 'card' template.
    at KanbanArchParser.parse (kanban_arch_parser.js)
```

---

## What the error actually means

Odoo builds the kanban "card" from a template tag inside `<templates>`.
The client-side parser (`KanbanArchParser.parse`) looks for a template whose
`t-name` is **`card`**:

```js
// addons/web/static/src/views/kanban/kanban_arch_parser.js
export const KANBAN_CARD_ATTRIBUTE = "card";
...
const cardDoc = templateDocs[KANBAN_CARD_ATTRIBUTE];   // templateDocs["card"]
if (!cardDoc) {
    throw new Error(`Missing '${KANBAN_CARD_ATTRIBUTE}' template.`);
}
```

If it cannot find a `<t t-name="card">`, it throws exactly
`Missing 'card' template.`

> ⚠️ **Important:** This Odoo version (19) uses **`card`** as the template name.
> Older/stock Odoo guides show **`kanban-box`** — that name is **wrong** on this
> build and produces this exact error.

---

## The one-line fix

Find every kanban view and change the card template's `t-name`:

**Before (WRONG):**
```xml
<templates>
    <t t-name="kanban-box">      <!-- ← this name is wrong on Odoo 19 -->
        <div class="oe_kanban_global_click">...</div>
    </t>
</templates>
```

**After (CORRECT):**
```xml
<templates>
    <t t-name="card">            <!-- ← Odoo 19 requires "card" -->
        <div class="oe_kanban_global_click">...</div>
    </t>
</templates>
```

### Files to fix (all 6 kanban views in this project)

| File | Search for |
|------|-----------|
| `views/student_views.xml` | `t-name="kanban-box"` |
| `views/teacher_views.xml` | `t-name="kanban-box"` |
| `views/class_views.xml` | `t-name="kanban-box"` |
| `views/attendance_views.xml` | `t-name="kanban-box"` |
| `views/grade_views.xml` | `t-name="kanban-box"` |
| `views/fee_views.xml` | `t-name="kanban-box"` |

Replace `t-name="kanban-box"` with `t-name="card"` in each.

---

## Other things that can ALSO break the card (check these too)

Even with the correct name, the card template fails to build if it references a
field that is not declared in the kanban's field list, or uses unsupported syntax.

### 1. Every field you call in the template MUST be listed at the top of the kanban

```xml
<kanban>
    <field name="capacity"/>     <!-- ← must be listed here if used in the template -->
    <field name="student_count"/>
    <templates>
        <t t-name="card">
            ... <field name="capacity"/> ...   <!-- used here -->
        </t>
    </templates>
</kanban>
```
Missing declaration example that caused this project's Class page to break:
the template used `<field name="capacity"/>` but `capacity` was not in the
`<field>` list. **Solution:** add `<field name="capacity"/>` at the top.

### 2. Avoid `bg_color` with ternary expressions on `<field widget="badge">` inside the template

`bg_color="gender == 'male' ? '...' : '...'"` on a `<field>` **inside** a kanban
template can fail to compile. Prefer a `<span>` with `t-att-class`:

```xml
<!-- Prefer this (safe): -->
<span t-att-class="'badge ' + ('bg-teal-200 text-teal-900' if record.gender.raw == 'male' else 'bg-pink-200 text-pink-900')">
    <field name="gender"/>
</span>
```

(Note: `bg_color` on `<field>` is fine in **form** views — only avoid it inside
kanban templates.)

### 3. Use `t-attf-src` (not `t-att-src`) for images

```xml
<!-- Safe standard pattern: -->
<img t-if="record.photo.raw" t-attf-src="data:image/png;base64,#{record.photo.raw}"/>
```

---

## After editing: reload the module, then hard-refresh

View changes only take effect after the module is re-loaded and the browser
picks up new assets.

```powershell
cd C:\Users\USER\Desktop\odoo
.venv\Scripts\python.exe odoo-bin -c odoo.conf -d testing_db -u school_management --stop-after-init
```

Then in the browser do a **hard refresh** to clear the cached JS:
- Windows / Chrome / Firefox: **Ctrl + Shift + R**

---

## How to find every problem kanban quickly

1. Grep for the wrong template name:
   ```powershell
   Select-String -Path custom\school_management\views\*.xml -Pattern 't-name="kanban-box"'
   ```
   (Should return nothing after you fix it.)

2. Grep for `bg_color` inside a kanban `<templates>` block and convert those to
   `t-att-class` spans.
   ```powershell
   Select-String -Path custom\school_management\views\*.xml -Pattern 'bg_color'
   ```

3. Verify every field used in a template exists in that kanban's top-level
   `<field ...>` list.

---

## Quick reference

| Troubleshooting check | Command / action |
|----------------------|------------------|
| Wrong card name | `t-name="kanban-box"` → `t-name="card"` |
| Field used but not declared | Add `<field name=.../>` at top of `<kanban>` |
| `bg_color` ternary in template | Convert to `<span t-att-class="...">` |
| Image in kanban | Use `t-attf-src="data:image/png;base64,#{record.x.raw}"` |
| Reload views | `-u school_management --stop-after-init` |
| Clear cache | Browser hard refresh `Ctrl+Shift+R` |
