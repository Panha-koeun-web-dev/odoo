# Building the Login Page for the School Management App

## 1. Understand the Current State

This project is **Odoo 19.0** with a custom module **`school_management`** located at `custom/school_management/`. 

**Key fact:** Odoo already ships a complete, built-in login system. There is **no custom login page** in `school_management` today — it relies entirely on Odoo's default `/web/login` page. Before writing any new code, decide *what kind* of login you actually want:

| Goal | Approach |
|------|----------|
| Only restyle/rebrand the default login | Inherit the existing `web.login` template (simplest, recommended) |
| A fully custom front-end login page (own URL, own form) | Write a new controller + template + custom asset bundle |
| Role-based login experience (admin/teacher/student) | Extend the role groups in `school_security.xml` and hook routing after login |

> **Recommendation:** Unless you specifically need a completely separate front-end (website) login, build a themed version of Odoo's default login by **inheriting `web.login`**. Odoo handles passwords, CSRF, sessions, and redirects for you — you only customize appearance and branding.

---

## 2. How Odoo's Login Works (the pieces you must know)

### 2.1 The login templates
File: `addons/web/views/webclient_templates.xml`

- **`web.login_layout`** (line 110) — the outer page shell: logo header, centered card, footer links ("Manage Databases" / "Powered by Odoo").
- **`web.login`** (line 136) — the actual login form. Posts to `/web/login` with fields:
  - `csrf_token` (hidden)
  - `login` (text input, the email/username)
  - `password` (password input)
  - `redirect` (hidden)
  - `type` = `password` (hidden)
- **`web.login_successful`** (line 190) — the "You are logged in" page for external/portal users.
- **`web.login_oauth`** (line 203) — optional OAuth buttons block.

The form posts `login`, `password`, `csrf_token`, `redirect`, and `type` to the `/web/login` route.

### 2.2 The login controller
File: `addons/web/controllers/home.py`, method `web_login` (line 103–154).

```python
@http.route('/web/login', type='http', auth='none', readonly=False, list_as_website_content=_lt("Login"))
def web_login(self, redirect=None, **kw):
    ...
    if request.httprequest.method == 'POST':
        try:
            credential = {key: value for key, value in request.params.items()
                          if key in CREDENTIAL_PARAMS and value}
            credential.setdefault('type', 'password')
            auth_info = request.session.authenticate(request.env, credential)
            request.params['login_success'] = True
            return request.redirect(self._login_redirect(auth_info['uid'], redirect=redirect))
        except odoo.exceptions.AccessDenied as e:
            ...
    ...
    response = request.render('web.login', values)
```

- **GET** → renders the login form.
- **POST** → authenticates via `request.session.authenticate(...)`, then redirects.
- On failure → renders `web.login` again with a `values['error']` message.

### 2.3 The authentication internals
- User model: `base` module `res.users` (`addons/base/models/res_users.py`), uses `passlib` for password hashing.
- The `web` addon extends `res.users` (`addons/web/models/res_users.py`) with helpers like `_should_captcha_login`.
- Session/route auth happens in `odoo/http.py` (`Request.authenticate`, auth dispatch).

### 2.4 Existing example of inheritance
`addons/auth_signup/views/auth_signup_login_templates.xml` shows how other modules customize the login:

```xml
<template id="auth_signup.login" inherit_id="web.login" name="Sign up - Reset Password">
    <xpath expr="//div[hasclass('oe_login_buttons')]/button" position="after">
        <a t-if="signup_enabled" class="btn btn-link btn-sm mt-2"
           t-attf-href="/web/signup?{{ keep_query() }}">Don't have an account?</a>
    </xpath>
    ...
</template>
```

This is the pattern to copy.

---

## 3. Recommended Approach: Theme the Default Login

Create a new XML template file in the module that inherits `web.login`. Steps:

### Step A — Create the template file
Create `custom/school_management/views/login_templates.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Inherit the default login form and customize it -->
    <template id="school_login" inherit_id="web.login" name="School Login">
        <!-- Add a welcome/header message inside the card -->
        <xpath expr="//div[hasclass('oe_login_form')]" position="before">
            <div class="text-center pb-3 mb-2">
                <h3 class="mb-1">Welcome to School Management</h3>
                <p class="text-muted mb-0">Sign in to your account</p>
            </div>
        </xpath>

        <!-- Move the "Log in" button text / tweak button styling -->
        <xpath expr="//div[hasclass('oe_login_buttons')]/button" position="attributes">
            <attribute name="class">btn btn-primary w-100</attribute>
        </xpath>
    </template>
</odoo>
```

### Step B — Add SCSS for a theme
Create `static/src/login/login.scss` for any custom styles (backgrounds, logo sizing, colors):

```scss
// Example snippet — adjust to taste
body.bg-100 {
    background: #f4f6f9;
}
.o_database_list {
    box-shadow: 0 1rem 3rem rgba(0, 0, 0, .175);
}
```

### Step C — Register the files in `__manifest__.py`
Add the new view to `data` and the SCSS to the existing `web.assets_backend` bundle (assets used at login come from the backend bundle):

```python
'data': [
    'security/school_security.xml',
    'security/ir.model.access.csv',
    'views/login_templates.xml',          # <-- add this (before your main views is fine)
    'views/student_views.xml',
    ...
],
'assets': {
    'web.assets_backend': [
        'school_management/static/src/sidebar/sidebar.js',
        'school_management/static/src/sidebar/sidebar.scss',
        'school_management/static/src/login/login.scss',   # <-- add this
    ],
},
```

> Note: Odoo login renders using **`web.assets_backend`** when it sees a session, so putting login styles there works. Do **not** add them to `web.assets_frontend` for a backend-style school app.

### Step D — Update the module
On the running server:
1. Stop the server.
2. `python odoo-bin -u school_management -c odoo.conf` (upgrade the module so new data/views/assets load).
3. Restart the server and open `http://localhost:8069/web/login`.

---

## 4. Alternative: A Fully Custom Login Page

Only needed if you want a *separate* login flow with its own URL (e.g., a public website front-end at `/school/login`).

### 4.1 Write a controller
Create `custom/school_management/controllers/login.py`:

```python
from odoo import http
from odoo.http import request


class SchoolLoginController(http.Controller):

    @http.route('/school/login', type='http', auth='none', website=True, sitemap=False)
    def school_login(self, **kw):
        if request.session.uid:
            return request.redirect('/web')
        error = ''
        if request.httprequest.method == 'POST':
            login = kw.get('login', '')
            password = kw.get('password', '')
            try:
                request.session.authenticate(request.env, {
                    'type': 'password', 'login': login, 'password': password})
                return request.redirect('/web')
            except Exception:
                error = "Wrong login/password"
        return request.render('school_management.school_login_page',
                              {'error': error})
```

Register it in `custom/school_management/controllers/__init__.py` and add `controllers` to the package. Then add `'controllers'` to the module by importing it in `custom/school_management/__init__.py`.

### 4.2 Write a custom QWeb page
Create `custom/school_management/views/login_page_templates.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="school_login_page" name="School Login Page">
        <t t-call="web.frontend_layout">
            <t t-set="no_header" t-value="True"/>
            <t t-set="no_footer" t-value="True"/>
            <div class="container" style="max-width: 420px; margin-top: 10vh;">
                <div class="card border-0 shadow">
                    <div class="card-body p-4">
                        <h3 class="text-center mb-4">School Login</h3>
                        <form method="post" action="/school/login">
                            <input type="hidden" name="csrf_token"
                                   t-att-value="request.csrf_token()"/>
                            <div class="mb-3">
                                <label class="form-label">Email</label>
                                <input type="text" name="login" class="form-control"
                                       required="required" autofocus="autofocus"/>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input type="password" name="password"
                                       class="form-control" required="required"/>
                            </div>
                            <p class="alert alert-danger" t-if="error"><t t-esc="error"/></p>
                            <button type="submit" class="btn btn-primary w-100">Log in</button>
                        </form>
                        <p class="text-center mt-3 mb-0">
                            <a href="/web/login">Back to Odoo login</a>
                        </p>
                    </div>
                </div>
            </div>
        </t>
    </template>
</odoo>
```

### 4.3 Register in manifest
Add `'controllers/login.py'` handling in `__init__.py`, and add `views/login_page_templates.xml` to `data`.

> **Caveat:** Writing a custom login from scratch means *you* now own session handling, error messages, `redirect` handling, CSRF, and post-login routing. For ~95% of apps, approach #3 (theming the built-in login) is the better choice.

---

## 5. Connecting Login to the Role Groups

`school_management` already defines three groups in `security/school_security.xml` (lines 2–12):

- `group_school_admin`
- `group_school_teacher`
- `group_school_student`

These groups exist **but are not yet wired into access/menus**, and no login routing uses them. To make the login "role-aware":

1. Add `implied_ids`/parentage in `school_security.xml` if you want hierarchy (e.g., admin implies teacher).
2. Override the post-login redirect per role by overriding `_login_redirect` in `res.users`:

```python
from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_login_redirect_url(self, uid, redirect=None):
        if redirect and redirect not in ('', '/web'):
            return redirect
        user = self.browse(uid)
        if user.has_group('school_management.group_school_student'):
            return '/web'  # or a student dashboard route
        if user.has_group('school_management.group_school_teacher'):
            return '/web#action=school_management.school_teacher_action'
        return '/web'
```

> Tip: if you later make separate student/teacher dashboards, point each group to its own `ir.actions.act_window` action instead of hard-coded strings.

---

## 6. Common Gotchas (learned from this repo)

1. **Strict XML schema** — This build enforces strict validation (`odoo/addons/base/rng/`). Avoid invalid attributes in views (e.g., don't put `bg_color`/`progress` in list/search views — only form/kanban). Keep your login template simple.
2. **CSRF is mandatory** — Every `method="post"` form in Odoo must include:
   ```xml
   <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
   ```
   Omit it → you'll get a 400 CSRF error.
3. **`t-attf-*` vs literal attributes** — When injecting runtime values, use `t-attf-` (`/web/login?{{ keep_query() }}`), not plain `href`.
4. **Assets/caching** — After editing SCSS or XML, run `-u school_management` (and `--dev=all` during dev) so asset bundles refresh. Otherwise you'll see stale styles.
5. **`admin`/`admin`** is the current login (per `odoo.conf`: db `testing_db`, addons_path includes `custom`).
6. **Backend bundle** — Styles for the login page belong in `web.assets_backend`, not `web.assets_frontend`, for a backend app.

---

## 7. Files You'll Add/Modify (quick checklist)

**Approach #3 (theming built-in login):**
- ✅ New: `custom/school_management/views/login_templates.xml`
- ✅ New: `custom/school_management/static/src/login/login.scss`
- ✅ Edit: `custom/school_management/__manifest__.py` (add view to `data`, scss to assets)

**Approach #4 (custom login page):**
- ✅ New: `custom/school_management/controllers/__init__.py`
- ✅ New: `custom/school_management/controllers/login.py`
- ✅ New: `custom/school_management/views/login_page_templates.xml`
- ✅ Edit: `custom/school_management/__init__.py` (import controllers)
- ✅ Edit: `custom/school_management/__manifest__.py`

**Role-aware routing (optional, either approach):**
- ✅ Edit: `custom/school_management/models/res_users.py` (new file) overriding `_get_login_redirect_url`

**Server steps every time:**
```
python odoo-bin -u school_management -c odoo.conf
python odoo-bin -c odoo.conf   # restart server
# open http://localhost:8069/web/login
```

---

## 8. Decision Summary

- **Want a fast, robust, branded login that reuses Odoo's security?** → Approach #3 (inherit `web.login` + SCSS). This is the **recommended** path for the School Management app.
- **Want a totally separate public login URL with full control of markup?** → Approach #4 (new controller + template).
- **Want per-role destinations after login?** → Add the `_get_login_redirect_url` override alongside either approach.
