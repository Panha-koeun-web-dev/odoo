import os
import sys
import psycopg2

db_name = os.environ.get('DB_NAME')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT', '5432')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')

print(f"Connecting to database {db_name} at {db_host}...")

is_initialized = False
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
        print("Database initialized. Clearing stale asset bundles from ir_attachment...")
        cur.execute("DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';")
        # Ensure attachments are stored in Postgres so ephemeral disk wipes on Render don't break them
        cur.execute("""
            INSERT INTO ir_config_parameter (key, value)
            VALUES ('ir_attachment.location', 'db')
            ON CONFLICT (key) DO UPDATE SET value = 'db';
        """)
        conn.commit()
    conn.close()
except Exception as e:
    print(f"Database check notice: {e}")

cmd = [
    sys.executable,
    'odoo-bin',
    '-c', 'odoo-render.conf',
    '--http-port=8069',
    f'--db_host={db_host}',
    f'--db_port={db_port}',
    f'--db_user={db_user}',
    f'--db_password={db_password}',
    '-d', db_name
]

if not is_initialized:
    print("Database tables not found. Initializing base module (-i base)...")
    cmd.extend(['-i', 'base'])
else:
    print("Database already initialized. Starting Odoo server...")

# Replace process with Odoo
os.execvp(cmd[0], cmd)
