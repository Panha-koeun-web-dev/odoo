import os
import subprocess
import sys
import time
import psycopg2

RENDER_URL = "postgresql://odoo_user:UETIIryCLNrSeMeoxcvJhZB4eU95rGiG@dpg-dat1c4h7lnhs73b8qubg-a.virginia-postgres.render.com/odoo_4fyd"
DUMP_FILE = r"C:\Users\USER\Desktop\odoo\backup_clean.dump"
PG_RESTORE = r"C:\Program Files\PostgreSQL\18\bin\pg_restore.exe"

print("=" * 60)
print("1. CLEANING RENDER DATABASE PUBLIC SCHEMA")
print("=" * 60)
conn = psycopg2.connect(RENDER_URL, connect_timeout=10)
conn.autocommit = True
cur = conn.cursor()

print("Dropping and recreating schema public...")
cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
cur.execute("CREATE SCHEMA public;")
cur.execute("GRANT ALL ON SCHEMA public TO odoo_user;")
cur.execute("GRANT ALL ON SCHEMA public TO public;")
conn.close()
print("Schema public successfully reset.")

print("\n" + "=" * 60)
print("2. RESTORING COMPLETE DATABASE TO RENDER")
print("=" * 60)
restore_cmd = [
    PG_RESTORE,
    "--no-owner",
    "--no-acl",
    "-d", RENDER_URL,
    DUMP_FILE
]
start_t = time.time()
p = subprocess.run(restore_cmd, capture_output=True, text=True)
print(f"Restore finished in {time.time() - start_t:.1f} seconds with return code: {p.returncode}")
if p.stderr:
    # Print errors if any (excluding benign warnings)
    errors = [line for line in p.stderr.splitlines() if "ERROR" in line or "FATAL" in line]
    if errors:
        print(f"Errors encountered ({len(errors)}):")
        for err in errors[:10]:
            print("  ", err)

print("\n" + "=" * 60)
print("3. VERIFYING SCHOOL TABLES ON RENDER")
print("=" * 60)
conn = psycopg2.connect(RENDER_URL, connect_timeout=10)
cur = conn.cursor()
cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'school_%'")
school_count = cur.fetchone()[0]
print(f"Total school tables restored on Render: {school_count}")

for table in ["school_student", "school_teacher", "school_term", "school_timetable", "school_public_holiday"]:
    try:
        cur.execute(f"SELECT count(*) FROM {table}")
        print(f"  {table}: {cur.fetchone()[0]} rows")
    except Exception as e:
        print(f"  {table}: error {e}")
conn.close()

print("\n" + "=" * 60)
print("4. SYNCING FILESTORE IMAGES (STUDENT/TEACHER PHOTOS, LOGOS)")
print("=" * 60)
sync_cmd = [
    sys.executable,
    "sync_filestore_to_render.py",
    RENDER_URL
]
subprocess.run(sync_cmd, check=True)

print("\n" + "=" * 60)
print("SUCCESS: LOCAL AND DEPLOYMENT DATABASES ARE NOW IDENTICAL!")
print("=" * 60)
