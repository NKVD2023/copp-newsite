import json
from datetime import datetime

def from_json_filter(value):
    """
    Кастомный фильтр Jinja: парсит JSON строку в Python объект (список/словарь).
    Используется в шаблонах так: {{ my_string | from_json }}
    """
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []

def datetime_format_filter(value):
    """
    Форматирует строку даты из SQLite (YYYY-MM-DD HH:MM:SS) в человекочитаемый вид.
    Например: "21 июля 2026, 05:32"
    """
    if not value:
        return ""
    try:
        dt = datetime.strptime(value[:19], '%Y-%m-%d %H:%M:%S')
        months = ['', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        return f"{dt.day} {months[dt.month]} {dt.year}, {dt.strftime('%H:%M')}"
    except Exception:
        return value
