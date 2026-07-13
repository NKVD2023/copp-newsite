"""
Утилиты для форматирования дат на русском языке.
Вынесено из routes.py, где дублировалось в 4 местах.
"""
from datetime import datetime

MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


def format_date_ru(date_str: str) -> str:
    """
    Форматирует строку даты 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'
    в читаемый русский формат: '5 июля 2026 г.'
    При ошибке возвращает исходную строку.
    """
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
        return f"{dt.day} {MONTHS_RU[dt.month - 1]} {dt.year} г."
    except (ValueError, IndexError):
        return str(date_str)[:10]


def format_event_date_ru(date_str: str) -> str:
    """
    Форматирует дату мероприятия. Поддерживает форматы:
    - 'YYYY-MM-DDTHH:MM'  →  '5 июля 2026 г., 14:00'
    - 'YYYY-MM-DD'        →  '5 июля 2026 г.'
    При ошибке возвращает исходную строку.
    """
    if not date_str:
        return ""
    try:
        if 'T' in str(date_str):
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            return f"{dt.day} {MONTHS_RU[dt.month - 1]} {dt.year} г., {dt.hour:02d}:{dt.minute:02d}"
        else:
            dt = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
            return f"{dt.day} {MONTHS_RU[dt.month - 1]} {dt.year} г."
    except (ValueError, IndexError):
        return str(date_str)


def enrich_news_list(news_rows) -> list:
    """
    Принимает список строк из таблицы news (sqlite3.Row или dict),
    возвращает список dict с добавленным полем 'human_date'.
    """
    result = []
    for row in news_rows:
        item = dict(row)
        item['human_date'] = format_date_ru(item.get('publish_date', ''))
        result.append(item)
    return result
