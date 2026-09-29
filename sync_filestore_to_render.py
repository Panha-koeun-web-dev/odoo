"""
Sync local Odoo filestore images to Render PostgreSQL database.
This uploads all student photos, teacher photos, logos, and icons
directly into the PostgreSQL database (db_datas) so they persist
and display properly on Render without needing local container disks.
"""

import os
import sys
import psycopg2

LOCAL_FILESTORE = r"C:\Users\USER\AppData\Local\OpenERP S.A\Odoo\filestore\testing_db"


def main():
    if not os.path.exists(LOCAL_FILESTORE):
        print(f"Error: Local filestore directory not found at: {LOCAL_FILESTORE}")
        sys.exit(1)

    db_url = None
    if len(sys.argv) > 1:
        db_url = sys.argv[1]
    else:
        db_url = os.environ.get("RENDER_DATABASE_URL")

    if not db_url:
        print("=" * 60)
        print("Render Database Image Sync Tool")
        print("=" * 60)
        print("\nPlease enter your Render External Database URL.")
        print("(Find it in Render Dashboard -> Your PostgreSQL DB -> 'External Database URL')\n")
        try:
            db_url = input("External Database URL: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    if not db_url:
        print("Error: No database URL provided.")
        sys.exit(1)

    print(f"\nConnecting to Render PostgreSQL database...")
    try:
        conn = psycopg2.connect(db_url)
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)

    cur = conn.cursor()

    print("Checking attachments in database...")
    cur.execute("""
        SELECT id, checksum, name, res_model, file_size 
        FROM ir_attachment 
        WHERE checksum IS NOT NULL 
          AND (db_datas IS NULL OR db_datas = '')
        ORDER BY id;
    """)
    rows = cur.fetchall()
    print(f"Found {len(rows)} attachments needing image/file data.")

    uploaded_count = 0
    uploaded_bytes = 0
    missing_count = 0

    for aid, checksum, name, res_model, file_size in rows:
        file_path = os.path.join(LOCAL_FILESTORE, checksum[:2], checksum)
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                data = f.read()

            cur.execute("""
                UPDATE ir_attachment 
                SET db_datas = %s, store_fname = NULL 
                WHERE id = %s;
            """, (data, aid))

            uploaded_count += 1
            uploaded_bytes += len(data)

            if uploaded_count % 25 == 0 or uploaded_count == len(rows):
                print(f"  Progress: {uploaded_count}/{len(rows)} uploaded ({uploaded_bytes / (1024*1024):.1f} MB)...")
        else:
            missing_count += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("Sync Complete!")
    print(f"Successfully uploaded: {uploaded_count} images ({uploaded_bytes / (1024*1024):.2f} MB)")
    if missing_count > 0:
        print(f"Skipped (not found locally): {missing_count}")
    print("=" * 60)
    print("\nRefresh your Odoo page on Render — all photos, logos, and icons will now display!")


if __name__ == "__main__":
    main()
