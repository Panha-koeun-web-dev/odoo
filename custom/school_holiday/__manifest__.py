{
    'name': 'School Public Holiday',
    'version': '19.0.1.0.0',
    'category': 'Education',
    'summary': 'Manage public holidays and integrate with school study schedules',
    'description': """
School Public Holiday
=====================

Features:
- Manage public holidays
- Create, update, archive holidays
- Import holidays from CSV and Excel (.xlsx)
- Validate against school study timetable schedule
- Automatically reschedule conflicting class sessions to the next week
- Display public holidays directly on the timetable calendar
- Prevent scheduling new classes on public holidays
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
        'wizard/import_holiday_wizard_views.xml',
        'views/public_holiday_views.xml',
        'views/menu.xml',
        'data/holiday_data.xml',
    ],
    'installable': True,
    'application': True,
}
