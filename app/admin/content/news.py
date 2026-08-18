from flask import render_template, request, redirect, url_for, flash, send_file
import os
from werkzeug.utils import secure_filename
from app.admin import bp
from app.admin.core.auth import login_required
from app.admin.core.logger import log_admin_action
from app.db import get_db_connection
from app.services.upload_service import UploadService
from app.repositories.models import NewsRepository

@bp.route('/add_news', methods=['POST'])
@login_required
def add_news():
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

    main_image_path = UploadService.handle_main_image(upload_folder='uploads/news')
    extra_images_str = UploadService.handle_extra_images(upload_folder='uploads/news')

    try:
        data = {
            'title': title, 'teaser': teaser, 'content': content, 
            'main_image_path': main_image_path, 'extra_images_str': extra_images_str, 
            'status': status, 'is_event': is_event, 'event_date': event_date, 
            'event_location': event_location, 'publish_date': publish_date
        }
        news_id = NewsRepository.create(data)
        log_admin_action('CREATE', 'news', entity_id=news_id, details=f'Добавлена новость: "{title}"')
        flash("Новость успешно добавлена!", "success")
    except Exception as e:
        flash(f"Ошибка при сохранении: {e}", "error")

    return redirect(url_for('admin.dashboard', tab='news'))

@bp.route('/edit_news/<int:news_id>', methods=['GET'])
@login_required
def edit_news(news_id):
    return redirect(url_for('admin.dashboard', tab='news', edit_news_id=news_id))

@bp.route('/update_news/<int:news_id>', methods=['POST'])
@login_required
def update_news(news_id):
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
            
    main_image_path = UploadService.handle_main_image(upload_folder='uploads/news')
    extra_images_str = UploadService.handle_extra_images(upload_folder='uploads/news')

    try:
        data = {
            'title': title, 'teaser': teaser, 'content': content, 
            'main_image_path': main_image_path, 'extra_images_str': extra_images_str, 
            'status': status, 'is_event': is_event, 'event_date': event_date, 
            'event_location': event_location, 'publish_date': publish_date
        }
        NewsRepository.update(news_id, data)
        log_admin_action('UPDATE', 'news', entity_id=news_id, details=f'Обновлена новость: "{title}"')
        flash("Новость успешно обновлена!", "success")
    except Exception as e:
        flash(f"Ошибка при обновлении: {e}", "error")
        
    return redirect(url_for('admin.dashboard', tab='news'))

@bp.route('/toggle_news_status/<int:news_id>', methods=['POST'])
@login_required
def toggle_news_status(news_id):
    current_status = request.form.get('current_status')
    new_status = 'archived' if current_status == 'published' else 'published'
    
    try:
        NewsRepository.update_status(news_id, new_status)
        item = NewsRepository.get_by_id(news_id)
        log_title = item['title'] if item else f"ID {news_id}"
        action_desc = "Опубликована" if new_status == 'published' else "Отправлена в архив"
        log_admin_action('UPDATE', 'news', entity_id=news_id, details=f'Изменен статус новости "{log_title}": {action_desc}')
        flash(f"Статус новости изменен на '{new_status}'", "success")
    except Exception as e:
        flash(f"Ошибка: {e}", "error")
        
    return redirect(url_for('admin.dashboard', tab='news'))

@bp.route('/delete_news/<int:news_id>', methods=['POST'])
@login_required
def delete_news(news_id):
    item = NewsRepository.get_by_id(news_id)
    if item:
        NewsRepository.delete(news_id)
        log_title = item['title']
        log_admin_action('DELETE', 'news', entity_id=news_id, details=f'Удалена новость: "{log_title}"')
        
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
    return redirect(url_for('admin.dashboard', tab='news'))

@bp.route('/export_news', methods=['GET'])
@login_required
def export_news():
    import pandas as pd
    import io
    from datetime import datetime
    from openpyxl.styles import Alignment, Font
    
    month = request.args.get('month')
    status = request.args.get('status')
    
    rows = NewsRepository.export(month=month, status=status)
        
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
