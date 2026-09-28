#!/bin/sh
set -e

echo "Checking if database $DB_NAME is initialized..."

python3 - <<EOF
import os, sys, psycopg2

try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', 5432),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        dbname=os.environ.get('DB_NAME')
    )
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name='ir_module_module'")
    exists = cur.fetchone()
    conn.close()
    if not exists:
        print("Database tables not found. Initializing base module...")
        sys.exit(10)
    else:
        print("Database already initialized.")
        sys.exit(0)
except Exception as e:
    print(f"Warning checking database: {e}")
    sys.exit(0)
EOF

STATUS=$?

if [ "$STATUS" -eq 10 ]; then
    echo "First time boot: Initializing database with -i base..."
    exec python3 odoo-bin -c odoo-render.conf --http-port=8069 --db_host=${DB_HOST} --db_port=${DB_PORT} --db_user=${DB_USER} --db_password=${DB_PASSWORD} -d ${DB_NAME} -i base
else
    echo "Starting Odoo server..."
    exec python3 odoo-bin -c odoo-render.conf --http-port=8069 --db_host=${DB_HOST} --db_port=${DB_PORT} --db_user=${DB_USER} --db_password=${DB_PASSWORD} -d ${DB_NAME}
fi
