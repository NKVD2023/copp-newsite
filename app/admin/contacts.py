from flask import request, redirect, url_for, flash, session
from app.admin import bp
from app.db import get_db_connection

@bp.route('/contact_settings/update', methods=['POST'])
def update_contact_settings():
    """
    Обновление контактной информации организации (телефон, email, адрес и т.д.).
    Данные сохраняются в таблице contact_settings.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    title = request.form.get('title')
    org_name = request.form.get('org_name')
    phones = request.form.get('phones')
    email = request.form.get('email')
    address = request.form.get('address')
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE contact_settings
        SET title = ?, org_name = ?, phones = ?, email = ?, address = ?
        WHERE id = 1
    ''', (title, org_name, phones, email, address))
    conn.commit()
    conn.close()
    
    flash('Настройки контактов успешно обновлены!', 'success')
    return redirect(url_for('admin.dashboard', tab='contacts'))

@bp.route('/contact_requests/<int:id>/mark_read', methods=['POST'])
def mark_request_read(id):
    """
    Пометка входящей заявки с формы обратной связи как "прочитанной".
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    conn = get_db_connection()
    conn.execute('UPDATE contact_requests SET status = "read" WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Заявка отмечена как прочитанная.', 'success')
    return redirect(url_for('admin.dashboard', tab='contacts'))

@bp.route('/contact_requests/<int:id>/delete', methods=['POST'])
def delete_request(id):
    """
    Удаление входящей заявки (формы обратной связи) из базы данных.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM contact_requests WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Заявка удалена.', 'success')
    return redirect(url_for('admin.dashboard', tab='contacts'))
