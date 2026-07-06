import os
from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from app.admin import bp
from app.db import get_db_connection

UPLOAD_DOCS_FOLDER = os.path.join('app', 'static', 'uploads', 'documents')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar', 'txt', 'rtf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload_document', methods=['POST'])
def upload_document():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    if 'document' not in request.files:
        flash('Нет файла для загрузки', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    file = request.files['document']
    if file.filename == '':
        flash('Файл не выбран', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    if file and allowed_file(file.filename):
        os.makedirs(UPLOAD_DOCS_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        # Avoid overwriting existing files with the same name
        base, extension = os.path.splitext(filename)
        counter = 1
        filepath = os.path.join(UPLOAD_DOCS_FOLDER, filename)
        while os.path.exists(filepath):
            filename = f"{base}_{counter}{extension}"
            filepath = os.path.join(UPLOAD_DOCS_FOLDER, filename)
            counter += 1
            
        file.save(filepath)
        
        db_filepath = f"uploads/documents/{filename}"
        
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO documents (original_name, filepath)
                VALUES (?, ?)
            ''', (file.filename, db_filepath))
            conn.commit()
            
        if request.form.get('ajax'):
            return {'success': True, 'filepath': url_for('static', filename=db_filepath)}
            
        flash("Документ успешно загружен!", "success")
    else:
        if request.form.get('ajax'):
            return {'success': False, 'error': f"Недопустимый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"}
        flash(f"Недопустимый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}", "danger")
        
    return redirect(url_for('admin.dashboard', tab='documents'))

@bp.route('/delete_document/<int:doc_id>', methods=['POST'])
def delete_document(doc_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    with get_db_connection() as conn:
        doc = conn.execute('SELECT filepath FROM documents WHERE id = ?', (doc_id,)).fetchone()
        
        if doc:
            full_path = os.path.join('app', 'static', doc['filepath'])
            if os.path.exists(full_path):
                os.remove(full_path)
                
            conn.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
            conn.commit()
            flash("Документ удален!", "success")
            
    return redirect(url_for('admin.dashboard', tab='documents'))

@bp.route('/delete_media', methods=['POST'])
def delete_media():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    filepath = request.form.get('filepath')
    if not filepath:
        flash("Путь к файлу не указан.", "danger")
        return redirect(url_for('admin.dashboard', tab='documents'))
        
    # Security check: ensure path starts with uploads/ and has no directory traversal
    if '..' in filepath or not filepath.startswith('uploads/'):
        flash("Недопустимый путь к файлу.", "danger")
        return redirect(url_for('admin.dashboard', tab='documents'))
        
    full_path = os.path.join('app', 'static', filepath)
    
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            
            # Clean up documents table if it was a document
            with get_db_connection() as conn:
                conn.execute('DELETE FROM documents WHERE filepath = ?', (filepath,))
                conn.commit()
                
            flash(f"Файл успешно удален!", "success")
        except Exception as e:
            flash(f"Ошибка при удалении файла: {e}", "danger")
    else:
        flash("Файл не найден.", "danger")
        
    return redirect(url_for('admin.dashboard', tab='documents'))
