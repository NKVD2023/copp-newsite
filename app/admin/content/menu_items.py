from flask import request, redirect, url_for, flash
from app.admin import bp
from app.admin.core.auth import login_required
from app.db import get_db_connection

@bp.route('/menu/add', methods=['POST'])
@login_required
def menu_add():
    title = request.form.get('title')
    url = request.form.get('url')
    parent_id = request.form.get('parent_id') or None
    position = request.form.get('position', type=int) or 0
    type = request.form.get('type') or 'static'
    
    with get_db_connection() as conn:
        conn.execute(
            'INSERT INTO menu_items (title, url, parent_id, position, type) VALUES (?, ?, ?, ?, ?)',
            (title, url, parent_id, position, type)
        )
    flash('Пункт меню успешно добавлен.', 'success')
    return redirect(url_for('admin.dashboard', tab='menu'))

@bp.route('/menu/edit/<int:item_id>', methods=['POST'])
@login_required
def menu_edit(item_id):
    title = request.form.get('title')
    url = request.form.get('url')
    parent_id = request.form.get('parent_id') or None
    position = request.form.get('position', type=int) or 0
    type = request.form.get('type') or 'static'
    is_active = 1 if request.form.get('is_active') else 0
    
    with get_db_connection() as conn:
        conn.execute(
            'UPDATE menu_items SET title=?, url=?, parent_id=?, position=?, type=?, is_active=? WHERE id=?',
            (title, url, parent_id, position, type, is_active, item_id)
        )
    flash('Пункт меню обновлен.', 'success')
    return redirect(url_for('admin.dashboard', tab='menu'))

@bp.route('/menu/delete/<int:item_id>', methods=['POST'])
@login_required
def menu_delete(item_id):
    with get_db_connection() as conn:
        # Сначала удаляем дочерние элементы
        conn.execute('DELETE FROM menu_items WHERE parent_id = ?', (item_id,))
        # Затем удаляем сам элемент
        conn.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))
    flash('Пункт меню удален.', 'success')
    return redirect(url_for('admin.dashboard', tab='menu'))
