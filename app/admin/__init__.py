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
    from datetime import datetime
    from app.db import get_db_connection
    from app.admin.professions import CATEGORIES_RU
    
    context = {}
    context['categories_dict'] = CATEGORIES_RU
    
    with get_db_connection() as conn:
        context['contact_requests'] = conn.execute('SELECT * FROM contact_requests ORDER BY id DESC').fetchall()
        context['tables_list'] = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        
        try:
            context['prof_uploads'] = conn.execute('SELECT * FROM dashboard_uploads ORDER BY upload_date DESC').fetchall()
        except:
            context['prof_uploads'] = []
            
        try:
            context['professions_list'] = conn.execute('SELECT * FROM professions ORDER BY id DESC').fetchall()
        except:
            context['professions_list'] = []
            
    colleges_list = []
    colleges_path = os.path.join('app', 'static', 'data', 'colleges.json')
    try:
        with open(colleges_path, 'r', encoding='utf-8') as f:
            colleges_list = json.load(f)
    except Exception:
        pass
    context['colleges_list'] = colleges_list
    
    uploads_dir = os.path.join('app', 'static', 'uploads')
    all_media_files = []
    if os.path.exists(uploads_dir):
        for root, dirs, files in os.walk(uploads_dir):
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, os.path.join('app', 'static')).replace('\\', '/')
                folder = os.path.basename(root)
                stat = os.stat(filepath)
                size_kb = round(stat.st_size / 1024, 1)
                date_obj = datetime.fromtimestamp(stat.st_mtime)
                date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                ext = file.rsplit('.', 1)[-1].lower() if '.' in file else ''
                is_image = ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']
                all_media_files.append({
                    'filename': file, 'filepath': rel_path, 'folder': folder,
                    'size_kb': size_kb, 'date_str': date_str, 'is_image': is_image,
                    'timestamp': stat.st_mtime
                })
    all_media_files.sort(key=lambda x: x['timestamp'], reverse=True)
    context['all_media_files'] = all_media_files
    
    return context

# Импортируем модули маршрутов админки. 
# Они должны быть строго внизу, чтобы избежать циклических импортов, 
# так как внутри этих файлов импортируется переменная `bp` из этого файла.
from app.admin import auth, dashboard, news, contacts, documents, pages, projects, socials, statistics, database, prof_stats, professions