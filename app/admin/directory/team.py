from flask import request, redirect, url_for, flash
from app.admin import bp
from app.db import get_db_connection
from app.admin.core.auth import login_required
import os
from werkzeug.utils import secure_filename
from app.utils.image_utils import save_image_as_webp

UPLOAD_TEAM_FOLDER = os.path.join('app', 'static', 'uploads', 'team')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handle_icon_upload(file, existing_icon_file=None):
    if file and file.filename != '' and allowed_file(file.filename):
        filename = save_image_as_webp(file, UPLOAD_TEAM_FOLDER, add_uuid=True)
        if filename:
            return f"uploads/team/{filename}"
    return existing_icon_file

@bp.route('/team/add', methods=['POST'])
@login_required
def add_team_member():
    full_name = request.form.get('full_name')
    position = request.form.get('position')
    email = request.form.get('email', '')
    display_order = request.form.get('display_order', 0)
    
    icon_file = request.files.get('image_file')
    existing_icon_file = request.form.get('existing_image_file')
    
    os.makedirs(UPLOAD_TEAM_FOLDER, exist_ok=True)
    image_path = handle_icon_upload(icon_file, existing_icon_file)
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO team_members (full_name, position, email, display_order, image_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (full_name, position, email, display_order, image_path))
    conn.commit()
    
    flash('Сотрудник успешно добавлен!', 'success')
    return redirect(url_for('admin.dashboard', tab='team'))

@bp.route('/team/<int:id>/edit', methods=['POST'])
@login_required
def edit_team_member(id):
    full_name = request.form.get('full_name')
    position = request.form.get('position')
    email = request.form.get('email', '')
    display_order = request.form.get('display_order', 0)
    
    icon_file = request.files.get('image_file')
    existing_icon_file = request.form.get('existing_image_file')
    
    os.makedirs(UPLOAD_TEAM_FOLDER, exist_ok=True)
    image_path = handle_icon_upload(icon_file, existing_icon_file)
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE team_members
        SET full_name = ?, position = ?, email = ?, display_order = ?, image_path = ?
        WHERE id = ?
    ''', (full_name, position, email, display_order, image_path, id))
    conn.commit()
    
    flash('Сотрудник успешно обновлен!', 'success')
    return redirect(url_for('admin.dashboard', tab='team'))

@bp.route('/team/<int:id>/delete', methods=['POST'])
@login_required
def delete_team_member(id):
    conn = get_db_connection()
    member = conn.execute('SELECT image_path FROM team_members WHERE id = ?', (id,)).fetchone()
    if member and member['image_path']:
        full_path = os.path.join('app', 'static', member['image_path'])
        if os.path.exists(full_path):
            os.remove(full_path)
            
    conn.execute('DELETE FROM team_members WHERE id = ?', (id,))
    conn.commit()
    
    flash('Сотрудник удален.', 'success')
    return redirect(url_for('admin.dashboard', tab='team'))
