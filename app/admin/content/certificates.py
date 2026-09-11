import os
from flask import render_template, request, redirect, url_for, flash, send_file, current_app
from app.admin import bp
from app.admin.core.auth import login_required
from app.admin.core.logger import log_admin_action
from app.db import get_db_connection
from app.services.pdf_generator import generate_income_certificate_pdf

@bp.route('/certificates')
@login_required
def list_certificates():
    conn = get_db_connection()
    status_filter = request.args.get('status')
    
    query = 'SELECT * FROM income_cert_requests'
    params = []
    
    if status_filter:
        query += ' WHERE status = ?'
        params.append(status_filter)
        
    query += ' ORDER BY created_at DESC'
    
    requests = conn.execute(query, params).fetchall()
    return render_template('admin/certificates/list.html', requests=requests, current_status=status_filter)

@bp.route('/certificates/update_status/<int:req_id>', methods=['POST'])
@login_required
def update_certificate_status(req_id):
    new_status = request.form.get('status')
    conn = get_db_connection()
    conn.execute('UPDATE income_cert_requests SET status = ? WHERE id = ?', (new_status, req_id))
    conn.commit()
    flash('Статус обновлен', 'success')
    return redirect(request.referrer or url_for('admin.dashboard', tab='certificates'))

@bp.route('/certificates/download/<int:req_id>')
@login_required
def download_certificate(req_id):
    conn = get_db_connection()
    req_data = conn.execute('SELECT * FROM income_cert_requests WHERE id = ?', (req_id,)).fetchone()
    
    if not req_data:
        flash('Заявка не найдена', 'danger')
        return redirect(url_for('admin.dashboard', tab='certificates'))
        
    tmp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    
    # Имя файла по фамилии
    surname = req_data['fio'].split()[0] if req_data['fio'] else 'Без_имени'
    file_name = f"Заявление_{surname}_{req_id}.pdf"
    file_path = os.path.join(tmp_dir, file_name)
    
    try:
        generate_income_certificate_pdf(dict(req_data), file_path)
        log_admin_action('download_pdf', 'certificates', req_id, f"Скачано заявление от {req_data['fio']}")
        
        # Автоматическая смена статуса на Готово (ready)
        if req_data['status'] == 'new':
            conn.execute("UPDATE income_cert_requests SET status = 'ready' WHERE id = ?", (req_id,))
            conn.commit()
            
        return send_file(file_path, as_attachment=True, download_name=file_name)
    except Exception as e:
        flash(f'Ошибка генерации PDF: {e}', 'danger')
        return redirect(url_for('admin.dashboard', tab='certificates'))

@bp.route('/certificates/bulk_download', methods=['POST'])
@login_required
def bulk_download_certificates():
    req_ids = request.form.getlist('cert_ids')
    if not req_ids:
        flash('Не выбрано ни одной заявки', 'warning')
        return redirect(url_for('admin.dashboard', tab='certificates'))
        
    conn = get_db_connection()
    
    import zipfile
    import io
    
    memory_file = io.BytesIO()
    
    tmp_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for req_id in req_ids:
            req_data = conn.execute('SELECT * FROM income_cert_requests WHERE id = ?', (req_id,)).fetchone()
            if req_data:
                surname = req_data['fio'].split()[0] if req_data['fio'] else 'Без_имени'
                file_name = f"Заявление_{surname}_{req_id}.pdf"
                file_path = os.path.join(tmp_dir, file_name)
                
                # Генерируем PDF
                generate_income_certificate_pdf(dict(req_data), file_path)
                
                # Добавляем в ZIP
                zf.write(file_path, arcname=file_name)
                
                # Авто-смена статуса
                if req_data['status'] == 'new':
                    conn.execute("UPDATE income_cert_requests SET status = 'ready' WHERE id = ?", (req_id,))
                    
    conn.commit()
    memory_file.seek(0)
    
    log_admin_action('bulk_download', 'certificates', details=f"Массовое скачивание {len(req_ids)} заявлений")
    
    return send_file(memory_file, download_name='Заявления_справки.zip', as_attachment=True)

@bp.route('/certificates/bulk_action', methods=['POST'])
@login_required
def bulk_action_certificates():
    action = request.form.get('action')
    req_ids = request.form.getlist('cert_ids')
    
    if not req_ids:
        flash('Ничего не выбрано', 'warning')
        return redirect(url_for('admin.dashboard', tab='certificates'))
        
    conn = get_db_connection()
    
    if action == 'mark_ready':
        placeholders = ','.join('?' * len(req_ids))
        conn.execute(f"UPDATE income_cert_requests SET status = 'ready' WHERE id IN ({placeholders})", req_ids)
        flash(f'Статус изменен для {len(req_ids)} заявок', 'success')
    elif action == 'delete':
        placeholders = ','.join('?' * len(req_ids))
        conn.execute(f"DELETE FROM income_cert_requests WHERE id IN ({placeholders})", req_ids)
        flash(f'Удалено {len(req_ids)} заявок', 'success')
        
    conn.commit()
    return redirect(url_for('admin.dashboard', tab='certificates'))
