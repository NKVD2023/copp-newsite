import os
import io
import zipfile
import tempfile
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, send_file, current_app
from app.admin import bp
from app.admin.core.auth import login_required, module_required
from app.admin.core.logger import log_admin_action
from app.db import get_db_connection
from app.services.pdf_generator import generate_study_certificate_pdf


@bp.route('/study_certificates/update/<int:req_id>', methods=['POST'])
@login_required
@module_required('study_certificates')
def update_study_certificate(req_id):
    """
    Обновление параметров справки об обучении (заполняется сотрудником).
    """
    study_period_start = request.form.get('study_period_start', '').strip()
    study_period_end   = request.form.get('study_period_end', '').strip()
    is_state_support   = 1 if request.form.get('is_state_support') == '1' else 0
    funding_type       = request.form.get('funding_type', 'budget')
    order_number       = request.form.get('order_number', '').strip()
    order_date         = request.form.get('order_date', '').strip()
    cert_number        = request.form.get('cert_number', '').strip()
    cert_date          = request.form.get('cert_date', '').strip()
    # Если нажали «Сохранить и скачать» и дата выдачи не заполнена вручную — формируем сегодняшней датой
    if request.form.get('action_save_download') == '1' and not cert_date:
        cert_date = datetime.now().strftime('%Y-%m-%d')
    director_title     = request.form.get('director_title', 'Директор').strip()
    director_name      = request.form.get('director_name', 'М.И. Пальчук').strip()
    head_teacher_title = request.form.get('head_teacher_title', 'И.о. зав. учебной частью').strip()
    head_teacher_name  = request.form.get('head_teacher_name', 'В.А. Чупахина').strip()
    # При оформлении справки в модальном окне (Сохранить или Сохранить и скачать) статус всегда 'ready'
    status             = 'ready'
    group_number       = request.form.get('group_number', '').strip()
    copies_raw         = request.form.get('copies_count')
    try:
        copies_count = max(1, min(int(copies_raw or 1), 10))
    except (ValueError, TypeError):
        copies_count = 1

    conn = get_db_connection()
    conn.execute('''
        UPDATE study_cert_requests SET
            group_number = COALESCE(NULLIF(?, ''), group_number),
            copies_count = ?,
            study_period_start = ?,
            study_period_end = ?,
            is_state_support = ?,
            funding_type = ?,
            order_number = ?,
            order_date = ?,
            cert_number = ?,
            cert_date = ?,
            director_title = ?,
            director_name = ?,
            head_teacher_title = ?,
            head_teacher_name = ?,
            status = ?
        WHERE id = ?
    ''', (
        group_number, copies_count,
        study_period_start, study_period_end, is_state_support, funding_type,
        order_number, order_date, cert_number, cert_date,
        director_title, director_name, head_teacher_title, head_teacher_name,
        status, req_id
    ))
    conn.commit()

    log_admin_action('update', 'study_certificates', req_id, f"Оформлена справка об обучении #{req_id} (статус: Готово)")
    flash('Данные справки успешно сохранены, статус переключен в «Готово»', 'success')

    # Если была нажата кнопка «Сохранить и скачать PDF»
    if request.form.get('action_save_download') == '1':
        return redirect(url_for('admin.download_study_certificate', req_id=req_id))

    return redirect(url_for('admin.dashboard', tab='study_certificates'))


@bp.route('/study_certificates/update_status/<int:req_id>', methods=['POST'])
@login_required
@module_required('study_certificates')
def update_study_certificate_status(req_id):
    """
    Быстрая смена статуса из таблицы.
    """
    new_status = request.form.get('status')
    if new_status not in ('new', 'processed', 'ready'):
        flash('Недопустимый статус', 'danger')
        return redirect(url_for('admin.dashboard', tab='study_certificates'))

    conn = get_db_connection()
    conn.execute('UPDATE study_cert_requests SET status = ? WHERE id = ?', (new_status, req_id))
    conn.commit()

    log_admin_action('update_status', 'study_certificates', req_id, f"Статус заявки #{req_id} изменен на {new_status}")
    flash('Статус обновлен', 'success')
    return redirect(request.referrer or url_for('admin.dashboard', tab='study_certificates'))


import re

def _build_study_cert_filename(req_dict):
    """
    Формирует имя PDF-файла по правилу: {номер_группы}_{фамилия}.pdf
    Если группа не указана — Справка_{фамилия}_{id}.pdf
    """
    surname = req_dict['fio'].split()[0] if req_dict.get('fio') else 'Студент'
    surname = re.sub(r'[\\/*?:"<>|]', '', surname).strip()
    group = (req_dict.get('group_number') or '').strip()
    if group:
        group_clean = re.sub(r'[\\/*?:"<>|]', '', group).strip()
        return f"{group_clean}_{surname}.pdf"
    req_id = req_dict.get('id', '')
    return f"Справка_{surname}_{req_id}.pdf"


@bp.route('/study_certificates/download/<int:req_id>')
@login_required
@module_required('study_certificates')
def download_study_certificate(req_id):
    """
    Генерация и скачивание готовой справки об обучении в PDF.
    """
    conn = get_db_connection()
    req_data = conn.execute('SELECT * FROM study_cert_requests WHERE id = ?', (req_id,)).fetchone()

    if not req_data:
        flash('Заявка не найдена', 'danger')
        return redirect(url_for('admin.dashboard', tab='study_certificates'))

    req_dict = dict(req_data)

    # При скачивании формируем дату выдачи справки сегодняшней датой, если не была сформирована ранее
    if not req_dict.get('cert_date'):
        today_str = datetime.now().strftime('%Y-%m-%d')
        conn.execute("UPDATE study_cert_requests SET cert_date = ?, status = 'ready' WHERE id = ?", (today_str, req_id))
        conn.commit()
        req_dict['cert_date'] = today_str
        req_dict['status'] = 'ready'

    file_name = _build_study_cert_filename(req_dict)

    try:
        tmp_dir = os.path.join(tempfile.gettempdir(), 'copp_pdf_tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        file_path = os.path.join(tmp_dir, file_name)

        generate_study_certificate_pdf(req_dict, file_path)

        with open(file_path, 'rb') as f:
            pdf_bytes = io.BytesIO(f.read())

        try:
            os.remove(file_path)
        except OSError:
            pass

        log_admin_action('download_pdf', 'study_certificates', req_id, f"Скачана справка об обучении #{req_id} для {req_dict.get('fio')}")

        # При скачивании переводим статус в 'ready' если был 'new' или 'processed'
        if req_dict['status'] in ('new', 'processed'):
            conn.execute("UPDATE study_cert_requests SET status = 'ready' WHERE id = ?", (req_id,))
            conn.commit()

        pdf_bytes.seek(0)
        return send_file(pdf_bytes, as_attachment=True, download_name=file_name, mimetype='application/pdf')

    except Exception as e:
        flash(f'Ошибка при создании PDF: {e}', 'danger')
        return redirect(url_for('admin.dashboard', tab='study_certificates'))


@bp.route('/study_certificates/bulk_download', methods=['POST'])
@login_required
@module_required('study_certificates')
def bulk_download_study_certificates():
    """
    Массовая генерация и скачивание выбранных справок в ZIP архиве.
    """
    req_ids = request.form.getlist('cert_ids')
    if not req_ids:
        flash('Не выбрано ни одной заявки', 'warning')
        return redirect(url_for('admin.dashboard', tab='study_certificates'))

    req_ids = req_ids[:50]
    conn = get_db_connection()

    tmp_dir = os.path.join(tempfile.gettempdir(), 'copp_pdf_tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    zip_buffer = io.BytesIO()
    generated_count = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for req_id in req_ids:
            try:
                req_data = conn.execute('SELECT * FROM study_cert_requests WHERE id = ?', (req_id,)).fetchone()
                if not req_data:
                    continue

                req_dict = dict(req_data)

                # При массовом скачивании формируем дату выдачи справки, если не была сформирована
                if not req_dict.get('cert_date'):
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    conn.execute("UPDATE study_cert_requests SET cert_date = ?, status = 'ready' WHERE id = ?", (today_str, req_id))
                    req_dict['cert_date'] = today_str
                    req_dict['status'] = 'ready'

                file_name = _build_study_cert_filename(req_dict)
                file_path = os.path.join(tmp_dir, file_name)

                generate_study_certificate_pdf(req_dict, file_path)

                with open(file_path, 'rb') as f:
                    zf.writestr(file_name, f.read())

                try:
                    os.remove(file_path)
                except OSError:
                    pass

                if req_dict['status'] in ('new', 'processed'):
                    conn.execute("UPDATE study_cert_requests SET status = 'ready' WHERE id = ?", (req_id,))

                generated_count += 1
            except Exception as e:
                current_app.logger.error(f"Ошибка генерации справки #{req_id}: {e}")

    conn.commit()
    zip_buffer.seek(0)

    log_admin_action('bulk_download', 'study_certificates', details=f"Массовое скачивание {generated_count} справок об обучении")
    return send_file(zip_buffer, download_name='Справки_об_обучении.zip', as_attachment=True, mimetype='application/zip')


@bp.route('/study_certificates/bulk_action', methods=['POST'])
@login_required
@module_required('study_certificates')
def bulk_action_study_certificates():
    """
    Массовые действия над заявками (отметить 'Готово' или удалить).
    """
    action = request.form.get('action')
    req_ids = request.form.getlist('cert_ids')

    if not req_ids:
        flash('Ничего не выбрано', 'warning')
        return redirect(url_for('admin.dashboard', tab='study_certificates'))

    req_ids = req_ids[:200]
    conn = get_db_connection()

    if action == 'mark_ready':
        placeholders = ','.join('?' * len(req_ids))
        conn.execute(f"UPDATE study_cert_requests SET status = 'ready' WHERE id IN ({placeholders})", req_ids)
        flash(f'Статус "Готово" установлен для {len(req_ids)} заявок', 'success')
    elif action == 'delete':
        placeholders = ','.join('?' * len(req_ids))
        conn.execute(f"DELETE FROM study_cert_requests WHERE id IN ({placeholders})", req_ids)
        flash(f'Удалено {len(req_ids)} заявок', 'success')
    else:
        flash('Неизвестное действие', 'danger')
        return redirect(url_for('admin.dashboard', tab='study_certificates'))

    conn.commit()
    return redirect(url_for('admin.dashboard', tab='study_certificates'))
