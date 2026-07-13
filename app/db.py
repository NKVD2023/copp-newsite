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