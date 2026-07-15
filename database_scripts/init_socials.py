import sqlite3
import os

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'coppdb.sqlite')

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS social_networks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    icon_svg TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    display_order INTEGER DEFAULT 0
)
''')

# Insert default social networks if empty
c.execute('SELECT COUNT(*) FROM social_networks')
if c.fetchone()[0] == 0:
    # VKontakte SVG
    vk_svg = '<svg viewBox="0 0 24 24"><path d="M20.5 4h-17C2.1 4 1 5.1 1 6.5v11C1 18.9 2.1 20 3.5 20h17c1.4 0 2.5-1.1 2.5-2.5v-11C23 5.1 21.9 4 20.5 4zm-7.6 12.3c-.6 0-1.8-.1-3.2-1.6-1.5-1.6-3-4.7-3-4.7h2.2s1.1 2.4 2.1 3.5c.9 1.1 1.2 1.4 1.5 1.4.1 0 .4-.1.4-.7V9.7c0-.6-.2-.8-.7-.8h-.4c.2-.3.6-.5 1.1-.6.4-.1 1.2-.1 1.7 0 .5.1.7.3.9.7.2.4.1 1.9.1 2.6 0 .6.2.7.4.7.2 0 .6-.3 1.5-1.3 1-1.1 1.5-2.5 1.5-2.5h2.2s-.5 1.3-1.4 2.5c-.7.9-1.6 1.8-1.5 2.1.2.2 1 1 1.6 1.8 1 1.1 1.3 1.5 1.3 1.5h-2.3c0-.1-.4-.5-1.1-1.3-.8-1-1.1-1.2-1.5-1.2-.4 0-.6.1-.7.4v1.3c0 .6-.2.8-.7.8z"/></svg>'
    
    # Telegram SVG
    tg_svg = '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>'

    c.execute('''
    INSERT INTO social_networks (name, url, icon_svg, display_order)
    VALUES (?, ?, ?, ?)
    ''', ('ВКонтакте', 'https://vk.com/copp82', vk_svg, 1))

    c.execute('''
    INSERT INTO social_networks (name, url, icon_svg, display_order)
    VALUES (?, ?, ?, ?)
    ''', ('Telegram', 'https://t.me/copp82', tg_svg, 2))
    
    print("Added default social networks.")
else:
    print("Social networks table is already populated.")

conn.commit()
conn.close()
print("Done initializing social_networks table.")
