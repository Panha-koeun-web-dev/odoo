{
    'name': 'School Public Holiday',
    'version': '19.0.1.0.0',
    'category': 'Education',
    'summary': 'Manage public holidays and integrate them with school management',
    'description': """
School Public Holiday
=====================

Features:
- Manage public holidays
- Create/update/delete holidays
- Import holidays from CSV
- Import holidays from Excel
- Search and filter holidays
- Holiday types
- Multi-day holidays
- Holiday year
- Integrate with School Management
- Prevent attendance on public holidays
    """,
    'author': 'Panha Koeun',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'school_management',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/public_holiday_views.xml',
        'views/menu.xml',

        'wizard/import_holiday_wizard_views.xml',

        'data/holiday_data.xml',
    ],
    'installable': True,
    'application': True,
}