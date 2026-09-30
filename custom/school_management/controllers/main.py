# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class SchoolHome(Home):

    def _login_redirect(self, uid, redirect=None):
        user = request.env['res.users'].sudo().browse(uid)
        is_student = (
            user.has_group('school_management.group_school_student')
            and not user.has_group('school_management.group_school_teacher')
            and not user.has_group('school_management.group_school_admin')
        )
        is_teacher = (
            user.has_group('school_management.group_school_teacher')
            and not user.has_group('school_management.group_school_admin')
        )

        action_student = request.env.ref('school_management.action_student', raise_if_not_found=False)
        action_timetable = request.env.ref('school_management.action_timetable', raise_if_not_found=False)

        # 1. If Student: Redirect directly to Unified Timetable & Master Calendar
        if is_student:
            # Override if no redirect, generic root redirect, or stale redirect to student action
            if not redirect or redirect in ('/odoo', '/web', '/', '/web/login', '/odoo/action-') or (action_student and f'action-{action_student.id}' in str(redirect)):
                if action_timetable:
                    return f'/odoo/action-{action_timetable.id}'

        # 2. If Teacher: Redirect to Timetable
        elif is_teacher:
            if not redirect or redirect in ('/odoo', '/web', '/', '/web/login', '/odoo/action-'):
                if action_timetable:
                    return f'/odoo/action-{action_timetable.id}'

        return super()._login_redirect(uid, redirect=redirect)

    @http.route(['/web', '/odoo', '/odoo/<path:subpath>', '/scoped_app/<path:subpath>'], type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        if request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid)
            is_student = (
                user.has_group('school_management.group_school_student')
                and not user.has_group('school_management.group_school_teacher')
                and not user.has_group('school_management.group_school_admin')
            )
            if is_student:
                action_student = request.env.ref('school_management.action_student', raise_if_not_found=False)
                action_timetable = request.env.ref('school_management.action_timetable', raise_if_not_found=False)
                current_path = request.httprequest.path or ''
                # Redirect if on root or trying to load restricted student action page
                if current_path in ('/odoo', '/web', '/odoo/') or (action_student and f'action-{action_student.id}' in current_path):
                    if action_timetable:
                        return request.redirect(f'/odoo/action-{action_timetable.id}', 303)
        return super().web_client(s_action=s_action, **kw)
