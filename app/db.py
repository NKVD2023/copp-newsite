"""
Модуль для работы с базой данных SQLite.
"""
import sqlite3
from flask import current_app

def get_db_connection():
    """
    Создает и возвращает подключение к базе данных.
    Использует путь к БД из конфигурации приложения.
    """
    conn = sqlite3.connect(current_app.config['DATABASE'])
    # Устанавливаем фабрику строк, чтобы к столбцам можно было обращаться по именам (как к словарям: row['title'])
    conn.row_factory = sqlite3.Row
    return conn