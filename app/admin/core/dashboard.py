"""
Модуль отображения главной страницы админ-панели (Дашборд).
Собирает все необходимые данные из БД для вывода вкладок админки.
"""
from datetime import datetime
from flask import render_template, redirect, url_for, session, request
from app.admin import bp
from app.admin.core.auth import login_required
from app.db import get_db_connection
from app.utils.media_utils import scan_uploads_dir


@bp.route('/')
@login_required
def dashboard():
    """
    Главная страница администратора (/admin/).
    Собирает данные из всех таблиц БД и список файлов из папки загрузок
    для отображения на соответствующих вкладках.
    """
    active_tab = request.args.get('tab', 'news')

    # Сканирование директории загрузок — вынесено в утилиту (было продублировано 3 раза)
    all_media_files = scan_uploads_dir()

    import json
    import os
    from app.admin.directory.professions import CATEGORIES_RU

    with get_db_connection() as conn:
        news_list       = conn.execute('SELECT * FROM news ORDER BY id DESC').fetchall()
        pages_list      = conn.execute('SELECT * FROM pages ORDER BY id DESC').fetchall()
        documents_list  = conn.execute('SELECT * FROM documents ORDER BY id DESC').fetchall()
        projects_list   = conn.execute('SELECT * FROM projects ORDER BY id DESC').fetchall()
        stats_list      = conn.execute('SELECT * FROM statistics ORDER BY display_order ASC').fetchall()
        socials_list    = conn.execute('SELECT * FROM social_networks ORDER BY display_order ASC').fetchall()
        contact_settings  = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
        menu_groups_list  = conn.execute('SELECT DISTINCT menu_group FROM pages WHERE menu_group IS NOT NULL AND menu_group != ""').fetchall()
        tables_list       = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        contact_requests  = conn.execute('SELECT * FROM contact_requests ORDER BY id DESC').fetchall()

        try:
            forms_list = conn.execute('SELECT * FROM page_forms ORDER BY id DESC').fetchall()
            submissions_list = conn.execute('''
                SELECT s.*, f.title as form_title, f.year
                FROM form_submissions s
                JOIN page_forms f ON s.form_id = f.id
                ORDER BY s.id DESC
            ''').fetchall()
        except Exception:
            forms_list = []
            submissions_list = []

        try:
            prof_uploads = conn.execute('SELECT * FROM dashboard_uploads ORDER BY upload_date DESC').fetchall()
        except Exception:
            prof_uploads = []

        try:
            professions_list = conn.execute('SELECT * FROM professions ORDER BY id DESC').fetchall()
        except Exception:
            professions_list = []

        try:
            team_members = conn.execute('SELECT * FROM team_members ORDER BY display_order ASC, id DESC').fetchall()
        except Exception:
            team_members = []

    # Загружаем список учебных заведений для чекбоксов
    colleges_list = []
    colleges_path = os.path.join('app', 'static', 'data', 'colleges.json')
    try:
        with open(colleges_path, 'r', encoding='utf-8') as f:
            colleges_list = json.load(f)
    except Exception as e:
        print(f"Error loading colleges: {e}")

    return render_template(
        'admin_dashboard.html',
        active_tab=active_tab,
        news_list=news_list,
        pages_list=pages_list,
        documents_list=documents_list,
        projects_list=projects_list,
        stats_list=stats_list,
        socials_list=socials_list,
        contact_settings=contact_settings,
        menu_groups_list=menu_groups_list,
        tables_list=tables_list,
        all_media_files=all_media_files,
        prof_uploads=prof_uploads,
        professions_list=professions_list,
        colleges_list=colleges_list,
        categories_dict=CATEGORIES_RU,
        contact_requests=contact_requests,
        forms_list=forms_list,
        submissions_list=submissions_list,
        team_members=team_members,
        now_str=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )
