from flask import request, redirect, url_for, flash, session
from app.admin import bp
from app.db import get_db_connection
import os
from werkzeug.utils import secure_filename

UPLOAD_SOCIALS_FOLDER = os.path.join('app', 'static', 'uploads', 'socials')
ALLOWED_EXTENSIONS = {'png', 'svg', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handle_icon_upload(file):
    if file and file.filename != '' and allowed_file(file.filename):
        os.makedirs(UPLOAD_SOCIALS_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        base, extension = os.path.splitext(filename)
        counter = 1
        filepath = os.path.join(UPLOAD_SOCIALS_FOLDER, filename)
        while os.path.exists(filepath):
            filename = f"{base}_{counter}{extension}"
            filepath = os.path.join(UPLOAD_SOCIALS_FOLDER, filename)
            counter += 1
            
        file.save(filepath)
        return f"uploads/socials/{filename}"
    return None

@bp.route('/socials/add', methods=['POST'])
def add_social():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    name = request.form.get('name')
    url = request.form.get('url')
    icon_svg = request.form.get('icon_svg', '')
    display_order = request.form.get('display_order', 0)
    
    icon_file = request.files.get('icon_file')
    image_path = handle_icon_upload(icon_file)
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO social_networks (name, url, icon_svg, display_order, image_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, url, icon_svg, display_order, image_path))
    conn.commit()
    conn.close()
    
    flash('Социальная сеть успешно добавлена!', 'success')
    return redirect(url_for('admin.dashboard', tab='socials'))

@bp.route('/socials/<int:id>/edit', methods=['POST'])
def edit_social(id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    name = request.form.get('name')
    url = request.form.get('url')
    icon_svg = request.form.get('icon_svg', '')
    display_order = request.form.get('display_order', 0)
    is_active = 1 if request.form.get('is_active') else 0
    
    icon_file = request.files.get('icon_file')
    image_path = handle_icon_upload(icon_file)
    
    conn = get_db_connection()
    
    if image_path:
        conn.execute('''
            UPDATE social_networks
            SET name = ?, url = ?, icon_svg = ?, display_order = ?, is_active = ?, image_path = ?
            WHERE id = ?
        ''', (name, url, icon_svg, display_order, is_active, image_path, id))
    else:
        conn.execute('''
            UPDATE social_networks
            SET name = ?, url = ?, icon_svg = ?, display_order = ?, is_active = ?
            WHERE id = ?
        ''', (name, url, icon_svg, display_order, is_active, id))
    conn.commit()
    conn.close()
    
    flash('Социальная сеть успешно обновлена!', 'success')
    return redirect(url_for('admin.dashboard', tab='socials'))

@bp.route('/socials/<int:id>/delete', methods=['POST'])
def delete_social(id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    conn = get_db_connection()
    social = conn.execute('SELECT image_path FROM social_networks WHERE id = ?', (id,)).fetchone()
    if social and social['image_path']:
        full_path = os.path.join('app', 'static', social['image_path'])
        if os.path.exists(full_path):
            os.remove(full_path)
            
    conn.execute('DELETE FROM social_networks WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Социальная сеть удалена.', 'success')
    return redirect(url_for('admin.dashboard', tab='socials'))
