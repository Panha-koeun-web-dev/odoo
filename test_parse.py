import sys
sys.path.insert(0, r'C:\Users\USER\Desktop\odoo')

from datetime import datetime, date
from odoo import fields
from odoo.fields import Date

# Simulate the updated _parse_date_value logic
def parse_date_value(val):
    """Updated parse logic from the wizard."""
    if not val:
        return False
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()

    val_str = str(val).strip()
    if not val_str:
        return False

    # Get today's date for year assumption
    today = Date.today()
    
    # Try common date formats
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d',
                 '%b %d', '%B %d', '%d %b', '%d %B'):
        try:
            parsed = datetime.strptime(val_str, fmt).date()
            # If year is 1900 (default when not specified), use current year
            if parsed.year == 1900:
                parsed = Date.from_string(
                    f"{today.year}-{parsed.month}-{parsed.day}"
                )
            return parsed
        except ValueError:
            continue

    # Try Odoo's from_string
    try:
        parsed = Date.from_string(val_str)
        if parsed:
            return parsed
    except Exception:
        pass

    raise ValidationError(
        _("Invalid date format: '%s'.") % val_str
    )

# Test dates
test_dates = [
    '01 Jan',       # Should become current year-01-01
    '1 Jan',        # Should become current year-01-01
    'January 1',    # Should become current year-01-01
    '1 January',    # Should become current year-01-01
    '01/01/2024',   # Should become 2024-01-01
    '2024-01-01',   # Should become 2024-01-01
    '25 Dec',       # Should become current year-12-25
    '04 July',      # Should become current year-07-04
]

print(f"Today's year: {Date.today().year}\n")
print("="*60)
for d in test_dates:
    try:
        result = parse_date_value(d)
        print(f'OK "{d}" -> {result}')
    except Exception as e:
        print(f'FAIL "{d}": {e}')