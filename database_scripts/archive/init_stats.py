import sqlite3
import os

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'coppdb.sqlite')

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    value INTEGER NOT NULL,
    display_order INTEGER DEFAULT 0
)
''')

# Check if empty
c.execute('SELECT COUNT(*) FROM statistics')
count = c.fetchone()[0]

if count == 0:
    stats = [
        ('ПРОШЕДШИХ ОБУЧЕНИЕ ПО ВСЕМ ВИДАМ ОБРАЗОВАТЕЛЬНЫХ ПРОГРАММ', 744, 1),
        ('ЧИСЛЕННОСТЬ ГРАЖДАН, ОХВАЧЕННЫХ ДЕЯТЕЛЬНОСТЬЮ ЦОПП', 36671, 2),
        ('ОБРАТИВШИХСЯ В ЦОПП РЕСПУБЛИКИ КРЫМ', 52, 3),
        ('УЧАСТНИКИ ПРОФОРИЕНТАЦИОННЫХ МЕРОПРИЯТИЙ', 35875, 4)
    ]
    c.executemany('INSERT INTO statistics (label, value, display_order) VALUES (?, ?, ?)', stats)
    conn.commit()
    print("Added default statistics.")
else:
    print("Table already has data.")

conn.close()
print("Done.")
