import os
import uuid
from flask import render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename
from app.admin import bp
from app.db import get_db_connection
import json

UPLOAD_PROJECTS_FOLDER = os.path.join('app', 'static', 'uploads', 'projects')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

@bp.route('/add_project', methods=['POST'])
def add_project():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    title = request.form['title']
    slug = request.form['slug']
    teaser = request.form.get('teaser', '')
    content = request.form['content']
    button_text = request.form.get('button_text', '')
    button_url = request.form.get('button_url', '')
    project_color = request.form.get('project_color', '#0066ff')
    
    os.makedirs(UPLOAD_PROJECTS_FOLDER, exist_ok=True)
    
    main_image_path = None
    if 'main_image' in request.files:
        file = request.files['main_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = str(uuid.uuid4()) + "_" + filename
            file_path = os.path.join(UPLOAD_PROJECTS_FOLDER, unique_name)
            file.save(file_path)
            main_image_path = f"uploads/projects/{unique_name}"
            
    extra_images_paths = []
    if 'extra_images' in request.files:
        files = request.files.getlist('extra_images')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = str(uuid.uuid4()) + "_" + filename
                file_path = os.path.join(UPLOAD_PROJECTS_FOLDER, unique_name)
                file.save(file_path)
                extra_images_paths.append(f"uploads/projects/{unique_name}")

    extra_images_json = json.dumps(extra_images_paths)
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO projects (title, slug, teaser, content, main_image, extra_images, button_text, button_url, project_color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, slug, teaser, content, main_image_path, extra_images_json, button_text, button_url, project_color))
        conn.commit()
        flash('Проект успешно создан!', 'success')
    except Exception as e:
        flash(f'Ошибка при создании проекта (возможно, такой URL уже существует): {e}', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('admin.dashboard', tab='projects'))

@bp.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    
    if not project:
        conn.close()
        flash('Проект не найден.', 'danger')
        return redirect(url_for('admin.dashboard', tab='projects'))
        
    if request.method == 'POST':
        title = request.form['title']
        slug = request.form['slug']
        teaser = request.form.get('teaser', '')
        content = request.form['content']
        button_text = request.form.get('button_text', '')
        button_url = request.form.get('button_url', '')
        project_color = request.form.get('project_color', '#0066ff')
        
        main_image_path = project['main_image']
        if 'main_image' in request.files:
            file = request.files['main_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = str(uuid.uuid4()) + "_" + filename
                file_path = os.path.join(UPLOAD_PROJECTS_FOLDER, unique_name)
                file.save(file_path)
                main_image_path = f"uploads/projects/{unique_name}"
                
        # Parse existing extra images
        try:
            extra_images_paths = json.loads(project['extra_images']) if project['extra_images'] else []
        except:
            extra_images_paths = []
            
        # Handle deletion of existing images
        images_to_delete = request.form.getlist('delete_images')
        for img_path in images_to_delete:
            if img_path in extra_images_paths:
                extra_images_paths.remove(img_path)
                try:
                    os.remove(os.path.join('app', 'static', img_path))
                except:
                    pass

        # Handle new extra images upload
        if 'extra_images' in request.files:
            files = request.files.getlist('extra_images')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_name = str(uuid.uuid4()) + "_" + filename
                    file_path = os.path.join(UPLOAD_PROJECTS_FOLDER, unique_name)
                    file.save(file_path)
                    extra_images_paths.append(f"uploads/projects/{unique_name}")

        extra_images_json = json.dumps(extra_images_paths)
        
        try:
            conn.execute('''
                UPDATE projects 
                SET title = ?, slug = ?, teaser = ?, content = ?, main_image = ?, extra_images = ?, button_text = ?, button_url = ?, project_color = ?
                WHERE id = ?
            ''', (title, slug, teaser, content, main_image_path, extra_images_json, button_text, button_url, project_color, project_id))
            conn.commit()
            flash('Проект успешно обновлен!', 'success')
        except Exception as e:
            flash(f'Ошибка обновления (URL должен быть уникальным): {e}', 'danger')
        finally:
            conn.close()
            
        return redirect(url_for('admin.dashboard', tab='projects'))

    # Для GET запроса
    # Получим все данные для dashboard, чтобы отрендерить его с активной формой
    news_list = conn.execute('SELECT * FROM news ORDER BY id DESC').fetchall()
    pages_list = conn.execute('SELECT * FROM pages ORDER BY id DESC').fetchall()
    documents_list = conn.execute('SELECT * FROM documents ORDER BY id DESC').fetchall()
    projects_list = conn.execute('SELECT * FROM projects ORDER BY id DESC').fetchall()
    stats_list = conn.execute('SELECT * FROM statistics ORDER BY display_order ASC').fetchall()
    socials_list = conn.execute('SELECT * FROM social_networks ORDER BY display_order ASC').fetchall()
    contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
    menu_groups_list = conn.execute('SELECT DISTINCT menu_group FROM pages WHERE menu_group IS NOT NULL AND menu_group != ""').fetchall()
    conn.close()
    
    extra_images_list = []
    if project and project['extra_images']:
        try:
            extra_images_list = json.loads(project['extra_images'])
        except:
            pass
    
    return render_template('admin_dashboard.html', 
                           active_tab='projects',
                           edit_project_item=project,
                           extra_images_list=extra_images_list,
                           news_list=news_list,
                           pages_list=pages_list,
                           documents_list=documents_list,
                           projects_list=projects_list,
                           stats_list=stats_list,
                           socials_list=socials_list,
                           contact_settings=contact_settings,
                           menu_groups_list=menu_groups_list)


@bp.route('/toggle_project_status/<int:project_id>', methods=['POST'])
def toggle_project_status(project_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    current_status = request.form['current_status']
    new_status = 'archived' if current_status == 'published' else 'published'
    
    conn = get_db_connection()
    conn.execute('UPDATE projects SET status = ? WHERE id = ?', (new_status, project_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin.dashboard', tab='projects'))

@bp.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
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
                
        conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        flash('Проект удален!', 'success')
    conn.close()
    return redirect(url_for('admin.dashboard', tab='projects'))
