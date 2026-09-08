# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class SchoolHome(Home):

    def _login_redirect(self, uid, redirect=None):
        if not redirect or redirect in ('/odoo', '/web', '/', '/web/login', '/odoo/action-'):
            user = request.env['res.users'].sudo().browse(uid)
            # 1. If Student: Redirect directly to their own student profile account page!
            if (user.has_group('school_management.group_school_student')
                    and not user.has_group('school_management.group_school_teacher')
                    and not user.has_group('school_management.group_school_admin')):
                student = request.env['school.student'].sudo().search([('user_id', '=', uid)], limit=1)
                action = request.env.ref('school_management.action_student', raise_if_not_found=False)
                if student and action:
                    return f'/odoo/action-{action.id}/{student.id}'
                elif action:
                    return f'/odoo/action-{action.id}'

            # 2. If Teacher: Redirect to the student list!
            elif (user.has_group('school_management.group_school_teacher')
                  and not user.has_group('school_management.group_school_admin')):
                action = request.env.ref('school_management.action_student', raise_if_not_found=False)
                if action:
                    return f'/odoo/action-{action.id}'

        return super()._login_redirect(uid, redirect=redirect)

    @http.route(['/web', '/odoo', '/odoo/<path:subpath>', '/scoped_app/<path:subpath>'], type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        # If user is logged in, and visited root '/odoo' or '/web' without specific subpath
        if request.session.uid and request.httprequest.path in ('/odoo', '/web', '/odoo/'):
            user = request.env['res.users'].sudo().browse(request.session.uid)
            if (user.has_group('school_management.group_school_student')
                    and not user.has_group('school_management.group_school_teacher')
                    and not user.has_group('school_management.group_school_admin')):
                student = request.env['school.student'].sudo().search([('user_id', '=', user.id)], limit=1)
                action = request.env.ref('school_management.action_student', raise_if_not_found=False)
                if student and action:
                    return request.redirect(f'/odoo/action-{action.id}/{student.id}', 303)
        return super().web_client(s_action=s_action, **kw)
