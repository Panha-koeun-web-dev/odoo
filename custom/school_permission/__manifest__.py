{
    'name': 'School Permission',
    'version': '19.0.1.0.0',
    'category': 'School',
    'summary': 'Submit, track, and review student and teacher permission requests',
    'description': """
School Permission
=================

Dedicated workspace for student and teacher leave and permission requests.
Requests keep the existing school-specific identity, validation, and approval
rules, without requiring students to have Odoo employee records.
    """,
    'author': 'Panha Koeun',
    'license': 'LGPL-3',
    'depends': [
        'school_management',
        'school_holiday',
    ],
    'data': [
        'views/menu.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': True,
}
