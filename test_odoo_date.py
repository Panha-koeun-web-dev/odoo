from odoo import fields

# Test Odoo's from_string with various formats
test_dates = [
    '01 Jan',
    '1 Jan', 
    'January 1',
    '1 January',
    '01/01/2024',
    '2024-01-01',
]

for d in test_dates:
    val_str = d.strip()
    try:
        result = fields.Date.from_string(val_str)
        print(f'OK "{d}" -> {result}')
    except Exception as e:
        print(f'FAIL "{d}": {e}')