import sqlite3
conn = sqlite3.connect('coppdb.sqlite')
print(conn.execute('SELECT sql FROM sqlite_master WHERE type=\"table\" AND name=\"news\"').fetchone()[0])
