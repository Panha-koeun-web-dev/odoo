import psycopg2

conn_local = psycopg2.connect(host='localhost', port=5432, user='panha123', password='panha123!@#', dbname='testing_db')
conn_render = psycopg2.connect('postgresql://odoo_user:UETIIryCLNrSeMeoxcvJhZB4eU95rGiG@dpg-dat1c4h7lnhs73b8qubg-a.virginia-postgres.render.com/odoo_4fyd')
cur_l = conn_local.cursor()
cur_r = conn_render.cursor()

cur_l.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'school_%'")
tables = [r[0] for r in cur_l.fetchall()]
print(f"Comparing {len(tables)} school tables (Local vs Render):")
diff_count = 0
for t in sorted(tables):
    cur_l.execute(f"SELECT count(*) FROM {t}")
    cl = cur_l.fetchone()[0]
    try:
        cur_r.execute(f"SELECT count(*) FROM {t}")
        cr = cur_r.fetchone()[0]
    except Exception as e:
        conn_render.rollback()
        cr = "MISSING"
    mark = " [DIFF]" if str(cl) != str(cr) else "       "
    if str(cl) != str(cr):
        diff_count += 1
    print(f"{mark} {t:35} Local: {cl:4} | Render: {str(cr):4}")

print(f"\nTotal tables with differences: {diff_count}")
conn_local.close()
conn_render.close()
