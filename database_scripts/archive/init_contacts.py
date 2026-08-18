import sqlite3
import os

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'coppdb.sqlite')

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS contact_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    title TEXT DEFAULT 'Контакты',
    org_name TEXT DEFAULT 'ЦОПП Республики Крым',
    phones TEXT DEFAULT '8 (3652) 51-04-40
7 (978) 391-46-44',
    email TEXT DEFAULT 'office@copp82.ru',
    address TEXT DEFAULT '295051 Респ. Крым, г. Симферополь, ул. Металлистов, д. 13'
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS contact_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'new'
)
''')

# Insert default settings if empty
c.execute('SELECT COUNT(*) FROM contact_settings')
if c.fetchone()[0] == 0:
    c.execute('''
    INSERT INTO contact_settings (id, title, org_name, phones, email, address)
    VALUES (1, 'Контакты', 'ЦОПП Республики Крым', '8 (3652) 51-04-40\n7 (978) 391-46-44', 'office@copp82.ru', '295051 Респ. Крым, г. Симферополь, ул. Металлистов, д. 13')
    ''')
    print("Added default contact settings.")
else:
    print("Contact settings already exist.")

conn.commit()
conn.close()
print("Done initializing contacts db tables.")
