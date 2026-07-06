import sqlite3
conn = sqlite3.connect('coppdb.sqlite')
for row in conn.execute("SELECT sql FROM sqlite_master WHERE type='table';").fetchall():
    if row[0]:
        print(row[0])
