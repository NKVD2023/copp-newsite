import sqlite3

conn = sqlite3.connect('coppdb.sqlite')
conn.row_factory = sqlite3.Row
profs = conn.execute("SELECT * FROM professions ORDER BY id DESC LIMIT 5").fetchall()

for p in profs:
    print(dict(p))
