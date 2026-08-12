import sqlite3
import os

DB_PATH = '../coppdb.sqlite'

def migrate():
    # Adjust path if run from root
    db_path = DB_PATH
    if not os.path.exists(db_path):
        db_path = 'coppdb.sqlite'
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN totp_secret TEXT")
        print("Колонка totp_secret добавлена.")
    except sqlite3.OperationalError as e:
        print(f"totp_secret: {e}")

    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN is_2fa_enabled BOOLEAN DEFAULT 0")
        print("Колонка is_2fa_enabled добавлена.")
    except sqlite3.OperationalError as e:
        print(f"is_2fa_enabled: {e}")

    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN backup_codes TEXT")
        print("Колонка backup_codes добавлена.")
    except sqlite3.OperationalError as e:
        print(f"backup_codes: {e}")

    conn.commit()
    conn.close()
    print("Миграция завершена.")

if __name__ == '__main__':
    migrate()
