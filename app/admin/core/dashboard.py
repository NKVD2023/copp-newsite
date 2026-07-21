"""
Модуль отображения главной страницы админ-панели (Дашборд).
Собирает все необходимые данные из БД для вывода вкладок админки.
"""
from datetime import datetime
from flask import render_template, redirect, url_for, session, request, jsonify
from app.admin import bp
from app.admin.core.auth import login_required, get_current_user_modules, ALL_MODULES, ROLE_LABELS
from app.db import get_db_connection
from app.utils.media_utils import scan_uploads_dir


@bp.route('/api/unread_contacts_count')
@login_required
def unread_contacts_count():
    with get_db_connection() as conn:
        count = conn.execute('SELECT COUNT(*) FROM contact_requests WHERE status = "new"').fetchone()[0]
    return jsonify({'count': count})


@bp.route('/')
@login_required
def dashboard():
    """
    Главная страница администратора (/admin/).
    Собирает данные из всех таблиц БД и список файлов из папки загрузок
    для отображения на соответствующих вкладках.
    """
    allowed_modules = get_current_user_modules()
    active_tab = request.args.get('tab', 'news')

    # Если активная вкладка недоступна — перенаправляем на первую доступную
    if not session.get('is_admin') and active_tab not in allowed_modules + ['users']:
        first = allowed_modules[0] if allowed_modules else 'news'
        active_tab = first

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
        menu_items_list   = conn.execute('SELECT * FROM menu_items ORDER BY position ASC, id ASC').fetchall()

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

        # Список субадминов и логов (только для суперадмина)
        users_list = []
        logs_list = []
        if session.get('is_admin'):
            try:
                users_list = conn.execute('SELECT * FROM admin_users ORDER BY created_at DESC').fetchall()
                logs_list = conn.execute('SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT 1000').fetchall()
            except Exception:
                users_list = []
                logs_list = []

    # Загружаем список учебных заведений для чекбоксов
    colleges_list = []
    colleges_path = os.path.join('app', 'static', 'data', 'colleges.json')
    try:
        with open(colleges_path, 'r', encoding='utf-8') as f:
            colleges_list = json.load(f)
    except Exception as e:
        print(f"Error loading colleges: {e}")

    # Обработка редактирования элементов через GET параметры
    edit_item = None
    edit_page_item = None
    page_form = None
    attached_files_list = []
    edit_project_item = None
    extra_images_list = []
    
    with get_db_connection() as conn:
        if request.args.get('edit_news_id'):
            edit_item = conn.execute('SELECT * FROM news WHERE id = ?', (request.args.get('edit_news_id'),)).fetchone()
            
        if request.args.get('edit_page_id'):
            edit_page_item = conn.execute('SELECT * FROM pages WHERE id = ?', (request.args.get('edit_page_id'),)).fetchone()
            page_form = conn.execute("SELECT * FROM page_forms WHERE page_id = ? AND status != 'archived'", (request.args.get('edit_page_id'),)).fetchone()
            if edit_page_item and edit_page_item['attached_files']:
                try:
                    attached_files_list = json.loads(edit_page_item['attached_files'])
                except:
                    pass
                    
        if request.args.get('edit_project_id'):
            edit_project_item = conn.execute('SELECT * FROM projects WHERE id = ?', (request.args.get('edit_project_id'),)).fetchone()
            if edit_project_item and edit_project_item['extra_images']:
                try:
                    extra_images_list = json.loads(edit_project_item['extra_images'])
                except:
                    pass

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
        menu_items_list=menu_items_list,
        all_media_files=all_media_files,
        prof_uploads=prof_uploads,
        professions_list=professions_list,
        colleges_list=colleges_list,
        categories_dict=CATEGORIES_RU,
        contact_requests=contact_requests,
        forms_list=forms_list,
        submissions_list=submissions_list,
        team_members=team_members,
        users_list=users_list,
        logs_list=logs_list,
        allowed_modules=allowed_modules,
        all_modules=ALL_MODULES,
        role_labels=ROLE_LABELS,
        current_username=session.get('username', 'Суперадмин'),
        current_role=session.get('user_role', 'superadmin'),
        is_superadmin=bool(session.get('is_admin')),
        now_str=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        edit_item=edit_item,
        edit_page_item=edit_page_item,
        page_form=page_form,
        attached_files_list=attached_files_list,
        edit_project_item=edit_project_item,
        extra_images_list=extra_images_list
    )
