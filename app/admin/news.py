from flask import render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from app.admin import bp
from app.db import get_db_connection

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads', 'news')

@bp.route('/add_news', methods=['POST'])
def add_news():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))

    title = request.form.get('title')
    status = request.form.get('status')
    teaser = request.form.get('teaser')
    content = request.form.get('content')
    is_event = 1 if request.form.get('is_event') else 0
    event_date = request.form.get('event_date') if is_event else None
    event_location = request.form.get('event_location') if is_event else None

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    main_image_path = ""
    if 'main_image' in request.files:
        file = request.files['main_image']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            main_image_path = f"uploads/news/{filename}"

    extra_images_paths = []
    if 'extra_images' in request.files:
        files = request.files.getlist('extra_images')
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                extra_images_paths.append(f"uploads/news/{filename}")
    
    extra_images_str = ",".join(extra_images_paths)

    with get_db_connection() as conn:
        try:
            conn.execute('''
                INSERT INTO news (title, teaser, content, main_image, extra_images, status, is_event, event_date, event_location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, teaser, content, main_image_path, extra_images_str, status, is_event, event_date, event_location))
            conn.commit()
            flash("Новость успешно добавлена!", "success")
        except Exception as e:
            flash(f"Ошибка при сохранении: {e}", "error")

    return redirect(url_for('admin.dashboard'))


@bp.route('/edit_news/<int:news_id>', methods=['GET'])
def edit_news(news_id):
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
        menu_groups_list = conn.execute('SELECT DISTINCT menu_group FROM pages WHERE menu_group IS NOT NULL AND menu_group != ""').fetchall()
        edit_item = conn.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()
    
    return render_template('admin_dashboard.html', 
                           active_tab='news',
                           news_list=news_list, 
                           pages_list=pages_list,
                           documents_list=documents_list,
                           projects_list=projects_list,
                           stats_list=stats_list,
                           socials_list=socials_list,
                           contact_settings=contact_settings,
                           menu_groups_list=menu_groups_list,
                           edit_item=edit_item)


@bp.route('/update_news/<int:news_id>', methods=['POST'])
def update_news(news_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    title = request.form.get('title')
    status = request.form.get('status')
    teaser = request.form.get('teaser')
    content = request.form.get('content')
    is_event = 1 if request.form.get('is_event') else 0
    event_date = request.form.get('event_date') if is_event else None
    event_location = request.form.get('event_location') if is_event else None
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    with get_db_connection() as conn:
        old_item = conn.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()
        
        main_image_path = old_item['main_image']
        extra_images_str = old_item['extra_images']
        
        # Обновление главного фото и удаление старого
        if 'main_image' in request.files:
            file = request.files['main_image']
            if file and file.filename != '':
                # Удаляем старый файл
                if main_image_path:
                    old_path = os.path.join('app', 'static', main_image_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                        
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                main_image_path = f"uploads/news/{filename}"
                
        # Обновление доп. фото и удаление старых
        if 'extra_images' in request.files:
            files = request.files.getlist('extra_images')
            if files and files[0].filename != '':
                # Удаляем старые файлы
                if extra_images_str:
                    for ext_img in extra_images_str.split(','):
                        if ext_img:
                            old_ext_path = os.path.join('app', 'static', ext_img)
                            if os.path.exists(old_ext_path):
                                os.remove(old_ext_path)

                extra_paths = []
                for file in files:
                    if file and file.filename != '':
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(UPLOAD_FOLDER, filename))
                        extra_paths.append(f"uploads/news/{filename}")
                extra_images_str = ",".join(extra_paths)
                
        conn.execute('''
            UPDATE news 
            SET title = ?, teaser = ?, content = ?, main_image = ?, extra_images = ?, status = ?, is_event = ?, event_date = ?, event_location = ?
            WHERE id = ?
        ''', (title, teaser, content, main_image_path, extra_images_str, status, is_event, event_date, event_location, news_id))
        conn.commit()
    
    flash("Новость успешно обновлена!", "success")
    return redirect(url_for('admin.dashboard'))


@bp.route('/toggle_news_status/<int:news_id>', methods=['POST'])
def toggle_news_status(news_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    
    current_status = request.form.get('current_status')
    new_status = 'archived' if current_status == 'published' else 'published'
    
    with get_db_connection() as conn:
        conn.execute('UPDATE news SET status = ? WHERE id = ?', (new_status, news_id))
        conn.commit()
    
    flash(f"Статус новости изменен на '{new_status}'", "success")
    return redirect(url_for('admin.dashboard'))


@bp.route('/delete_news/<int:news_id>', methods=['POST'])
def delete_news(news_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    with get_db_connection() as conn:
        item = conn.execute('SELECT main_image, extra_images FROM news WHERE id = ?', (news_id,)).fetchone()
        
        if item:
            # Удаляем запись из БД
            conn.execute('DELETE FROM news WHERE id = ?', (news_id,))
            conn.commit()
            
            # Физически удаляем файлы картинок
            if item['main_image']:
                main_img_path = os.path.join('app', 'static', item['main_image'])
                if os.path.exists(main_img_path):
                    os.remove(main_img_path)
                    
            if item['extra_images']:
                for ext_img in item['extra_images'].split(','):
                    if ext_img:
                        ext_img_path = os.path.join('app', 'static', ext_img)
                        if os.path.exists(ext_img_path):
                            os.remove(ext_img_path)
    
    flash("Новость и прикрепленные файлы успешно удалены!", "success")
    return redirect(url_for('admin.dashboard'))