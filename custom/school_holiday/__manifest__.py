{
    'name': 'School Public Holiday',
    'version': '19.0.1.0.0',
    'category': 'School',
    'summary': 'Manage public holidays and integrate with school study schedules',
    'description': """
School Public Holiday
=====================

Features:
- Manage public holidays (multi-company support)
- Create, update, archive holidays
- Import holidays from CSV and Excel (.xlsx)
- Decoupled Holiday Timetable Service:
  * Reschedule conflicting class sessions to the next week
  * Display public holidays on calendar views
  * Prevent scheduling new classes on public holidays
- REST API for Public Holidays (/api/holidays)
    """,
    'author': 'Panha Koeun',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'school_management',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/holiday_data.xml',
        'wizard/import_holiday_wizard_views.xml',
        'views/public_holiday_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}
