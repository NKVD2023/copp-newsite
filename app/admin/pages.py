from flask import render_template, request, redirect, url_for, session, flash
from app.admin import bp
from app.db import get_db_connection
import os
import uuid
from werkzeug.utils import secure_filename
import json
from app.utils.image_utils import save_image_as_webp

UPLOAD_PAGES_FILES_FOLDER = os.path.join('app', 'static', 'uploads', 'page_files')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar', 'txt', 'rtf', 'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/add_page', methods=['POST'])
def add_page():
    """
    Создание новой статической страницы.
    Обрабатывает текст (через TinyMCE), файлы (вложения) и привязку к меню.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    title = request.form.get('title')
    slug = request.form.get('slug')
    content = request.form.get('content', '')
    is_in_navbar = 1 if request.form.get('is_in_navbar') else 0
    menu_group = request.form.get('menu_group', '').strip()
    
    page_style = request.form.get('page_style', 'default')
    teaser = request.form.get('teaser')
    page_color = request.form.get('page_color')
    tabs_data = request.form.get('tabs_data')
    main_image = None
    
    attached_files_paths = request.form.getlist('existing_attached_files')
    os.makedirs(UPLOAD_PAGES_FILES_FOLDER, exist_ok=True)
    
    if 'main_image' in request.files:
        file = request.files['main_image']
        if file and allowed_file(file.filename):
            filename = save_image_as_webp(file, UPLOAD_PAGES_FILES_FOLDER, add_uuid=True)
            if filename:
                main_image = f"uploads/page_files/{filename}"

    if 'attached_files' in request.files:
        files = request.files.getlist('attached_files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = save_image_as_webp(file, UPLOAD_PAGES_FILES_FOLDER, add_uuid=True)
                if filename:
                    attached_files_paths.append(f"uploads/page_files/{filename}")

    attached_files_json = json.dumps(attached_files_paths)
    
    with get_db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pages (title, slug, content, is_in_navbar, menu_group, attached_files, page_style, teaser, page_color, tabs_data, main_image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, slug, content, is_in_navbar, menu_group, attached_files_json, page_style, teaser, page_color, tabs_data, main_image))
            
            page_id = cursor.lastrowid
            
            # Обработка конфигурации формы
            form_enabled = request.form.get('enable_dynamic_form')
            form_title = request.form.get('dynamic_form_title', '').strip()
            form_fields_json = request.form.get('dynamic_form_fields', '[]')
            
            if form_enabled == '1' and form_title:
                form_year = request.form.get('dynamic_form_year', '').strip()
                cursor.execute('''
                    INSERT INTO page_forms (page_id, title, year, fields_config, status) 
                    VALUES (?, ?, ?, ?, 'active')
                ''', (page_id, form_title, form_year, form_fields_json))
                
            conn.commit()
            flash("Страница успешно создана!", "success")
        except Exception as e:
            with open('error_log.txt', 'a') as f:
                f.write(f"Add Page Error: {e}\\n")
            flash(f"Ошибка при создании (возможно такой URL уже существует): {e}", "danger")
            
    return redirect(url_for('admin.dashboard', tab='pages'))

@bp.route('/edit_page/<int:page_id>', methods=['GET'])
def edit_page(page_id):
    """
    Страница редактирования статической страницы.
    Отображает дашборд с формой редактирования выбранной страницы.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    with get_db_connection() as conn:
        news_list = conn.execute('SELECT * FROM news ORDER BY id DESC').fetchall()
        pages_list = conn.execute('SELECT * FROM pages ORDER BY id DESC').fetchall()
        documents_list = conn.execute('SELECT * FROM documents ORDER BY id DESC').fetchall()
        projects_list = conn.execute('SELECT * FROM projects ORDER BY id DESC').fetchall()
        stats_list = conn.execute('SELECT * FROM statistics ORDER BY display_order ASC').fetchall()
        socials_list = conn.execute('SELECT * FROM social_networks ORDER BY display_order ASC').fetchall()
        contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
        edit_page_item = conn.execute('SELECT * FROM pages WHERE id = ?', (page_id,)).fetchone()
        menu_groups_list = conn.execute('SELECT DISTINCT menu_group FROM pages WHERE menu_group IS NOT NULL AND menu_group != ""').fetchall()
        
        # Получаем привязанную форму (не архивированную)
        page_form = conn.execute("SELECT * FROM page_forms WHERE page_id = ? AND status != 'archived'", (page_id,)).fetchone()
    
    attached_files_list = []
    if edit_page_item and edit_page_item['attached_files']:
        try:
            attached_files_list = json.loads(edit_page_item['attached_files'])
        except:
            pass
            
    return render_template('admin_dashboard.html', 
                           news_list=news_list, 
                           pages_list=pages_list, 
                           documents_list=documents_list,
                           projects_list=projects_list,
                           stats_list=stats_list,
                           socials_list=socials_list,
                           contact_settings=contact_settings,
                           edit_page_item=edit_page_item, 
                           attached_files_list=attached_files_list, 
                           active_tab='pages', 
                           menu_groups_list=menu_groups_list,
                           page_form=page_form)

@bp.route('/update_page/<int:page_id>', methods=['POST'])
def update_page(page_id):
    """
    Обновление существующей статической страницы.
    Обрабатывает новые файлы, удаление старых файлов из ФС и обновляет БД.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    title = request.form.get('title')
    slug = request.form.get('slug')
    content = request.form.get('content', '')
    is_in_navbar = 1 if request.form.get('is_in_navbar') else 0
    menu_group = request.form.get('menu_group', '').strip()
    
    page_style = request.form.get('page_style', 'default')
    teaser = request.form.get('teaser')
    page_color = request.form.get('page_color')
    tabs_data = request.form.get('tabs_data')
    
    main_image = request.form.get('existing_main_image')
    attached_files_paths = request.form.getlist('existing_attached_files')

    os.makedirs(UPLOAD_PAGES_FILES_FOLDER, exist_ok=True)
    
    if 'main_image' in request.files:
        file = request.files['main_image']
        if file and allowed_file(file.filename):
            filename = save_image_as_webp(file, UPLOAD_PAGES_FILES_FOLDER, add_uuid=True)
            if filename:
                main_image = f"uploads/page_files/{filename}"

    if 'attached_files' in request.files:
        files = request.files.getlist('attached_files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = save_image_as_webp(file, UPLOAD_PAGES_FILES_FOLDER, add_uuid=True)
                if filename:
                    attached_files_paths.append(f"uploads/page_files/{filename}")

    attached_files_json = json.dumps(attached_files_paths)
    
    with get_db_connection() as conn:
        try:
            conn.execute('''
                UPDATE pages 
                SET title = ?, slug = ?, content = ?, is_in_navbar = ?, menu_group = ?, attached_files = ?,
                    page_style = ?, teaser = ?, page_color = ?, tabs_data = ?, main_image = ?
                WHERE id = ?
            ''', (title, slug, content, is_in_navbar, menu_group, attached_files_json, page_style, teaser, page_color, tabs_data, main_image, page_id))
            
            # Обработка конфигурации формы
            form_enabled = request.form.get('enable_dynamic_form')
            delete_form = request.form.get('delete_dynamic_form')
            form_title = request.form.get('dynamic_form_title', '').strip()
            form_fields_json = request.form.get('dynamic_form_fields', '[]')
            
            if delete_form == '1':
                conn.execute("UPDATE page_forms SET status = 'archived' WHERE page_id = ? AND status != 'archived'", (page_id,))
            else:
                existing_form = conn.execute("SELECT id FROM page_forms WHERE page_id = ? AND status != 'archived'", (page_id,)).fetchone()
                
                if form_enabled == '1' and form_title:
                    form_year = request.form.get('dynamic_form_year', '').strip()
                    
                    if existing_form:
                        conn.execute('''
                            UPDATE page_forms SET title = ?, year = ?, fields_config = ?, status = 'active' WHERE id = ?
                        ''', (form_title, form_year, form_fields_json, existing_form['id']))
                    else:
                        conn.execute('''
                            INSERT INTO page_forms (page_id, title, year, fields_config, status) 
                            VALUES (?, ?, ?, ?, 'active')
                        ''', (page_id, form_title, form_year, form_fields_json))
                else:
                    # Если форма отключена (скрыта), просто меняем статус
                    if existing_form:
                        conn.execute("UPDATE page_forms SET status = 'hidden' WHERE id = ?", (existing_form['id'],))
                
            conn.commit()
            flash("Страница успешно обновлена!", "success")
        except Exception as e:
            with open('error_log.txt', 'a') as f:
                f.write(f"Update Page Error: {e}\\n")
            flash(f"Ошибка при обновлении: {e}", "danger")
            
    return redirect(url_for('admin.dashboard', tab='pages'))

@bp.route('/delete_page/<int:page_id>', methods=['POST'])
def delete_page(page_id):
    """
    Полное удаление страницы и всех прикрепленных к ней файлов из ФС и БД.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    with get_db_connection() as conn:
        page = conn.execute('SELECT attached_files FROM pages WHERE id = ?', (page_id,)).fetchone()
        if page and page['attached_files']:
            try:
                attached_files = json.loads(page['attached_files'])
                for file_path in attached_files:
                    os.remove(os.path.join('app', 'static', file_path))
            except:
                pass
        conn.execute('DELETE FROM pages WHERE id = ?', (page_id,))
        conn.commit()
        
    flash("Страница удалена!", "success")
    return redirect(url_for('admin.dashboard', tab='pages'))

@bp.route('/toggle_page_navbar/<int:page_id>', methods=['POST'])
def toggle_page_navbar(page_id):
    """
    Включение/Отключение отображения страницы в главном меню навигации.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    current_status = int(request.form.get('current_status', 0))
    new_status = 0 if current_status == 1 else 1
    
    with get_db_connection() as conn:
        conn.execute('UPDATE pages SET is_in_navbar = ? WHERE id = ?', (new_status, page_id))
        conn.commit()
        
    flash("Статус отображения в меню изменен", "success")
    return redirect(url_for('admin.dashboard', tab='pages'))

import os
from werkzeug.utils import secure_filename
from flask import jsonify

UPLOAD_PAGES_FOLDER = os.path.join('app', 'static', 'uploads', 'pages')

@bp.route('/upload_image', methods=['POST'])
def upload_image():
    """
    Обработчик асинхронной загрузки картинок напрямую из редактора TinyMCE.
    Возвращает JSON с URL загруженной картинки.
    """
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = save_image_as_webp(file, UPLOAD_PAGES_FOLDER, add_uuid=True)
        if filename:
            return jsonify({'location': url_for('static', filename=f'uploads/pages/{filename}')})
        return jsonify({'error': 'Failed to upload image'}), 500

