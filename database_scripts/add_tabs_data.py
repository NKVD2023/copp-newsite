import sqlite3
import os
from config import Config

def add_tabs_data():
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN tabs_data TEXT")
        print("Column 'tabs_data' added to 'projects' table.")
        conn.commit()
    except sqlite3.OperationalError as e:
        print("Error or column already exists:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    add_tabs_data()
