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
    from app.repositories.models import (
        NewsRepository, PagesRepository, DocumentsRepository, ProjectsRepository,
        StatisticsRepository, SocialNetworksRepository, ContactSettingsRepository,
        ContactRequestsRepository, MenuItemsRepository, PageFormsRepository,
        FormSubmissionsRepository, DashboardUploadsRepository, ProfessionsRepository,
        TeamMembersRepository, CareerTestResultsRepository, AdminUsersRepository,
        SystemRepository
    )

    # Инициализируем пустые списки для шаблона
    news_list, pages_list, documents_list, projects_list = [], [], [], []
    stats_list, socials_list, menu_items_list, contact_requests = [], [], [], []
    forms_list, submissions_list, prof_uploads, professions_list = [], [], [], []
    team_members, career_test_stats, users_list = [], [], []
    tables_list, menu_groups_list = [], []
    contact_settings = None

    # Загружаем только те данные, которые нужны для текущей вкладки (ленивая загрузка)
    if active_tab == 'news':
        news_list = NewsRepository.get_all()
    elif active_tab == 'pages':
        pages_list = PagesRepository.get_all()
        menu_groups_list = PagesRepository.get_menu_groups()
    elif active_tab == 'documents':
        documents_list = DocumentsRepository.get_all()
    elif active_tab == 'projects':
        projects_list = ProjectsRepository.get_all()
    elif active_tab == 'stats':
        stats_list = StatisticsRepository.get_all(order_by='display_order ASC')
    elif active_tab == 'socials':
        socials_list = SocialNetworksRepository.get_all(order_by='display_order ASC')
    elif active_tab == 'contacts':
        contact_settings = ContactSettingsRepository.get_settings()
        contact_requests = ContactRequestsRepository.get_all()
    elif active_tab == 'menu':
        menu_items_list = MenuItemsRepository.get_all(order_by='position ASC, id ASC')
    elif active_tab == 'database':
        tables_list = SystemRepository.get_all_tables()
    elif active_tab == 'forms_data':
        try:
            forms_list = PageFormsRepository.get_all()
            submissions_list = FormSubmissionsRepository.get_all_with_form_titles()
        except Exception:
            pass
    elif active_tab == 'prof_stats':
        try:
            prof_uploads = DashboardUploadsRepository.get_all()
        except Exception:
            pass
    elif active_tab == 'prof_atlas':
        try:
            professions_list = ProfessionsRepository.get_all()
        except Exception:
            pass
    elif active_tab == 'team':
        try:
            team_members = TeamMembersRepository.get_all()
        except Exception:
            pass
    elif active_tab == 'statistics':
        try:
            career_test_stats = CareerTestResultsRepository.get_recent_stats(50)
        except Exception:
            pass
    elif active_tab == 'users' and session.get('is_admin'):
        try:
            users_list = AdminUsersRepository.get_all()
        except Exception:
            pass

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
    
    if request.args.get('edit_news_id'):
        edit_item = NewsRepository.get_by_id(request.args.get('edit_news_id'))
        
    if request.args.get('edit_page_id'):
        edit_page_item = PagesRepository.get_by_id(request.args.get('edit_page_id'))
        with get_db_connection() as conn:
            page_form = conn.execute("SELECT * FROM page_forms WHERE page_id = ? AND status != 'archived'", (request.args.get('edit_page_id'),)).fetchone()
        if edit_page_item and edit_page_item['attached_files']:
            try:
                attached_files_list = json.loads(edit_page_item['attached_files'])
            except:
                pass
                
    if request.args.get('edit_project_id'):
        edit_project_item = ProjectsRepository.get_by_id(request.args.get('edit_project_id'))
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
        extra_images_list=extra_images_list,
        career_test_stats=career_test_stats
    )

@bp.route('/logs/clear', methods=['POST'])
@login_required
def clear_logs():
    if not session.get('is_admin'):
        return jsonify({'error': 'Доступ запрещен'}), 403
        
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM admin_logs')
        conn.commit()
        from app.admin.core.logger import log_admin_action
        log_admin_action('DELETE', 'logs', details='Очищен журнал действий системы')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/logs/fix_time', methods=['GET'])
@login_required
def fix_logs_time():
    if not session.get('is_admin'):
        return "Доступ запрещен", 403
    try:
        conn = get_db_connection()
        conn.execute("UPDATE admin_logs SET created_at = datetime(created_at, '+3 hours')")
        conn.commit()
        return "Время старых логов успешно сдвинуто на +3 часа! Вернитесь назад."
    except Exception as e:
        return f"Ошибка: {str(e)}"

@bp.route('/logs/export')
@login_required
def export_logs():
    if not session.get('is_admin'):
        return redirect(url_for('admin.dashboard'))
    try:
        import pandas as pd
        from flask import send_file
        import io
        from app.admin.core.logger import log_admin_action
        
        with get_db_connection() as conn:
            logs = conn.execute('SELECT created_at, username, role, action, module, details, ip_address FROM admin_logs ORDER BY created_at DESC').fetchall()
        
        df = pd.DataFrame(logs, columns=['Дата и Время', 'Пользователь', 'Роль', 'Действие', 'Модуль', 'Детали', 'IP-адрес'])
        
        action_map = {
            'LOGIN': 'Вход в систему',
            'LOGOUT': 'Выход из системы',
            'CREATE': 'Создание',
            'UPDATE': 'Обновление',
            'DELETE': 'Удаление',
            'UPLOAD': 'Загрузка файла',
            'EXPORT': 'Экспорт'
        }
        df['Действие'] = df['Действие'].map(lambda x: action_map.get(x, x))
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Журнал действий')
        
        output.seek(0)
        filename = f"action_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        log_admin_action('EXPORT', 'logs', details='Экспорт журнала действий в Excel')
        
        return send_file(output, download_name=filename, as_attachment=True)
    except Exception as e:
        print(f"Ошибка при экспорте: {e}")
        return redirect(url_for('admin.dashboard'))

@bp.route('/api/logs', methods=['GET'])
@login_required
def api_logs():
    if not session.get('is_admin'):
        return jsonify({'error': 'Доступ запрещен'}), 403

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    search = request.args.get('search', '').strip()

    offset = (page - 1) * per_page

    try:
        conn = get_db_connection()
        if search:
            search_term = f"%{search}%"
            # Фильтрация по дате, пользователю, действию, деталям или IP
            where_clause = "WHERE created_at LIKE ? OR username LIKE ? OR action LIKE ? OR details LIKE ? OR ip_address LIKE ?"
            params = (search_term, search_term, search_term, search_term, search_term)
            
            total_count = conn.execute(f"SELECT COUNT(*) as count FROM admin_logs {where_clause}", params).fetchone()['count']
            logs = conn.execute(f"SELECT * FROM admin_logs {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + (per_page, offset)).fetchall()
        else:
            total_count = conn.execute("SELECT COUNT(*) as count FROM admin_logs").fetchone()['count']
            logs = conn.execute("SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ? OFFSET ?", (per_page, offset)).fetchall()

        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log['id'],
                'created_at': log['created_at'], # Мы отформатируем на клиенте или здесь
                'username': log['username'],
                'role': log['role'],
                'action': log['action'],
                'details': log['details'],
                'entity_id': log['entity_id'],
                'ip_address': log['ip_address']
            })

        total_pages = (total_count + per_page - 1) // per_page
        if total_pages == 0: total_pages = 1

        return jsonify({
            'logs': logs_data,
            'total_count': total_count,
            'total_pages': total_pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
