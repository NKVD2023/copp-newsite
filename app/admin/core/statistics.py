from flask import request, redirect, url_for, flash
from app.admin import bp
from app.db import get_db_connection
from app.admin.core.auth import login_required

@bp.route('/statistics', methods=['POST'])
@login_required
def statistics():
    """
    Массовое обновление статических блоков со статистикой (цифры на главной странице).
    Перезаписывает значения и порядок отображения для всех переданных ID.
    """
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
    flash('Статистика успешно обновлена!', 'success')
    return redirect(url_for('admin.dashboard', tab='statistics'))
