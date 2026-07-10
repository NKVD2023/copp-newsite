"""
Модуль отображения главной страницы админ-панели (Дашборд).
Собирает все необходимые данные из БД для вывода вкладок админки.
"""
from flask import render_template, redirect, url_for, session
from app.admin import bp
from app.db import get_db_connection

@bp.route('/')
def dashboard():
    """
    Главная страница администратора (/admin/).
    Проверяет сессию. Если не авторизован - перенаправляет на логин.
    Собирает данные из всех таблиц БД и список файлов из папки загрузок
    для отображения на соответствующих вкладках.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    
    from flask import request
    active_tab = request.args.get('tab', 'news')
    
    import os
    from datetime import datetime

    # Сканирование директории загрузок для менеджера файлов
    uploads_dir = os.path.join('app', 'static', 'uploads')
    all_media_files = []
    
    if os.path.exists(uploads_dir):
        # Рекурсивный проход по всем подпапкам в uploads
        for root, dirs, files in os.walk(uploads_dir):
            for file in files:
                filepath = os.path.join(root, file)
                # Вычисляем относительный путь для HTML тегов (src/href)
                rel_path = os.path.relpath(filepath, os.path.join('app', 'static')).replace('\\', '/')
                folder = os.path.basename(root)
                
                stat = os.stat(filepath)
                size_kb = round(stat.st_size / 1024, 1)
                
                # Format date
                date_obj = datetime.fromtimestamp(stat.st_mtime)
                date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                
                ext = file.rsplit('.', 1)[-1].lower() if '.' in file else ''
                is_image = ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']
                
                all_media_files.append({
                    'filename': file,
                    'filepath': rel_path,
                    'folder': folder,
                    'size_kb': size_kb,
                    'date_str': date_str,
                    'is_image': is_image,
                    'timestamp': stat.st_mtime
                })
    
    # Сортируем файлы по дате изменения (новые сверху)
    all_media_files.sort(key=lambda x: x['timestamp'], reverse=True)

    # Загружаем данные из всех таблиц для заполнения вкладок дашборда
    with get_db_connection() as conn:
        news_list = conn.execute('SELECT * FROM news ORDER BY id DESC').fetchall()
        pages_list = conn.execute('SELECT * FROM pages ORDER BY id DESC').fetchall()
        documents_list = conn.execute('SELECT * FROM documents ORDER BY id DESC').fetchall()
        projects_list = conn.execute('SELECT * FROM projects ORDER BY id DESC').fetchall()
        stats_list = conn.execute('SELECT * FROM statistics ORDER BY display_order ASC').fetchall()
        socials_list = conn.execute('SELECT * FROM social_networks ORDER BY display_order ASC').fetchall()
        contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
        menu_groups_list = conn.execute('SELECT DISTINCT menu_group FROM pages WHERE menu_group IS NOT NULL AND menu_group != ""').fetchall()
        tables_list = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        contact_requests = conn.execute('SELECT * FROM contact_requests ORDER BY id DESC').fetchall()
        
        try:
            forms_list = conn.execute('SELECT * FROM page_forms ORDER BY id DESC').fetchall()
            submissions_list = conn.execute('''
                SELECT s.*, f.title as form_title, f.year 
                FROM form_submissions s 
                JOIN page_forms f ON s.form_id = f.id 
                ORDER BY s.id DESC
            ''').fetchall()
        except:
            forms_list = []
            submissions_list = []
        try:
            prof_uploads = conn.execute('SELECT * FROM dashboard_uploads ORDER BY upload_date DESC').fetchall()
        except:
            prof_uploads = []
            
        try:
            professions_list = conn.execute('SELECT * FROM professions ORDER BY id DESC').fetchall()
        except:
            professions_list = []
            
        try:
            team_members = conn.execute('SELECT * FROM team_members ORDER BY display_order ASC, id DESC').fetchall()
        except:
            team_members = []
            
    # Загружаем список учебных заведений для чекбоксов
    import json
    colleges_list = []
    colleges_path = os.path.join('app', 'static', 'data', 'colleges.json')
    try:
        with open(colleges_path, 'r', encoding='utf-8') as f:
            colleges_list = json.load(f)
    except Exception as e:
        print(f"Error loading colleges: {e}")
            
    from app.admin.professions import CATEGORIES_RU
    return render_template('admin_dashboard.html', 
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
                           now_str=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))