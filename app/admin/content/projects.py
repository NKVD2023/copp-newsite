import os
import uuid
from flask import render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from app.admin import bp
from app.admin.core.auth import login_required
from app.admin.core.logger import log_admin_action
from app.db import get_db_connection
from app.utils.image_utils import save_image_as_webp
import json

UPLOAD_PROJECTS_FOLDER = os.path.join('app', 'static', 'uploads', 'projects')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

@bp.route('/add_project', methods=['POST'])
@login_required
def add_project():
    """
    Создание нового проекта в разделе "Наши проекты".
    Загружает главную картинку, дополнительные фото, обрабатывает текст и цвет карточки.
    """
    title = request.form['title']
    slug = request.form['slug']
    teaser = request.form.get('teaser', '')
    tabs_json = request.form.get('tabs_json', '')
    
    # Фолбэк для content
    content = ''
    if tabs_json:
        try:
            tabs_data = json.loads(tabs_json)
            if tabs_data and len(tabs_data) > 0:
                content = tabs_data[0].get('content', '')
        except json.JSONDecodeError:
            pass
    button_text = request.form.get('button_text', '')
    button_url = request.form.get('button_url', '')
    project_color = request.form.get('project_color', '#0066ff')
    
    os.makedirs(UPLOAD_PROJECTS_FOLDER, exist_ok=True)
    
    main_image_path = request.form.get('existing_main_image') or None
    if 'main_image' in request.files:
        file = request.files['main_image']
        if file and allowed_file(file.filename):
            filename = save_image_as_webp(file, UPLOAD_PROJECTS_FOLDER, add_uuid=True)
            if filename:
                main_image_path = f"uploads/projects/{filename}"
            
    extra_images_paths = request.form.getlist('existing_extra_images')
    if 'extra_images' in request.files:
        files = request.files.getlist('extra_images')
        for file in files:
            if file and allowed_file(file.filename):
                filename = save_image_as_webp(file, UPLOAD_PROJECTS_FOLDER, add_uuid=True)
                if filename:
                    extra_images_paths.append(f"uploads/projects/{filename}")

    extra_images_json = json.dumps(extra_images_paths)
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO projects (title, slug, teaser, content, main_image, extra_images, button_text, button_url, project_color, tabs_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, slug, teaser, content, main_image_path, extra_images_json, button_text, button_url, project_color, tabs_json))
        conn.commit()
        project_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        log_admin_action('CREATE', 'projects', entity_id=project_id, details=f'Создан проект: "{title}"')
        flash('Проект успешно создан!', 'success')
    except Exception as e:
        flash(f'Ошибка при создании проекта (возможно, такой URL уже существует): {e}', 'danger')
        
    return redirect(url_for('admin.dashboard', tab='projects'))

@bp.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    """
    Редактирование проекта.
    Если GET - отображает форму редактирования на дашборде.
    Если POST - применяет изменения, загружает новые файлы и удаляет старые (по выбору пользователя).
    """
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if not project:
        flash('Проект не найден.', 'danger')
        return redirect(url_for('admin.dashboard', tab='projects'))
        
    if request.method == 'POST':
        title = request.form['title']
        slug = request.form['slug']
        teaser = request.form.get('teaser', '')
        tabs_json = request.form.get('tabs_json', '')
        
        # Фолбэк для content
        content = ''
        if tabs_json:
            try:
                tabs_data = json.loads(tabs_json)
                if tabs_data and len(tabs_data) > 0:
                    content = tabs_data[0].get('content', '')
            except json.JSONDecodeError:
                pass
        button_text = request.form.get('button_text', '')
        button_url = request.form.get('button_url', '')
        project_color = request.form.get('project_color', '#0066ff')
        
        main_image_path = project['main_image']
        existing_main = request.form.get('existing_main_image')
        if 'main_image' in request.files and request.files['main_image'].filename != '':
            file = request.files['main_image']
            if file and allowed_file(file.filename):
                filename = save_image_as_webp(file, UPLOAD_PROJECTS_FOLDER, add_uuid=True)
                if filename:
                    main_image_path = f"uploads/projects/{filename}"
        elif existing_main:
            main_image_path = existing_main
                
        # Parse existing extra images (passed from UI via hidden inputs)
        extra_images_paths = request.form.getlist('existing_extra_images')

        # Handle new extra images upload
        if 'extra_images' in request.files:
            files = request.files.getlist('extra_images')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = save_image_as_webp(file, UPLOAD_PROJECTS_FOLDER, add_uuid=True)
                    if filename:
                        extra_images_paths.append(f"uploads/projects/{filename}")

        extra_images_json = json.dumps(extra_images_paths)
        
        try:
            conn.execute('''
                UPDATE projects 
                SET title = ?, slug = ?, teaser = ?, content = ?, main_image = ?, extra_images = ?, button_text = ?, button_url = ?, project_color = ?, tabs_data = ?
                WHERE id = ?
            ''', (title, slug, teaser, content, main_image_path, extra_images_json, button_text, button_url, project_color, tabs_json, project_id))
            conn.commit()
            log_admin_action('UPDATE', 'projects', entity_id=project_id, details=f'Обновлён проект: "{title}"')
            flash('Проект успешно обновлен!', 'success')
        except Exception as e:
            flash(f'Ошибка обновления (URL должен быть уникальным): {e}', 'danger')
            
        return redirect(url_for('admin.dashboard', tab='projects'))

    # Для GET запроса
    # Редирект на дашборд с параметром edit_project_id
    return redirect(url_for('admin.dashboard', tab='projects', edit_project_id=project_id))


@bp.route('/toggle_project_status/<int:project_id>', methods=['POST'])
@login_required
def toggle_project_status(project_id):
    """
    Переключатель статуса проекта (Опубликован / В архиве).
    """
    current_status = request.form['current_status']
    new_status = 'archived' if current_status == 'published' else 'published'
    
    conn = get_db_connection()
    conn.execute('UPDATE projects SET status = ? WHERE id = ?', (new_status, project_id))
    conn.commit()
    
    title = conn.execute('SELECT title FROM projects WHERE id = ?', (project_id,)).fetchone()
    log_title = title['title'] if title else f"ID {project_id}"
    action_desc = "Опубликован" if new_status == 'published' else "В архиве"
    log_admin_action('UPDATE', 'projects', entity_id=project_id, details=f'Изменён статус проекта "{log_title}": {action_desc}')
    
    return redirect(url_for('admin.dashboard', tab='projects'))

@bp.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    """
    Удаление проекта. Также физически удаляет главное фото и дополнительные картинки.
    """
    conn = get_db_connection()
    project = conn.execute('SELECT main_image, extra_images FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if project:
        # Delete main image
        if project['main_image']:
            try:
                os.remove(os.path.join('app', 'static', project['main_image']))
            except:
                pass
        # Delete extra images
        if project['extra_images']:
            try:
                extra_imgs = json.loads(project['extra_images'])
                for img in extra_imgs:
                    os.remove(os.path.join('app', 'static', img))
            except:
                pass
        title = conn.execute('SELECT title FROM projects WHERE id = ?', (project_id,)).fetchone()
        log_title = title['title'] if title else f"ID {project_id}"
                
        conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        
        log_admin_action('DELETE', 'projects', entity_id=project_id, details=f'Удалён проект: "{log_title}"')
        flash('Проект удален!', 'success')
    return redirect(url_for('admin.dashboard', tab='projects'))
