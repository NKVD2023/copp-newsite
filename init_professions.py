import sqlite3
import os

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'coppdb.sqlite')

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS professions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    name TEXT NOT NULL,
    description TEXT,
    activities TEXT,
    qualities TEXT,
    medical TEXT,
    institutions TEXT,
    image_path TEXT
)
''')

conn.commit()
print("Table 'professions' created successfully.")
conn.close()
print("Done.")
