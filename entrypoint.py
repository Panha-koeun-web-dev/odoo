import os
import sys
import subprocess
import psycopg2

db_name = os.environ.get('DB_NAME')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT', '5432')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
port = os.environ.get('PORT', '8069')

print(f"Connecting to database {db_name} at {db_host}...")

is_initialized = False
school_installed = False
try:
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        dbname=db_name
    )
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name='ir_module_module'")
    if cur.fetchone():
        is_initialized = True
        print("Optimizing database attachments and assets...")
        
        # 1. Stop FileNotFoundError tracebacks: clear ghost file pointers where no data exists
        cur.execute("""
            UPDATE ir_attachment 
            SET store_fname = NULL 
            WHERE store_fname IS NOT NULL AND (db_datas IS NULL OR db_datas = '');
        """)
        
        # 2. Clear stale disk-based asset bundles (keep database-backed ones)
        cur.execute("""
            DELETE FROM ir_attachment 
            WHERE url LIKE '/web/assets/%' AND (db_datas IS NULL OR db_datas = '');
        """)
        
        # 3. Store all attachments in PostgreSQL so Render container restarts don't lose them
        cur.execute("""
            INSERT INTO ir_config_parameter (key, value)
            VALUES ('ir_attachment.location', 'db')
            ON CONFLICT (key) DO UPDATE SET value = 'db';
        """)

        # 4. Defensive migration: Ensure timetable_id column exists on school_permission table
        cur.execute("""
            SELECT 1 FROM information_schema.tables WHERE table_name='school_permission'
        """)
        if cur.fetchone():
            cur.execute("""
                ALTER TABLE school_permission 
                ADD COLUMN IF NOT EXISTS timetable_id INTEGER REFERENCES school_timetable(id) ON DELETE SET NULL;
            """)
            print("Ensured school_permission.timetable_id column exists in database.")

                # 4B. Fix missing not-null constraints on res_partner boolean columns if present
        for col in ('group_rfq', 'group_on'):
            cur.execute(f"SELECT is_nullable FROM information_schema.columns WHERE table_name='res_partner' AND column_name='{col}'")
            row = cur.fetchone()
            if row and row[0] == 'YES':
                cur.execute(f"UPDATE res_partner SET {col} = FALSE WHERE {col} IS NULL; ALTER TABLE res_partner ALTER COLUMN {col} SET DEFAULT FALSE; ALTER TABLE res_partner ALTER COLUMN {col} SET NOT NULL;")

        # 5. Fix legacy string values in school_certificate.class_rank before integer conversion
        cur.execute("""
            SELECT data_type FROM information_schema.columns 
            WHERE table_name='school_certificate' AND column_name='class_rank'
        """)
        row = cur.fetchone()
        if row and row[0] not in ('integer', 'smallint', 'bigint'):
            print("Migrating school_certificate.class_rank from text to integer...")
            cur.execute("""
                ALTER TABLE school_certificate 
                ALTER COLUMN class_rank TYPE integer 
                USING (
                    CASE 
                        WHEN class_rank ~ '^Rank ([0-9]+)' THEN (substring(class_rank from '^Rank ([0-9]+)'))::integer
                        WHEN class_rank ~ '^[0-9]+$' THEN class_rank::integer
                        ELSE 1
                    END
                );
            """)
            print("Successfully migrated school_certificate.class_rank to integer.")

        conn.commit()

        # 6. Check if school_management module is installed
        cur.execute("SELECT state FROM ir_module_module WHERE name='school_management'")
        row = cur.fetchone()
        if row and row[0] == 'installed':
            school_installed = True
            print("Detected school_management is installed in database.")

    cur.close()
    conn.close()
except Exception as e:
    print(f"Database check notice: {e}")

# Base initialization if database is brand new
if not is_initialized:
    print("Database tables not found. Initializing base module (-i base)...")
    init_cmd = [
        sys.executable,
        'odoo-bin',
        '-c', 'odoo-render.conf',
        '--stop-after-init',
        f'--db_host={db_host}',
        f'--db_port={db_port}',
        f'--db_user={db_user}',
        f'--db_password={db_password}',
        '-d', db_name,
        '-i', 'base'
    ]
    subprocess.run(init_cmd, check=True)
elif school_installed:
    # Auto-upgrade school_management cleanly before opening HTTP port
    auto_upgrade = os.environ.get('AUTO_UPGRADE', 'true').lower() in ('true', '1', 'yes')
    if auto_upgrade:
        print("Pre-compiling and upgrading school_management cleanly before starting HTTP server...")
        upgrade_cmd = [
            sys.executable,
            'odoo-bin',
            '-c', 'odoo-render.conf',
            '--stop-after-init',
            f'--db_host={db_host}',
            f'--db_port={db_port}',
            f'--db_user={db_user}',
            f'--db_password={db_password}',
            '-d', db_name,
            '-u', 'school_management'
        ]
        try:
            subprocess.run(upgrade_cmd, check=True)
            print("Module upgrade completed successfully.")
        except Exception as e:
            print(f"Warning during pre-compile upgrade: {e}. Starting server anyway...")

# Launch the live Odoo HTTP server
server_cmd = [
    sys.executable,
    'odoo-bin',
    '-c', 'odoo-render.conf',
    f'--http-port={port}',
    '--http-interface=0.0.0.0',
    f'--db_host={db_host}',
    f'--db_port={db_port}',
    f'--db_user={db_user}',
    f'--db_password={db_password}',
    '-d', db_name
]

print(f"Starting Odoo HTTP service on 0.0.0.0:{port}...")
sys.stdout.flush()
sys.stderr.flush()
os.execvp(server_cmd[0], server_cmd)
