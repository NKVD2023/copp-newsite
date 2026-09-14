import os
import io
import zipfile
from flask import render_template, request, redirect, url_for, flash, send_file, current_app
from app.admin import bp
from app.admin.core.auth import login_required, module_required
from app.admin.core.logger import log_admin_action
from app.db import get_db_connection
from app.services.pdf_generator import generate_income_certificate_pdf


@bp.route('/certificates')
@login_required
@module_required('certificates')
def list_certificates():
    conn = get_db_connection()
    status_filter = request.args.get('status')

    query = 'SELECT * FROM income_cert_requests'
    params = []

    if status_filter:
        query += ' WHERE status = ?'
        params.append(status_filter)

    query += ' ORDER BY created_at DESC'

    requests_list = conn.execute(query, params).fetchall()
    return render_template('admin/certificates/list.html', requests=requests_list, current_status=status_filter)


@bp.route('/certificates/update_status/<int:req_id>', methods=['POST'])
@login_required
@module_required('certificates')
def update_certificate_status(req_id):
    new_status = request.form.get('status')
    if new_status not in ('new', 'processed', 'ready'):
        flash('Недопустимый статус', 'danger')
        return redirect(url_for('admin.dashboard', tab='certificates'))
    conn = get_db_connection()
    conn.execute('UPDATE income_cert_requests SET status = ? WHERE id = ?', (new_status, req_id))
    conn.commit()
    flash('Статус обновлен', 'success')
    return redirect(request.referrer or url_for('admin.dashboard', tab='certificates'))


@bp.route('/certificates/download/<int:req_id>')
@login_required
@module_required('certificates')
def download_certificate(req_id):
    conn = get_db_connection()
    req_data = conn.execute('SELECT * FROM income_cert_requests WHERE id = ?', (req_id,)).fetchone()

    if not req_data:
        log_admin_action('download_pdf_fail', 'certificates', req_id, f"Заявка #{req_id} не найдена")
        flash('Заявка не найдена', 'danger')
        return redirect(url_for('admin.dashboard', tab='certificates'))

    surname = req_data['fio'].split()[0] if req_data['fio'] else 'Без_имени'
    file_name = f"Заявление_{surname}_{req_id}.pdf"

    try:
        tmp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        file_path = os.path.join(tmp_dir, file_name)

        generate_income_certificate_pdf(dict(req_data), file_path)

        # Читаем в память — PDF не должен оставаться на диске и быть публично доступен
        with open(file_path, 'rb') as f:
            pdf_bytes = io.BytesIO(f.read())

        try:
            os.remove(file_path)
        except OSError:
            pass

        log_admin_action('download_pdf', 'certificates', req_id, f"Скачано заявление от {req_data['fio']}")

        # Автоматическая смена статуса на Готово при первом скачивании
        if req_data['status'] == 'new':
            conn.execute("UPDATE income_cert_requests SET status = 'ready' WHERE id = ?", (req_id,))
            conn.commit()

        pdf_bytes.seek(0)
        return send_file(pdf_bytes, as_attachment=True, download_name=file_name, mimetype='application/pdf')

    except Exception as e:
        flash(f'Ошибка генерации PDF: {e}', 'danger')
        return redirect(url_for('admin.dashboard', tab='certificates'))


@bp.route('/certificates/bulk_download', methods=['POST'])
@login_required
@module_required('certificates')
def bulk_download_certificates():
    req_ids = request.form.getlist('cert_ids')
    if not req_ids:
        flash('Не выбрано ни одной заявки', 'warning')
        return redirect(url_for('admin.dashboard', tab='certificates'))

    req_ids = req_ids[:50]  # Защита от слишком большого запроса

    conn = get_db_connection()

    tmp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    zip_buffer = io.BytesIO()
    generated_count = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for req_id in req_ids:
            try:
                req_data = conn.execute(
                    'SELECT * FROM income_cert_requests WHERE id = ?', (req_id,)
                ).fetchone()
                if not req_data:
                    continue

                surname = req_data['fio'].split()[0] if req_data['fio'] else 'Без_имени'
                file_name = f"Заявление_{surname}_{req_id}.pdf"
                file_path = os.path.join(tmp_dir, file_name)

                generate_income_certificate_pdf(dict(req_data), file_path)

                # Читаем в память и сразу удаляем с диска
                with open(file_path, 'rb') as f:
                    zf.writestr(file_name, f.read())

                try:
                    os.remove(file_path)
                except OSError:
                    pass

                if req_data['status'] == 'new':
                    conn.execute("UPDATE income_cert_requests SET status = 'ready' WHERE id = ?", (req_id,))

                generated_count += 1

            except Exception as e:
                current_app.logger.error(f"Ошибка генерации PDF #{req_id}: {e}")

    conn.commit()
    zip_buffer.seek(0)

    log_admin_action('bulk_download', 'certificates', details=f"Массовое скачивание {generated_count} заявлений")

    return send_file(zip_buffer, download_name='Заявления_справки.zip', as_attachment=True, mimetype='application/zip')


@bp.route('/certificates/bulk_action', methods=['POST'])
@login_required
@module_required('certificates')
def bulk_action_certificates():
    action = request.form.get('action')
    req_ids = request.form.getlist('cert_ids')

    if not req_ids:
        flash('Ничего не выбрано', 'warning')
        return redirect(url_for('admin.dashboard', tab='certificates'))

    req_ids = req_ids[:200]  # Защита от слишком большого запроса

    conn = get_db_connection()

    if action == 'mark_ready':
        placeholders = ','.join('?' * len(req_ids))
        conn.execute(f"UPDATE income_cert_requests SET status = 'ready' WHERE id IN ({placeholders})", req_ids)
        flash(f'Статус изменён для {len(req_ids)} заявок', 'success')
    elif action == 'delete':
        placeholders = ','.join('?' * len(req_ids))
        conn.execute(f"DELETE FROM income_cert_requests WHERE id IN ({placeholders})", req_ids)
        flash(f'Удалено {len(req_ids)} заявок', 'success')
    else:
        flash('Неизвестное действие', 'danger')
        return redirect(url_for('admin.dashboard', tab='certificates'))

    conn.commit()
    return redirect(url_for('admin.dashboard', tab='certificates'))


