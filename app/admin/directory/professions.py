import os
import json
import pandas as pd
import io
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
from app.admin import bp
from app.admin.core.auth import login_required, module_required, ALL_MODULES, ROLE_LABELS
from app.db import get_db_connection
from app.utils.image_utils import save_image_as_webp
from app.utils.media_utils import scan_uploads_dir

UPLOAD_PROFESSIONS_FOLDER = os.path.join('app', 'static', 'uploads', 'professions')

CATEGORIES_RU = {
    'it': 'IT и цифровая связь',
    'construction': 'Строительство',
    'transport': 'Транспорт и автосервис',
    'service': 'Сфера услуг и туризм',
    'industry': 'Промышленность и производство',
    'agriculture': 'Сельское хозяйство',
    'medicine': 'Здравоохранение',
    'education': 'Образование, культура и спорт',
    'other': 'Другие сферы'
}

CATEGORIES_MAP = {
    'it': ['it', 'ит', 'информационные', 'связь', 'цифр', 'компьютер'],
    'construction': ['строительство', 'строй'],
    'transport': ['транспорт', 'авто', 'логистика', 'дорожн'],
    'service': ['сервис', 'туризм', 'услуг', 'гостеприимств', 'повар', 'торговл'],
    'industry': ['промышленность', 'производство', 'машиностроение', 'металл', 'химическ', 'электр'],
    'agriculture': ['сельское', 'агро', 'рыбное', 'лесное', 'фермер'],
    'medicine': ['медицина', 'здравоохранение', 'сестринское', 'врач', 'фармац'],
    'education': ['образование', 'педагогика', 'культура', 'искусство', 'спорт', 'дизайн'],
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def clean_val(v):
    if pd.isna(v):
        return None
    return str(v).strip()

def guess_category_from_code(code):
    if not code:
        return 'other'
    code = code.strip()
    if len(code) >= 2 and code[:2].isdigit():
        prefix = code[:2]
        if prefix == '08':
            return 'construction'
        elif prefix in {'09', '10', '11'}:
            return 'it'
        elif prefix in {'13', '15', '18', '22', '24', '29', '19', '20', '21'}:
            return 'industry'
        elif prefix == '23':
            return 'transport'
        elif prefix == '35':
            return 'agriculture'
        elif prefix in {'31', '32', '33', '34'}:
            return 'medicine'
        elif prefix == '43':
            return 'service'
        elif prefix in {'44', '54'}:
            return 'education'
    return 'other'

def parse_category_name(val, code):
    if not val:
        return guess_category_from_code(code)
    val_lower = val.lower().strip()
    for key, keywords in CATEGORIES_MAP.items():
        if key == val_lower:
            return key
        for kw in keywords:
            if kw in val_lower:
                return key
    return 'other'

@bp.route('/add_profession', methods=['POST'])
@login_required
def add_profession():
    """
    Создание новой профессии вручную.
    """
    code = request.form.get('code', '')
    name = request.form['name']
    description = request.form.get('description', '')
    activities = request.form.get('activities', '')
    qualities = request.form.get('qualities', '')
    medical = request.form.get('medical', '')
    status = request.form.get('status', 'published')
    
    # Считываем выбранную категорию (если "auto", то автоопределение по коду)
    category = request.form.get('category', 'auto')
    if not category or category == 'auto':
        category = guess_category_from_code(code)
        
    # Получаем выбранные колледжи из чекбоксов и сохраняем как JSON-строку
    selected_colleges = request.form.getlist('selected_colleges')
    institutions = json.dumps(selected_colleges, ensure_ascii=False)
    
    os.makedirs(UPLOAD_PROFESSIONS_FOLDER, exist_ok=True)
    
    image_path = request.form.get('existing_main_image') or None
    if 'main_image' in request.files:
        file = request.files['main_image']
        if file and allowed_file(file.filename):
            filename = save_image_as_webp(file, UPLOAD_PROFESSIONS_FOLDER, add_uuid=True)
            if filename:
                image_path = f"uploads/professions/{filename}"
                
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO professions (code, name, description, activities, qualities, medical, institutions, image_path, status, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (code, name, description, activities, qualities, medical, institutions, image_path, status, category))
        conn.commit()
        flash('Профессия успешно добавлена!', 'success')
    except Exception as e:
        flash(f'Ошибка при добавлении профессии: {e}', 'danger')
        
    return redirect(url_for('admin.dashboard', tab='prof_atlas'))

@bp.route('/edit_profession/<int:prof_id>', methods=['GET', 'POST'])
@login_required
def edit_profession(prof_id):
    """
    Редактирование профессии.
    """
    conn = get_db_connection()
    prof = conn.execute('SELECT * FROM professions WHERE id = ?', (prof_id,)).fetchone()
    
    if not prof:
        flash('Профессия не найдена.', 'danger')
        return redirect(url_for('admin.dashboard', tab='prof_atlas'))
        
    if request.method == 'POST':
        code = request.form.get('code', '')
        name = request.form['name']
        description = request.form.get('description', '')
        activities = request.form.get('activities', '')
        qualities = request.form.get('qualities', '')
        medical = request.form.get('medical', '')
        
        # Считываем выбранную категорию
        category = request.form.get('category', 'auto')
        if not category or category == 'auto':
            category = guess_category_from_code(code)
            
        # Получаем выбранные колледжи из чекбоксов и сохраняем как JSON-строку
        selected_colleges = request.form.getlist('selected_colleges')
        institutions = json.dumps(selected_colleges, ensure_ascii=False)
        
        # Сохраняем текущий статус
        status = prof['status'] or 'published'
        
        image_path = prof['image_path']
        existing_main = request.form.get('existing_main_image')
        if 'main_image' in request.files and request.files['main_image'].filename != '':
            file = request.files['main_image']
            if file and allowed_file(file.filename):
                filename = save_image_as_webp(file, UPLOAD_PROFESSIONS_FOLDER, add_uuid=True)
                if filename:
                    image_path = f"uploads/professions/{filename}"
        elif existing_main:
            image_path = existing_main
                    
        try:
            conn.execute('''
                UPDATE professions 
                SET code = ?, name = ?, description = ?, activities = ?, qualities = ?, medical = ?, institutions = ?, image_path = ?, status = ?, category = ?
                WHERE id = ?
            ''', (code, name, description, activities, qualities, medical, institutions, image_path, status, category, prof_id))
            conn.commit()
            flash('Профессия успешно обновлена!', 'success')
        except Exception as e:
            flash(f'Ошибка обновления: {e}', 'danger')
            
        return redirect(url_for('admin.dashboard', tab='prof_atlas'))
        
    # GET запрос
    selected_colleges_list = []
    if prof['institutions']:
        val = prof['institutions'].strip()
        if val.startswith('[') and val.endswith(']'):
            try:
                selected_colleges_list = json.loads(val)
            except:
                selected_colleges_list = [val]
        else:
            selected_colleges_list = [c.strip() for c in val.split(',') if c.strip()]
            
    import json as py_json
    colleges_list = []
    colleges_path = os.path.join('app', 'static', 'data', 'colleges.json')
    try:
        with open(colleges_path, 'r', encoding='utf-8') as f:
            colleges_list = py_json.load(f)
    except Exception as e:
        print(f"Error loading colleges: {e}")
        
    # Сканирование медиа-файлов — через утилиту, а не дублированный os.walk
    all_media_files = scan_uploads_dir()
    
    news_list = conn.execute('SELECT * FROM news ORDER BY id DESC').fetchall()
    pages_list = conn.execute('SELECT * FROM pages ORDER BY id DESC').fetchall()
    documents_list = conn.execute('SELECT * FROM documents ORDER BY id DESC').fetchall()
    projects_list = conn.execute('SELECT * FROM projects ORDER BY id DESC').fetchall()
    stats_list = conn.execute('SELECT * FROM statistics ORDER BY display_order ASC').fetchall()
    socials_list = conn.execute('SELECT * FROM social_networks ORDER BY display_order ASC').fetchall()
    contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
    menu_groups_list = conn.execute('SELECT DISTINCT menu_group FROM pages WHERE menu_group IS NOT NULL AND menu_group != ""').fetchall()
    tables_list = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    professions_list = conn.execute('SELECT * FROM professions ORDER BY id DESC').fetchall()
    
    try:
        prof_uploads = conn.execute('SELECT * FROM dashboard_uploads ORDER BY upload_date DESC').fetchall()
    except:
        prof_uploads = []
        
    return render_template('admin_dashboard.html', 
                           active_tab='prof_atlas',
                           edit_prof_item=prof,
                           selected_colleges_list=selected_colleges_list,
                           colleges_list=colleges_list,
                           news_list=news_list,
                           pages_list=pages_list,
                           documents_list=documents_list,
                           projects_list=projects_list,
                           stats_list=stats_list,
                           socials_list=socials_list,
                           contact_settings=contact_settings,
                           menu_groups_list=menu_groups_list,
                           tables_list=tables_list,
                           all_media_files=all_media_files,
                           prof_uploads=prof_uploads,
                           professions_list=professions_list,
                           categories_dict=CATEGORIES_RU,
                           allowed_modules=session.get('allowed_modules', []),
                           all_modules=ALL_MODULES,
                           role_labels=ROLE_LABELS,
                           current_username=session.get('username', 'Суперадмин'),
                           current_role=session.get('user_role', 'superadmin'),
                           is_superadmin=bool(session.get('is_admin')),
                           now_str=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@bp.route('/toggle_profession_status/<int:prof_id>', methods=['POST'])
@login_required
def toggle_profession_status(prof_id):
    """
    Переключение статуса публикации (Опубликовано / Черновик).
    """
    current_status = request.form.get('current_status', 'published')
    new_status = 'draft' if current_status == 'published' else 'published'
    
    conn = get_db_connection()
    try:
        conn.execute('UPDATE professions SET status = ? WHERE id = ?', (new_status, prof_id))
        conn.commit()
        flash('Статус публикации изменен!', 'success')
    except Exception as e:
        flash(f'Ошибка при изменении статуса: {e}', 'danger')
        
    return redirect(url_for('admin.dashboard', tab='prof_atlas'))

@bp.route('/delete_profession/<int:prof_id>', methods=['POST'])
@login_required
def delete_profession(prof_id):
    """
    Удаление профессии.
    """
    conn = get_db_connection()
    prof = conn.execute('SELECT * FROM professions WHERE id = ?', (prof_id,)).fetchone()
    
    if prof:
        image_path = prof['image_path']
        if image_path:
            try:
                os.remove(os.path.join('app', 'static', image_path))
            except:
                pass
        conn.execute('DELETE FROM professions WHERE id = ?', (prof_id,))
        conn.commit()
        flash('Профессия успешно удалена!', 'success')
    else:
        flash('Профессия не найдена.', 'danger')
        
    return redirect(url_for('admin.dashboard', tab='prof_atlas'))

@bp.route('/delete_all_professions', methods=['POST'])
@login_required
def delete_all_professions():
    """
    Удаление всех профессий из атласа (очистка).
    """
    conn = get_db_connection()
    try:
        # Получаем все профессии, чтобы удалить их картинки
        profs = conn.execute('SELECT image_path FROM professions WHERE image_path IS NOT NULL').fetchall()
        for prof in profs:
            if prof['image_path']:
                try:
                    os.remove(os.path.join('app', 'static', prof['image_path']))
                except Exception:
                    pass
        
        conn.execute('DELETE FROM professions')
        conn.commit()
        flash('Все профессии были успешно удалены!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении профессий: {e}', 'danger')
        
    return redirect(url_for('admin.dashboard', tab='prof_atlas'))


@bp.route('/import_professions', methods=['POST'])
@login_required
def import_professions():
    """
    Импорт профессий из Excel-файла.
    """
    file = request.files.get('excel_file')
    if not file or not file.filename.endswith('.xlsx'):
        flash("Пожалуйста, выберите файл формата .xlsx", "error")
        return redirect(url_for('admin.dashboard', tab='prof_atlas'))
        
    # Загружаем колледжи для сопоставления названий
    colleges_list = []
    colleges_path = os.path.join('app', 'static', 'data', 'colleges.json')
    try:
        with open(colleges_path, 'r', encoding='utf-8') as f:
            colleges_list = json.load(f)
    except Exception as e:
        print(f"Error loading colleges for import matching: {e}")
        
    try:
        df = pd.read_excel(file)
        
        # Получаем названия столбцов для гибкости регистра
        cols = {col.strip().upper(): col for col in df.columns}
        
        # Функция поиска нужной колонки независимо от регистра
        def get_col_val(row, *possible_names):
            for name in possible_names:
                u_name = name.upper()
                if u_name in cols:
                    return clean_val(row.get(cols[u_name]))
            return None
            
        with get_db_connection() as conn:
            conn.execute("DELETE FROM professions")
            
            for index, row in df.iterrows():
                code = get_col_val(row, 'КОД', 'код', 'code')
                name = get_col_val(row, 'НАЗВАНИЕ', 'название', 'name')
                
                if not name:
                    continue
                    
                description = get_col_val(row, 'КРАТКИЙ ОЧЕРК', 'ОПИСАНИЕ', 'описание', 'description')
                activities = get_col_val(row, 'ВИДЫ ДЕЯТЕЛЬНОСТИ', 'виды деятельности', 'activities')
                qualities = get_col_val(row, 'ПРОФЕССИОНАЛЬНОЕ ВАЖНЫЕ КАЧЕСТВА', 'Профессионально важные качества', 'качества', 'qualities')
                medical = get_col_val(row, 'МЕДИЦИНСКИЕ ПОКАЗАНИЯ', 'медицинские показания', 'medical')
                
                # Чтение и разбор учебных заведений
                institutions_text = get_col_val(row, 'УЧЕБНЫЕ ЗАВЕДЕНИЯ СПО', 'учебные заведения', 'institutions')
                matched_colleges = []
                if institutions_text:
                    institutions_text_lower = institutions_text.lower()
                    for college in colleges_list:
                        if college['name'].lower() in institutions_text_lower:
                            matched_colleges.append(college['name'])
                    
                    if not matched_colleges:
                        parts = [p.strip() for p in institutions_text.split(',') if p.strip()]
                        if parts:
                            matched_colleges = parts
                
                institutions_json = json.dumps(matched_colleges, ensure_ascii=False)
                
                image_val = get_col_val(row, "Подготовить фотографии 'Наименование.png", "Подготовить фотографии 'Наименование", "фото", "изображение", "image")
                
                image_path = None
                if image_val:
                    if '/' not in image_val and '\\' not in image_val:
                        image_path = f"uploads/professions/{image_val}"
                    else:
                        image_path = image_val
                        
                # Читаем сферу/категорию
                category_text = get_col_val(row, 'КАТЕГОРИЯ', 'СФЕРА', 'ОТРАСЛЬ', 'category')
                category = parse_category_name(category_text, code)
                
                status = 'published'
                
                conn.execute('''
                    INSERT INTO professions (code, name, description, activities, qualities, medical, institutions, image_path, status, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (code, name, description, activities, qualities, medical, institutions_json, image_path, status, category))
                
            conn.commit()
            
        flash(f"Данные из файла '{file.filename}' успешно импортированы!", "success")
    except Exception as e:
        flash(f"Ошибка при обработке файла: {e}", "danger")
        
    return redirect(url_for('admin.dashboard', tab='prof_atlas'))

@bp.route('/export_professions', methods=['GET'])
@login_required
def export_professions():
    """
    Экспорт всех профессий в Excel-файл.
    """
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM professions ORDER BY id ASC').fetchall()
    
    data = []
    for r in rows:
        img_name = ""
        if r['image_path']:
            img_name = os.path.basename(r['image_path'])
            
        inst_val = r['institutions']
        inst_text = ""
        if inst_val:
            try:
                inst_list = json.loads(inst_val)
                if isinstance(inst_list, list):
                    inst_text = ", ".join(inst_list)
                else:
                    inst_text = str(inst_val)
            except:
                inst_text = str(inst_val)
                
        status = r['status'] or 'published'
        cat_val = r['category'] or 'other'
        cat_name = CATEGORIES_RU.get(cat_val, CATEGORIES_RU['other'])
            
        data.append({
            'КОД': r['code'] or "",
            'НАЗВАНИЕ': r['name'],
            'ОПИСАНИЕ': r['description'] or "",
            'ВИДЫ ДЕЯТЕЛЬНОСТИ': r['activities'] or "",
            'ПРОФЕССИОНАЛЬНОЕ ВАЖНЫЕ КАЧЕСТВА': r['qualities'] or "",
            'МЕДИЦИНСКИЕ ПОКАЗАНИЯ': r['medical'] or "",
            'УЧЕБНЫЕ ЗАВЕДЕНИЯ СПО': inst_text,
            "Подготовить фотографии 'Наименование.png": img_name,
            'КАТЕГОРИЯ': cat_name,
            'СТАТУС': status
        })
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Атлас профессий')
        
    output.seek(0)
    
    from datetime import datetime
    filename = f"atlas_professions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )
