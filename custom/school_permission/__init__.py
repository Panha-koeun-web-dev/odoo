# The app reuses the permission model and workflows provided by school_management.

_LEGACY_MENU_XMLIDS = (
    'school_holiday.menu_time_off_school_permission_root',
    'school_holiday.menu_time_off_school_permission_mine',
    'school_holiday.menu_time_off_school_permission_all',
    'school_holiday.menu_time_off_school_permission_student',
    'school_holiday.menu_time_off_school_permission_teacher',
    'school_holiday.menu_time_off_school_permission_pending',
    'school_holiday.menu_time_off_school_permission_approved',
)


def post_init_hook(env):
    """Hide legacy Time Off entries when upgrading an existing database."""
    for xmlid in _LEGACY_MENU_XMLIDS:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.active = False


def uninstall_hook(env):
    """Restore legacy menus if the dedicated app is uninstalled."""
    for xmlid in _LEGACY_MENU_XMLIDS:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.active = True
