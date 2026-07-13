from flask import render_template, request, redirect, url_for, flash, send_file
import os
from werkzeug.utils import secure_filename
from app.admin import bp
from app.admin.auth import login_required
from app.db import get_db_connection
from app.utils.image_utils import save_image_as_webp

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads', 'news')

@bp.route('/add_news', methods=['POST'])
@login_required
def add_news():
    """
    Создание новой новости или мероприятия.
    Обрабатывает загрузку файлов (основное фото и доп. фото),
    формирует дату публикации (по таймеру или текущую) и сохраняет запись в БД.
    """
    title = request.form.get('title')
    status = request.form.get('status')
    teaser = request.form.get('teaser')
    content = request.form.get('content')
    is_event = 1 if request.form.get('is_event') else 0
    event_date = request.form.get('event_date') if is_event else None
    event_location = request.form.get('event_location') if is_event else None
    
    publish_date = request.form.get('publish_date')
    if publish_date:
        publish_date = publish_date.replace('T', ' ')
        if len(publish_date) == 16:
            publish_date += ":00"
    else:
        from datetime import datetime
        publish_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    main_image_path = request.form.get('existing_main_image', '')
    if 'main_image' in request.files:
        file = request.files['main_image']
        if file and file.filename != '':
            filename = save_image_as_webp(file, UPLOAD_FOLDER)
            if filename:
                main_image_path = f"uploads/news/{filename}"

    extra_images_paths = request.form.getlist('existing_extra_images')
    if 'extra_images' in request.files:
        files = request.files.getlist('extra_images')
        for file in files:
            if file and file.filename != '':
                filename = save_image_as_webp(file, UPLOAD_FOLDER)
                if filename:
                    extra_images_paths.append(f"uploads/news/{filename}")
    
    extra_images_str = ",".join(extra_images_paths)

    with get_db_connection() as conn:
        try:
            conn.execute('''
                INSERT INTO news (title, teaser, content, main_image, extra_images, status, is_event, event_date, event_location, publish_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, teaser, content, main_image_path, extra_images_str, status, is_event, event_date, event_location, publish_date))
            conn.commit()
            flash("Новость успешно добавлена!", "success")
        except Exception as e:
            flash(f"Ошибка при сохранении: {e}", "error")

    return redirect(url_for('admin.dashboard'))


@bp.route('/edit_news/<int:news_id>', methods=['GET'])
@login_required
def edit_news(news_id):
    """
    Страница редактирования новости.
    Загружает полный дашборд, но передает конкретную новость (edit_item)
    для заполнения формы редактирования в модальном окне/вкладке.
    """
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
    
    from datetime import datetime
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
                           edit_item=edit_item,
                           now_str=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@bp.route('/update_news/<int:news_id>', methods=['POST'])
@login_required
def update_news(news_id):
    """
    Обработчик сохранения изменений новости.
    Принимает новые данные, загружает новые картинки (с удалением старых из ФС),
    обновляет запись в БД.
    """
    title = request.form.get('title')
    status = request.form.get('status')
    teaser = request.form.get('teaser')
    content = request.form.get('content')
    is_event = 1 if request.form.get('is_event') else 0
    event_date = request.form.get('event_date') if is_event else None
    event_location = request.form.get('event_location') if is_event else None
    
    publish_date = request.form.get('publish_date')
    if publish_date:
        publish_date = publish_date.replace('T', ' ')
        if len(publish_date) == 16:
            publish_date += ":00"
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    with get_db_connection() as conn:
        old_item = conn.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()
        
        main_image_path = old_item['main_image']
        extra_images_str = old_item['extra_images']
        existing_main = request.form.get('existing_main_image')
        
        if 'main_image' in request.files and request.files['main_image'].filename != '':
            file = request.files['main_image']
            filename = save_image_as_webp(file, UPLOAD_FOLDER)
            if filename:
                main_image_path = f"uploads/news/{filename}"
        elif existing_main:
            main_image_path = existing_main
                
        # Обновление доп. фото (добавление новых и сохранение выбранных)
        extra_paths = request.form.getlist('existing_extra_images')
        if 'extra_images' in request.files:
            files = request.files.getlist('extra_images')
            for file in files:
                if file and file.filename != '':
                    filename = save_image_as_webp(file, UPLOAD_FOLDER)
                    if filename:
                        extra_paths.append(f"uploads/news/{filename}")
        extra_images_str = ",".join(extra_paths)
                
        if publish_date:
            conn.execute('''
                UPDATE news 
                SET title = ?, teaser = ?, content = ?, main_image = ?, extra_images = ?, status = ?, is_event = ?, event_date = ?, event_location = ?, publish_date = ?
                WHERE id = ?
            ''', (title, teaser, content, main_image_path, extra_images_str, status, is_event, event_date, event_location, publish_date, news_id))
        else:
            conn.execute('''
                UPDATE news 
                SET title = ?, teaser = ?, content = ?, main_image = ?, extra_images = ?, status = ?, is_event = ?, event_date = ?, event_location = ?
                WHERE id = ?
            ''', (title, teaser, content, main_image_path, extra_images_str, status, is_event, event_date, event_location, news_id))
        conn.commit()
    
    flash("Новость успешно обновлена!", "success")
    return redirect(url_for('admin.dashboard'))


@bp.route('/toggle_news_status/<int:news_id>', methods=['POST'])
@login_required
def toggle_news_status(news_id):
    """
    Быстрое переключение статуса новости (Опубликована <-> В архиве).
    Вызывается кнопкой из таблицы новостей на дашборде.
    """
    current_status = request.form.get('current_status')
    new_status = 'archived' if current_status == 'published' else 'published'
    
    with get_db_connection() as conn:
        conn.execute('UPDATE news SET status = ? WHERE id = ?', (new_status, news_id))
        conn.commit()
    
    flash(f"Статус новости изменен на '{new_status}'", "success")
    return redirect(url_for('admin.dashboard'))


@bp.route('/delete_news/<int:news_id>', methods=['POST'])
@login_required
def delete_news(news_id):
    """
    Полное удаление новости из БД.
    Также физически удаляет прикрепленные к новости картинки из файловой системы.
    """
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


@bp.route('/export_news', methods=['GET'])
@login_required
def export_news():
    """
    Экспорт новостей в Excel.
    Принимает опциональные параметры month и status.
    """
    import pandas as pd
    import io
    from datetime import datetime
    from openpyxl.styles import Alignment, Font
    
    month = request.args.get('month')
    status = request.args.get('status')
    
    query = 'SELECT * FROM news WHERE 1=1'
    params = []
    
    if month:
        query += ' AND publish_date LIKE ?'
        params.append(f'{month}%')
    if status:
        query += ' AND status = ?'
        params.append(status)
        
    query += ' ORDER BY publish_date DESC'
    
    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        
    data = []
    for r in rows:
        data.append({
            'Название статьи': r['title'],
            'Дата публикации': r['publish_date'] or '',
            'Ссылка': url_for('main.news_detail', news_id=r['id'], _external=True)
        })
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Новости')
        
        # Получаем объект листа (worksheet) для стилизации
        workbook = writer.book
        worksheet = writer.sheets['Новости']
        
        # Добавляем строку "Итог"
        total_row_idx = len(df) + 2  # +1 для заголовка, +1 для следующей строки
        cell = worksheet.cell(row=total_row_idx, column=1, value=f"Итог: {len(df)} статей(и)")
        cell.font = Font(bold=True, size=12)
        
        # Настраиваем ширину колонок для удобства чтения
        worksheet.column_dimensions['A'].width = 70  # Название статьи
        worksheet.column_dimensions['B'].width = 25  # Дата
        worksheet.column_dimensions['C'].width = 60  # Ссылка
        
        # Стилизуем все ячейки (перенос текста, выравнивание, отступы)
        for row in worksheet.iter_rows(min_row=1, max_row=total_row_idx):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='left')
                
        # Стилизуем строку заголовков
        for cell in worksheet[1]:
            cell.font = Font(bold=True, size=12)
            
    output.seek(0)
    
    filename = f"news_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )