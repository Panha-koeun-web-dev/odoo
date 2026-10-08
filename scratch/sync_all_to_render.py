import os
import subprocess
import sys
import psycopg2

LOCAL_DUMP = r"C:\Users\USER\Desktop\odoo\backup.dump"
PG_RESTORE = r"C:\Program Files\PostgreSQL\18\bin\pg_restore.exe"
PG_DUMP = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
RENDER_URL = "postgresql://odoo_user:UETIIryCLNrSeMeoxcvJhZB4eU95rGiG@dpg-dat1c4h7lnhs73b8qubg-a.virginia-postgres.render.com/odoo_4fyd"

print("=" * 60)
print("STARTING FULL LOCAL -> RENDER DATABASE & FILESTORE SYNC")
print("=" * 60)

# Step 1: Export local testing_db
print("\n[Step 1/4] Dumping local database testing_db...")
env = os.environ.copy()
env["PGPASSWORD"] = "panha123!@#"
dump_cmd = [
    PG_DUMP,
    "-h", "localhost",
    "-p", "5432",
    "-U", "panha123",
    "-d", "testing_db",
    "-F", "c",
    "-b",
    "-f", LOCAL_DUMP
]
res = subprocess.run(dump_cmd, env=env)
if res.returncode != 0:
    print("Error: pg_dump failed!")
    sys.exit(1)
print(f"Dump successful: {os.path.getsize(LOCAL_DUMP) / (1024*1024):.2f} MB")

# Step 2: Clean Render public schema
print("\n[Step 2/4] Resetting Render public schema...")
conn = psycopg2.connect(RENDER_URL)
conn.autocommit = True
cur = conn.cursor()

cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
cur.execute("CREATE SCHEMA public;")
cur.execute("GRANT ALL ON SCHEMA public TO odoo_user;")
cur.execute("GRANT ALL ON SCHEMA public TO public;")
conn.close()
print("Render public schema reset successfully.")

# Step 3: Fast Parallel pg_restore (-j 8)
print("\n[Step 3/4] Restoring backup to Render in parallel (8 workers)...")
restore_cmd = [
    PG_RESTORE,
    "-j", "8",
    "--no-owner",
    "--no-acl",
    "-d", RENDER_URL,
    LOCAL_DUMP
]
res = subprocess.run(restore_cmd)
print(f"pg_restore finished with code: {res.returncode}")

# Step 4: Sync filestore images to Render
print("\n[Step 4/4] Syncing local filestore images to Render...")
sync_cmd = [
    sys.executable,
    "sync_filestore_to_render.py",
    RENDER_URL
]
res = subprocess.run(sync_cmd)
if res.returncode != 0:
    print("Warning: sync_filestore_to_render reported errors.")

print("\n" + "=" * 60)
print("SYNC TO RENDER COMPLETED SUCCESSFULLY!")
print("=" * 60)
