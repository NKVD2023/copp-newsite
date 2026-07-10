import sqlite3

def test_insert():
    conn = sqlite3.connect('coppdb.sqlite')
    try:
        conn.execute('''
            INSERT INTO pages (title, slug, content, is_in_navbar, menu_group, attached_files, page_style, teaser, page_color, tabs_data, main_image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Тестовая страница', 'test-page-123', 'Контент', 0, '', '[]', 'modern', 'Тизер', '#0066ff', '[]', None))
        conn.commit()
        print("Insert successful!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    test_insert()
