import subprocess
import sys
import psycopg2

RENDER_URL = "postgresql://odoo_user:UETIIryCLNrSeMeoxcvJhZB4eU95rGiG@dpg-dat1c4h7lnhs73b8qubg-a.virginia-postgres.render.com/odoo_4fyd"

print("1. Checking connection to Render PostgreSQL...")
conn = psycopg2.connect(RENDER_URL)
cur = conn.cursor()
cur.execute("SELECT schema_owner FROM information_schema.schemata WHERE schema_name = 'public'")
row = cur.fetchone()
print(f"Public schema owner: {row[0] if row else 'None'}")
conn.close()
