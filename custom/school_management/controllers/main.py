# -*- coding: utf-8 -*-
import re
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.action import Action
from odoo.addons.web.controllers.utils import clean_action

STUDENT_RESTRICTED_XML_IDS = (
    'school_management.action_student',
    'school_management.action_teacher',
    'school_management.action_school_dashboard',
    'school_management.action_enrollment',
    'school_management.action_school_student_subject',
    'school_management.action_school_assign_subject_wizard',
    'school_management.action_school_teaching_assignment',
    'school_management.action_school_permission_teacher',
    'school_management.action_school_permission_pending',
    'school_management.action_school_term_schedule_wizard',
    'school_management.action_major',
    'school_management.action_major_enrollment',
    'school_management.action_fee',
    'school_management.action_school_feedback_all',
    'school_holiday.action_import_school_holiday_wizard',
    'school_management.action_school_report_student_xlsx',
    'school_management.action_school_report_class_xlsx',
    'school_management.action_school_report_grade_xlsx',
    'school_management.action_school_report_attendance_xlsx',
    'school_management.action_school_report_fee_xlsx',
    'school_management.action_school_report_year_payment_xlsx',
    'school_management.action_school_report_export_xlsx_wizard',
    'base.action_res_users',
    'base.action_partner_form',
    'base.action_res_company_form',
)

TEACHER_RESTRICTED_XML_IDS = (
    'school_management.action_major',
    'school_management.action_major_enrollment',
    'school_management.action_fee',
    'school_management.action_school_feedback_all',
    'school_management.action_school_term_schedule_wizard',
    'school_holiday.action_import_school_holiday_wizard',
    'school_management.action_school_report_fee_xlsx',
    'school_management.action_school_report_year_payment_xlsx',
    'base.action_res_users',
    'base.action_partner_form',
    'base.action_res_company_form',
)

SYSTEM_RESTRICTED_PATH_PATTERNS = (
    '/odoo/apps',
    '/web/apps',
    '/odoo/settings',
    '/web/settings',
    '/odoo/administration',
    '/web/administration',
)


def _get_restricted_action_ids(env, xml_ids):
    action_ids = set()
    for xid in xml_ids:
        rec = env.ref(xid, raise_if_not_found=False)
        if rec and hasattr(rec, 'id'):
            action_ids.add(rec.id)
    return action_ids


def _is_path_restricted_for_user(user, path_str, env):
    if not path_str or not user:
        return False

    is_admin = user.has_group('school_management.group_school_admin')
    if is_admin:
        return False

    is_teacher = user.has_group('school_management.group_school_teacher')
    is_student = (
        user.has_group('school_management.group_school_student')
        and not is_teacher
    )

    path_lower = str(path_str).lower()

    for pattern in SYSTEM_RESTRICTED_PATH_PATTERNS:
        if pattern in path_lower:
            return True

    match = re.search(r'action-([a-zA-Z0-9_\.]+)', path_str)
    act_ref = match.group(1) if match else None

    if is_student:
        restricted_ids = _get_restricted_action_ids(env, STUDENT_RESTRICTED_XML_IDS)
        if act_ref:
            if act_ref.isdigit() and int(act_ref) in restricted_ids:
                return True
            if any(xid in act_ref for xid in STUDENT_RESTRICTED_XML_IDS):
                return True
        for xid in STUDENT_RESTRICTED_XML_IDS:
            if xid in path_str:
                return True
        for act_id in restricted_ids:
            if f'action-{act_id}' in path_str:
                return True

    elif is_teacher:
        restricted_ids = _get_restricted_action_ids(env, TEACHER_RESTRICTED_XML_IDS)
        if act_ref:
            if act_ref.isdigit() and int(act_ref) in restricted_ids:
                return True
            if any(xid in act_ref for xid in TEACHER_RESTRICTED_XML_IDS):
                return True
        for xid in TEACHER_RESTRICTED_XML_IDS:
            if xid in path_str:
                return True
        for act_id in restricted_ids:
            if f'action-{act_id}' in path_str:
                return True

    return False


def _is_action_restricted_for_user(user, action_id, env):
    if not user or not action_id:
        return False

    if user.has_group('school_management.group_school_admin'):
        return False

    is_teacher = user.has_group('school_management.group_school_teacher')
    is_student = (
        user.has_group('school_management.group_school_student')
        and not is_teacher
    )

    resolved_id = None
    resolved_xml_id = None

    if isinstance(action_id, int) or (isinstance(action_id, str) and action_id.isdigit()):
        resolved_id = int(action_id)
    elif isinstance(action_id, str):
        if '.' in action_id:
            resolved_xml_id = action_id
            rec = env.ref(action_id, raise_if_not_found=False)
            if rec:
                resolved_id = rec.id
        else:
            act = env['ir.actions.actions'].sudo().search([('path', '=', action_id)], limit=1)
            if act:
                resolved_id = act.id

    if is_student:
        restricted_ids = _get_restricted_action_ids(env, STUDENT_RESTRICTED_XML_IDS)
        if resolved_id and resolved_id in restricted_ids:
            return True
        if resolved_xml_id and resolved_xml_id in STUDENT_RESTRICTED_XML_IDS:
            return True
    elif is_teacher:
        restricted_ids = _get_restricted_action_ids(env, TEACHER_RESTRICTED_XML_IDS)
        if resolved_id and resolved_id in restricted_ids:
            return True
        if resolved_xml_id and resolved_xml_id in TEACHER_RESTRICTED_XML_IDS:
            return True

    return False


class SchoolHome(Home):

    def _login_redirect(self, uid, redirect=None):
        user = request.env['res.users'].sudo().browse(uid)
        is_admin = user.has_group('school_management.group_school_admin')
        if not is_admin:
            is_teacher = user.has_group('school_management.group_school_teacher')
            is_student = user.has_group('school_management.group_school_student') and not is_teacher

            action_timetable = request.env.ref('school_management.action_timetable', raise_if_not_found=False)

            if is_student or is_teacher:
                if (
                    not redirect
                    or redirect in ('/odoo', '/web', '/', '/web/login', '/odoo/action-')
                    or _is_path_restricted_for_user(user, str(redirect), request.env)
                ):
                    if action_timetable:
                        return f'/odoo/action-{action_timetable.id}'

        return super()._login_redirect(uid, redirect=redirect)

    @http.route(['/web', '/odoo', '/odoo/<path:subpath>', '/scoped_app/<path:subpath>'], type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        if request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid)
            is_admin = user.has_group('school_management.group_school_admin')
            if not is_admin:
                is_teacher = user.has_group('school_management.group_school_teacher')
                is_student = user.has_group('school_management.group_school_student') and not is_teacher

                current_path = request.httprequest.path or ''
                action_timetable = request.env.ref('school_management.action_timetable', raise_if_not_found=False)

                # 1. Root landing redirect
                if current_path in ('/odoo', '/web', '/odoo/', '/scoped_app', '/scoped_app/'):
                    if action_timetable:
                        return request.redirect(f'/odoo/action-{action_timetable.id}', 303)

                # 2. Path-based restriction check (hide unauthorized paths by redirecting)
                if _is_path_restricted_for_user(user, current_path, request.env):
                    if action_timetable:
                        return request.redirect(f'/odoo/action-{action_timetable.id}', 303)

                # 3. Query-based action check
                query_action = kw.get('action') or (s_action if isinstance(s_action, str) else None)
                if query_action and _is_action_restricted_for_user(user, query_action, request.env):
                    if action_timetable:
                        return request.redirect(f'/odoo/action-{action_timetable.id}', 303)

        return super().web_client(s_action=s_action, **kw)


class SchoolAction(Action):

    @http.route('/web/action/load', type='jsonrpc', auth='user', readonly=True)
    def load(self, action_id, context=None):
        user = request.env.user
        if _is_action_restricted_for_user(user, action_id, request.env):
            action_timetable = request.env.ref('school_management.action_timetable', raise_if_not_found=False)
            if action_timetable:
                result = action_timetable.sudo()._get_action_dict()
                return clean_action(result, env=request.env) if result else False
        return super().load(action_id, context=context)
