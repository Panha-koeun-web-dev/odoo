import csv
import io
from datetime import datetime
from odoo import fields

# Simulate reading the test CSV
csv_content = """name,date,end_date,holiday_type,description
"International New Year",2024-01-01,2024-01-01,national,"International New Year holiday"
"Victory Day",01 Jan,,national,"Victory Day holiday"
"Independence Day",04 July,,national,"Independence Day holiday"
"Christmas",25 Dec,,religious,"Christmas holiday"
"""

# Simulate CSV reading (like the import wizard does)
decoded = csv_content.encode('utf-8-sig')
reader = csv.DictReader(io.StringIO(decoded.decode('utf-8-sig')))

print("CSV Headers:", reader.fieldnames)
print()

for r in reader:
    print("Row:", r)
    # Parse the date using the same logic as the wizard
    date_val = r.get('date', '')
    if date_val:
        val_str = str(date_val).strip()
        if not val_str:
            parsed_date = False
        else:
            # Try common date formats (from the wizard)
            parsed_date = None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d',
                         '%b %d', '%B %d', '%d %b', '%d %B'):
                try:
                    parsed_date = datetime.strptime(val_str, fmt).date()
                    print(f'  Parsed "{val_str}" using "{fmt}" -> {parsed_date}')
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                # Try Odoo's from_string
                try:
                    parsed_date = fields.Date.from_string(val_str)
                    print(f'  Parsed "{val_str}" using Odoo from_string -> {parsed_date}')
                except Exception as e:
                    print(f'  FAIL "{val_str}": {e}')
                    parsed_date = False
    else:
        parsed_date = False
    
    print(f"  -> Final date: {parsed_date}")
    print()