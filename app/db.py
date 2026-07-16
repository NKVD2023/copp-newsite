"""
Модуль для работы с базой данных SQLite.
Использует flask.g для хранения единственного соединения на весь HTTP-запрос.
Это устраняет избыточные открытия/закрытия соединений при нескольких вызовах get_db_connection().
"""
import sqlite3
from flask import current_app, g


def get_db_connection():
    """
    Возвращает подключение к SQLite, переиспользуя его в пределах одного HTTP-запроса.
    Соединение сохраняется в flask.g и автоматически закрывается по окончании запроса
    через teardown_appcontext, зарегистрированный в create_app().
    """
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        # Включаем WAL-режим для лучшей параллельности чтения/записи в SQLite
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db


def close_db(error=None):
    """
    Закрывает соединение с БД по окончании HTTP-запроса.
    Регистрируется через app.teardown_appcontext() в create_app().
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """
    Создает недостающие таблицы, если они отсутствуют в БД.
    """
    with app.app_context():
        conn = get_db_connection()
        # Создаем таблицу menu_items, если её нет (например, если откатили бэкап)
        conn.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT,
            parent_id INTEGER,
            position INTEGER DEFAULT 0,
            type TEXT DEFAULT 'static',
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (parent_id) REFERENCES menu_items(id)
        )
        ''')
        
        # Проверяем, пустая ли таблица
        count = conn.execute('SELECT COUNT(*) FROM menu_items').fetchone()[0]
        if count == 0:
            # Наполняем дефолтными значениями
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Новости', '', None, 10, 'static'))
            news_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Все новости', '/news', news_id, 10, 'static'))
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Мероприятия', '/events', news_id, 20, 'static'))
            
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Атлас профессий', '/atlas', None, 20, 'static'))
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Востребованные професии', '/dashboard', None, 30, 'static'))
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Цифровая платформа', 'https://cp.copp82.ru', None, 40, 'static'))
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Проекты', '', None, 50, 'dynamic_projects'))
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('О центре', '', None, 60, 'dynamic_pages_group_О центре'))
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Конкурсы', '', None, 70, 'dynamic_pages_group_Конкурсы'))
            conn.execute('INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)', ('Дополнительно', '', None, 80, 'dynamic_pages_group_Дополнительно'))
        
        conn.commit()