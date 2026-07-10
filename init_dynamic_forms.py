import sqlite3
import os

def init_forms_db():
    db_path = os.path.join(os.path.dirname(__file__), 'coppdb.sqlite')
    print(f"Подключение к БД: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Таблица для хранения настроек форм
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS page_forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            year INTEGER,
            fields_config TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (page_id) REFERENCES pages (id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица для хранения ответов пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS form_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_id INTEGER NOT NULL,
            submission_data TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (form_id) REFERENCES page_forms (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Таблицы page_forms и form_submissions успешно созданы/проверены!")

if __name__ == '__main__':
    init_forms_db()
