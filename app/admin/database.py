import os
import csv
import io
import shutil
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, send_file, Response
from app.admin import bp
from app.db import get_db_connection
from werkzeug.utils import secure_filename

DB_FILE_PATH = 'coppdb.sqlite'

@bp.route('/db/table/<table_name>')
def db_view_table(table_name):
    """
    Отображение содержимого таблицы БД в админке.
    Для предотвращения падения браузера лимит установлен на 500 записей.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
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
    finally:
        conn.close()

@bp.route('/db/export/csv/<table_name>')
def db_export_csv(table_name):
    """
    Экспорт выбранной таблицы БД в формате CSV.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
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
    finally:
        conn.close()

@bp.route('/db/export/sql')
def db_export_sqlite():
    """
    Создание и скачивание резервной копии всей базы данных (файла SQLite).
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    try:
        return send_file(os.path.abspath(DB_FILE_PATH), as_attachment=True, download_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite")
    except Exception as e:
        flash(f"Ошибка скачивания бэкапа: {str(e)}", "danger")
        return redirect(url_for('admin.dashboard', tab='database'))

@bp.route('/db/execute_sql', methods=['POST'])
def db_execute_sql():
    """
    Выполнение произвольного SQL-запроса из админки.
    Требует ввода пароля администратора для подтверждения полномочий.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    password = request.form.get('admin_password', '')
    if password != 'admin123':
        flash("Неверный пароль администратора", "danger")
        return redirect(url_for('admin.dashboard', tab='database'))
        
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
    finally:
        conn.close()
        
    return redirect(url_for('admin.dashboard', tab='database'))

@bp.route('/db/import/sqlite', methods=['POST'])
def db_import_sqlite():
    """
    Импорт (восстановление) базы данных из загруженного .sqlite файла.
    Перед заменой создает бэкап текущей БД с суффиксом .bak.
    """
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
        
    password = request.form.get('admin_password', '')
    if password != 'admin123':
        flash("Неверный пароль администратора", "danger")
        return redirect(url_for('admin.dashboard', tab='database'))
        
    if 'sqlite_file' not in request.files:
        flash('Файл не выбран', 'warning')
        return redirect(url_for('admin.dashboard', tab='database'))
        
    file = request.files['sqlite_file']
    if file.filename == '':
        flash('Файл не выбран', 'warning')
        return redirect(url_for('admin.dashboard', tab='database'))
        
    if file and file.filename.endswith('.sqlite'):
        try:
            # Backup current DB
            backup_path = f"{DB_FILE_PATH}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            shutil.copy2(DB_FILE_PATH, backup_path)
            
            # Replace with new DB
            file.save(DB_FILE_PATH)
            flash('База данных успешно восстановлена. Старая база сохранена как .bak файл.', 'success')
        except Exception as e:
            flash(f'Ошибка восстановления: {str(e)}', 'danger')
    else:
        flash('Файл должен иметь расширение .sqlite', 'danger')
        
    return redirect(url_for('admin.dashboard', tab='database'))

@bp.route('/db/update_cells', methods=['POST'])
def db_update_cells():
    """
    Обработчик AJAX-запросов для inline-редактирования ячеек БД прямо из таблицы.
    """
    if not session.get('is_admin'):
        return {"success": False, "error": "Unauthorized"}, 403
        
    data = request.json
    password = data.get('admin_password', '')
    if password != 'admin123':
        return {"success": False, "error": "Неверный пароль администратора"}, 403
        
    table = data.get('table')
    pk_col = data.get('pk_col')
    changes = data.get('changes', []) # [{'pk_val': 1, 'column': 'title', 'value': 'new'}]
    
    if not all([table, pk_col, changes]):
        return {"success": False, "error": "Missing parameters"}, 400
        
    conn = get_db_connection()
    try:
        # Basic validation to prevent SQL injection in table name
        if not table.isalnum() and '_' not in table:
             return {"success": False, "error": "Invalid table name"}, 400
             
        cursor = conn.cursor()
        for change in changes:
            column = change.get('column')
            pk_val = change.get('pk_val')
            new_val = change.get('value')
            
            # Simple column name validation (alphanumeric + underscore)
            if not column.isalnum() and '_' not in column:
                continue
                
            cursor.execute(f"UPDATE {table} SET {column} = ? WHERE {pk_col} = ?", (new_val, pk_val))
            
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}, 500
    finally:
        conn.close()
