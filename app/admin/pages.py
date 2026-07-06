from flask import render_template, request, redirect, url_for, session, flash
from app.admin import bp
from app.db import get_db_connection
import os
import uuid
from werkzeug.utils import secure_filename
import json

UPLOAD_PAGES_FILES_FOLDER = os.path.join('app', 'static', 'uploads', 'page_files')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar', 'txt', 'rtf', 'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/add_page', methods=['POST'])
def add_page():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    title = request.form.get('title')
    slug = request.form.get('slug')
    content = request.form.get('content')
    is_in_navbar = 1 if request.form.get('is_in_navbar') else 0
    menu_group = request.form.get('menu_group', '').strip()
    
    attached_files_paths = []
    os.makedirs(UPLOAD_PAGES_FILES_FOLDER, exist_ok=True)
    if 'attached_files' in request.files:
        files = request.files.getlist('attached_files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = str(uuid.uuid4()) + "_" + filename
                file_path = os.path.join(UPLOAD_PAGES_FILES_FOLDER, unique_name)
                file.save(file_path)
                # Store original name alongside path, or just path if we use basename later
                # For simplicity, we'll store a list of dicts or just paths. Let's just store paths and infer names.
                attached_files_paths.append(f"uploads/page_files/{unique_name}")

    attached_files_json = json.dumps(attached_files_paths)
    
    with get_db_connection() as conn:
        try:
            conn.execute('''
                INSERT INTO pages (title, slug, content, is_in_navbar, menu_group, attached_files)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, slug, content, is_in_navbar, menu_group, attached_files_json))
            conn.commit()
            flash("Страница успешно создана!", "success")
        except Exception as e:
            flash(f"Ошибка при создании (возможно такой URL уже существует): {e}", "danger")
            
    return redirect(url_for('admin.dashboard', tab='pages'))

@bp.route('/edit_page/<int:page_id>', methods=['GET'])
def edit_page(page_id):
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
                           menu_groups_list=menu_groups_list)

@bp.route('/update_page/<int:page_id>', methods=['POST'])
def update_page(page_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    title = request.form.get('title')
    slug = request.form.get('slug')
    content = request.form.get('content')
    is_in_navbar = 1 if request.form.get('is_in_navbar') else 0
    menu_group = request.form.get('menu_group', '').strip()
    
    with get_db_connection() as conn:
        page = conn.execute('SELECT attached_files FROM pages WHERE id = ?', (page_id,)).fetchone()
        
    try:
        attached_files_paths = json.loads(page['attached_files']) if page['attached_files'] else []
    except:
        attached_files_paths = []
        
    images_to_delete = request.form.getlist('delete_files')
    for file_path in images_to_delete:
        if file_path in attached_files_paths:
            attached_files_paths.remove(file_path)
            try:
                os.remove(os.path.join('app', 'static', file_path))
            except:
                pass

    os.makedirs(UPLOAD_PAGES_FILES_FOLDER, exist_ok=True)
    if 'attached_files' in request.files:
        files = request.files.getlist('attached_files')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = str(uuid.uuid4()) + "_" + filename
                file_path = os.path.join(UPLOAD_PAGES_FILES_FOLDER, unique_name)
                file.save(file_path)
                attached_files_paths.append(f"uploads/page_files/{unique_name}")

    attached_files_json = json.dumps(attached_files_paths)
    
    with get_db_connection() as conn:
        try:
            conn.execute('''
                UPDATE pages 
                SET title = ?, slug = ?, content = ?, is_in_navbar = ?, menu_group = ?, attached_files = ?
                WHERE id = ?
            ''', (title, slug, content, is_in_navbar, menu_group, attached_files_json, page_id))
            conn.commit()
            flash("Страница успешно обновлена!", "success")
        except Exception as e:
            flash(f"Ошибка при обновлении: {e}", "danger")
            
    return redirect(url_for('admin.dashboard', tab='pages'))

@bp.route('/delete_page/<int:page_id>', methods=['POST'])
def delete_page(page_id):
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
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        os.makedirs(UPLOAD_PAGES_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_PAGES_FOLDER, filename)
        file.save(filepath)
        return jsonify({'location': url_for('static', filename=f'uploads/pages/{filename}')})

