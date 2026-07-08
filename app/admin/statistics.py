from flask import request, redirect, url_for, flash, session
from app.admin import bp
from app.db import get_db_connection

@bp.route('/statistics', methods=['POST'])
def statistics():
    """
    Массовое обновление статических блоков со статистикой (цифры на главной странице).
    Перезаписывает значения и порядок отображения для всех переданных ID.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    conn = get_db_connection()
    # Update existing records
    stat_ids = request.form.getlist('id')
    labels = request.form.getlist('label')
    values = request.form.getlist('value')
    display_orders = request.form.getlist('display_order')

    for i in range(len(stat_ids)):
        stat_id = stat_ids[i]
        label = labels[i]
        value = values[i]
        display_order = display_orders[i]
        conn.execute('UPDATE statistics SET label = ?, value = ?, display_order = ? WHERE id = ?',
                     (label, value, display_order, stat_id))
    conn.commit()
    conn.close()
    flash('Статистика успешно обновлена!', 'success')
    return redirect(url_for('admin.dashboard', tab='statistics'))
