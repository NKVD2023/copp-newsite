"""
Инициализация Blueprint для панели администратора.
Все маршруты внутри этого Blueprint будут доступны по префиксу /admin.
"""
from flask import Blueprint

# Создаем Blueprint админки
bp = Blueprint('admin', __name__)



@bp.context_processor
def inject_admin_context():
    """
    Глобальные переменные для всех шаблонов админки.
    Решает проблему UndefinedError при рендеринге вкладок (например, вкладки атласа профессий)
    из других маршрутов (например, при редактировании страницы).
    """
    from flask import request
    # Не выполняем тяжелые запросы для страницы логина
    if request.endpoint == 'admin.login':
        return {}

    import os
    import json
    from app.db import get_db_connection
    from app.admin.directory.professions import CATEGORIES_RU
    from app.utils.media_utils import scan_uploads_dir

    context = {}
    context['categories_dict'] = CATEGORIES_RU

    with get_db_connection() as conn:
        context['contact_requests'] = conn.execute(
            'SELECT * FROM contact_requests ORDER BY id DESC'
        ).fetchall()
        context['tables_list'] = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

        try:
            context['professions_list'] = conn.execute(
                'SELECT * FROM professions ORDER BY id DESC'
            ).fetchall()
        except Exception:
            context['professions_list'] = []

    colleges_list = []
    colleges_path = os.path.join('app', 'static', 'data', 'colleges.json')
    try:
        with open(colleges_path, 'r', encoding='utf-8') as f:
            colleges_list = json.load(f)
    except Exception:
        pass
    context['colleges_list'] = colleges_list

    context['all_media_files'] = scan_uploads_dir()

    return context


from app.admin.core import auth, dashboard, database, statistics, prof_stats, users
from app.admin.content import news, pages, projects, documents, menu_items
from app.admin.directory import professions, team, socials, contacts
