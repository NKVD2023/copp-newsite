from flask import request, redirect, url_for, flash
from app.admin import bp
from app.db import get_db_connection
from app.admin.core.auth import login_required
from app.admin.core.logger import log_admin_action
import os
from werkzeug.utils import secure_filename
from app.utils.image_utils import save_image_as_webp

UPLOAD_SOCIALS_FOLDER = os.path.join('app', 'static', 'uploads', 'socials')
ALLOWED_EXTENSIONS = {'png', 'svg', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handle_icon_upload(file, existing_icon_file=None):
    if file and file.filename != '' and allowed_file(file.filename):
        filename = save_image_as_webp(file, UPLOAD_SOCIALS_FOLDER, add_uuid=True)
        if filename:
            return f"uploads/socials/{filename}"
    return existing_icon_file

@bp.route('/socials/add', methods=['POST'])
@login_required
def add_social():
    """
    Добавление новой социальной сети (ссылка + иконка).
    Поддерживает как SVG-код, так и загрузку картинки/иконки файлом.
    """
    name = request.form.get('name')
    url = request.form.get('url')
    icon_svg = request.form.get('icon_svg', '')
    display_order = request.form.get('display_order', 0)
    
    icon_file = request.files.get('icon_file')
    existing_icon_file = request.form.get('existing_icon_file')
    image_path = handle_icon_upload(icon_file, existing_icon_file)
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO social_networks (name, url, icon_svg, display_order, image_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, url, icon_svg, display_order, image_path))
    
    soc_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    
    log_admin_action('CREATE', 'socials', entity_id=soc_id, details=f'Добавлена социальная сеть: "{name}"')
    
    flash('Социальная сеть успешно добавлена!', 'success')
    return redirect(url_for('admin.dashboard', tab='socials'))

@bp.route('/socials/<int:id>/edit', methods=['POST'])
@login_required
def edit_social(id):
    """
    Редактирование параметров социальной сети (название, ссылка, иконка, порядок отображения, статус).
    """
    name = request.form.get('name')
    url = request.form.get('url')
    icon_svg = request.form.get('icon_svg', '')
    display_order = request.form.get('display_order', 0)
    is_active = 1 if request.form.get('is_active') else 0
    
    icon_file = request.files.get('icon_file')
    existing_icon_file = request.form.get('existing_icon_file')
    image_path = handle_icon_upload(icon_file, existing_icon_file)
    
    conn = get_db_connection()
    
    conn.execute('''
        UPDATE social_networks
        SET name = ?, url = ?, icon_svg = ?, display_order = ?, is_active = ?, image_path = ?
        WHERE id = ?
    ''', (name, url, icon_svg, display_order, is_active, image_path, id))
    conn.commit()
    
    log_admin_action('UPDATE', 'socials', entity_id=id, details=f'Обновлена социальная сеть: "{name}"')
    
    flash('Социальная сеть успешно обновлена!', 'success')
    return redirect(url_for('admin.dashboard', tab='socials'))

@bp.route('/socials/<int:id>/delete', methods=['POST'])
@login_required
def delete_social(id):
    """
    Удаление социальной сети и связанного с ней файла иконки.
    """
    conn = get_db_connection()
    social = conn.execute('SELECT name, image_path FROM social_networks WHERE id = ?', (id,)).fetchone()
    soc_name = social['name'] if social else f"ID {id}"
    
    if social and social['image_path']:
        full_path = os.path.join('app', 'static', social['image_path'])
        if os.path.exists(full_path):
            os.remove(full_path)
            
    conn.execute('DELETE FROM social_networks WHERE id = ?', (id,))
    conn.commit()
    
    log_admin_action('DELETE', 'socials', entity_id=id, details=f'Удалена социальная сеть: "{soc_name}"')
    
    flash('Социальная сеть удалена.', 'success')
    return redirect(url_for('admin.dashboard', tab='socials'))
