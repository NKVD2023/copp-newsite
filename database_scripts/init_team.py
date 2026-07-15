import sqlite3
import os

def init_team():
    db_path = os.path.join(os.path.dirname(__file__), 'coppdb.sqlite')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            position TEXT NOT NULL,
            email TEXT,
            image_path TEXT,
            display_order INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()
    print("Table 'team_members' created successfully.")

if __name__ == '__main__':
    init_team()
