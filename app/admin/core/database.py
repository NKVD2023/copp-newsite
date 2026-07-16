import os
import csv
import io
import shutil
import zipfile
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, send_file, Response
from app.admin import bp
from app.admin.core.auth import login_required
from app.db import get_db_connection
from werkzeug.utils import secure_filename

DB_FILE_PATH = 'coppdb.sqlite'

@bp.route('/db/table/<table_name>')
@login_required
def db_view_table(table_name):
    """
    Отображение содержимого таблицы БД в админке.
    Для предотвращения падения браузера лимит установлен на 500 записей.
    """
    conn = get_db_connection()
    try:
        # Check if table exists to prevent SQL injection via URL
        table_check = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
        if not table_check:
            flash(f"Таблица {table_name} не найдена", "danger")
            return redirect(url_for('admin.dashboard', tab='database'))

        columns_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = [col['name'] for col in columns_info]
        pk_col = next((col['name'] for col in columns_info if col['pk'] == 1), None)
        
        # We limit the rows to 500 to prevent browser crash on huge tables
        rows = conn.execute(f"SELECT * FROM {table_name} LIMIT 500").fetchall()
        
        return render_template('admin_tabs/db_table_partial.html', table_name=table_name, columns=columns, rows=rows, columns_info=columns_info, pk_col=pk_col)
    except Exception as e:
        return f"<div class='alert alert-danger'>Ошибка: {str(e)}</div>"

@bp.route('/db/export/csv/<table_name>')
@login_required
def db_export_csv(table_name):
    """
    Экспорт выбранной таблицы БД в формате CSV.
    """
    conn = get_db_connection()
    try:
        columns_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        if not columns_info:
            flash("Таблица не найдена", "danger")
            return redirect(url_for('admin.dashboard', tab='database'))
            
        columns = [col['name'] for col in columns_info]
        rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
        
        # Create CSV in memory
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(columns)
        for row in rows:
            cw.writerow([row[col] for col in columns])
            
        output = si.getvalue()
        
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={table_name}_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    except Exception as e:
        flash(f"Ошибка экспорта: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard', tab='database'))

@bp.route('/db/export/full')
@login_required
def db_export_full():
    """
    Создание и скачивание полного бэкапа (БД + папка uploads) в виде .zip архива.
    """
    try:
        uploads_dir = os.path.join('app', 'static', 'uploads')
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Добавляем базу данных
            if os.path.exists(DB_FILE_PATH):
                zf.write(DB_FILE_PATH, arcname=os.path.basename(DB_FILE_PATH))
                
            # 2. Добавляем папку uploads
            if os.path.exists(uploads_dir):
                for root, dirs, files in os.walk(uploads_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Вычисляем относительный путь внутри архива (в папке uploads/)
                        arcname = os.path.join('uploads', os.path.relpath(file_path, uploads_dir))
                        zf.write(file_path, arcname=arcname)
                        
        memory_file.seek(0)
        filename = f"copp-site-{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        return send_file(memory_file, download_name=filename, as_attachment=True, mimetype='application/zip')
    except Exception as e:
        flash(f"Ошибка создания полного бэкапа: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard', tab='database'))

@bp.route('/db/execute_sql', methods=['POST'])
@login_required
def db_execute_sql():
    """
    Выполнение произвольного SQL-запроса из админки.
    """
    query = request.form.get('sql_query', '').strip()
    if not query:
        flash("Запрос пуст", "warning")
        return redirect(url_for('admin.dashboard', tab='database'))
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        
        if query.upper().startswith("SELECT") or query.upper().startswith("PRAGMA"):
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            flash(f"Выполнено успешно. Найдено строк: {len(rows)}", "success")
            # In a real heavy app we would render a generic table. For now, we just pass rows as flash or generic UI.
            # But since it's a simple dashboard redirect, we will store results in session (only if small) or just show success.
            # To keep it simple, we just show success.
        else:
            conn.commit()
            flash(f"Запрос выполнен успешно. Затронуто строк: {cursor.rowcount}", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Ошибка выполнения SQL: {str(e)}", "danger")
        
    return redirect(url_for('admin.dashboard', tab='database'))

@bp.route('/db/import/full', methods=['POST'])
@login_required
def db_import_full():
    """
    Восстановление полного бэкапа из загруженного .zip файла.
    - Делает резервную копию текущей БД.
    - Заменяет БД файлом из архива.
    - Извлекает папку uploads, пропуская уже существующие файлы.
    """
    if 'backup_file' not in request.files:
        flash('Файл не выбран', 'warning')
        return redirect(url_for('admin.dashboard', tab='database'))
        
    file = request.files['backup_file']
    if file.filename == '':
        flash('Файл не выбран', 'warning')
        return redirect(url_for('admin.dashboard', tab='database'))
        
    if file and file.filename.endswith('.zip'):
        try:
            # 1. Бэкап текущей базы перед восстановлением
            if os.path.exists(DB_FILE_PATH):
                backup_path = f"{DB_FILE_PATH}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(DB_FILE_PATH, backup_path)
            
            # Читаем ZIP из файла (чтобы не занимать много ОЗУ, можно читать напрямую)
            with zipfile.ZipFile(file, 'r') as zf:
                # 2. Восстановление БД
                db_filename = os.path.basename(DB_FILE_PATH)
                if db_filename in zf.namelist():
                    with open(DB_FILE_PATH, 'wb') as f:
                        f.write(zf.read(db_filename))
                else:
                    flash('В архиве не найдена база данных (coppdb.sqlite). Восстановление файлов продолжено.', 'warning')
                
                # 3. Восстановление файлов (uploads)
                uploads_dir = os.path.join('app', 'static', 'uploads')
                os.makedirs(uploads_dir, exist_ok=True)
                
                for item in zf.namelist():
                    if item.startswith('uploads/') and not item.endswith('/'):
                        # Определяем путь извлечения
                        rel_path = item[len('uploads/'):]
                        target_path = os.path.join(uploads_dir, rel_path)
                        
                        # Если файла еще нет, извлекаем
                        if not os.path.exists(target_path):
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with open(target_path, 'wb') as f:
                                f.write(zf.read(item))
                                
            flash('Сайт успешно восстановлен из полного бэкапа! Старая БД сохранена как .bak файл.', 'success')
        except Exception as e:
            flash(f'Ошибка восстановления из ZIP: {str(e)}', 'danger')
    else:
        flash('Файл должен иметь расширение .zip', 'danger')
        
    return redirect(url_for('admin.dashboard', tab='database'))

@bp.route('/db/update_cells', methods=['POST'])
@login_required
def db_update_cells():
    """
    Обработчик AJAX-запросов для inline-редактирования ячеек БД прямо из таблицы.
    """
    import re
    data = request.json
    table = data.get('table')
    pk_col = data.get('pk_col')
    changes = data.get('changes', []) # [{'pk_val': 1, 'column': 'title', 'value': 'new'}]
    
    if not all([table, pk_col, changes]):
        return {"success": False, "error": "Missing parameters"}, 400
        
    conn = get_db_connection()
    try:
        # Strict validation to prevent SQL injection in table name
        if not re.match(r'^[a-zA-Z0-9_]+$', table) or not re.match(r'^[a-zA-Z0-9_]+$', pk_col):
             return {"success": False, "error": "Invalid table or pk column name"}, 400
             
        cursor = conn.cursor()
        for change in changes:
            column = change.get('column')
            pk_val = change.get('pk_val')
            new_val = change.get('value')
            
            # Strict column name validation
            if not column or not re.match(r'^[a-zA-Z0-9_]+$', column):
                continue
                
            cursor.execute(f"UPDATE {table} SET {column} = ? WHERE {pk_col} = ?", (new_val, pk_val))
            
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}, 500
