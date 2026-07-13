from flask import request, redirect, url_for, flash
from app.admin import bp
from app.db import get_db_connection
from app.admin.auth import login_required
import pandas as pd
import os
from werkzeug.utils import secure_filename

def clean_val(v):
    if pd.isna(v):
        return None
    return str(v)

@bp.route('/upload_prof_stats', methods=['POST'])
@login_required
def upload_prof_stats():
    """
    Загрузка и парсинг Excel-файла со статистикой по профессиям/вакансиям.
    Данные из файла используются для Дашборда (dashboard_vacancies).
    При загрузке старые записи указанной категории удаляются и заменяются новыми.
    """
    category = request.form.get('category')
    file = request.files.get('excel_file')
    
    if not file or not file.filename.endswith('.xlsx'):
        flash("Пожалуйста, загрузите файл формата .xlsx", "error")
        return redirect(url_for('admin.dashboard', tab='prof_stats'))
        
    filename = secure_filename(file.filename)
    upload_folder = os.path.join('app', 'static', 'uploads', 'stats')
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    
    try:
        df = pd.read_excel(filepath)
        
        with get_db_connection() as conn:
            # Delete old records for this category
            conn.execute("DELETE FROM dashboard_vacancies WHERE category = ?", (category,))
            
            # Record upload history
            conn.execute('''
                INSERT INTO dashboard_uploads (category, filename) 
                VALUES (?, ?)
            ''', (category, filename))
            
            # Parse and insert new records
            for index, row in df.iterrows():
                vac_name = clean_val(row.get("Вакансия"))
                employer = clean_val(row.get("Краткое название работодателя", row.get("Полное название работодателя")))
                muni = clean_val(row.get("Муниципалитет"))
                salary = row.get("Минимальная зарплата", 0)
                if pd.isna(salary): salary = 0
                jobs = row.get("Количество рабочих мест", 1)
                if pd.isna(jobs): jobs = 1
                hard = clean_val(row.get("Требуемые хардскиллы"))
                soft = clean_val(row.get("Требуемые софтскиллы"))
                lat = row.get("Широта адрес вакансии", None)
                lng = row.get("Долгота адрес вакансии", None)
                if pd.isna(lat): lat = None
                if pd.isna(lng): lng = None
                
                # New fields
                schedule = clean_val(row.get("График работы"))
                employment_type = clean_val(row.get("Тип занятости"))
                education = clean_val(row.get("Образование"))
                requirements = clean_val(row.get("Требования"))
                bonuses = clean_val(row.get("Бонусы"))
                contact_person = clean_val(row.get("Контактное лицо"))
                contact_phone = clean_val(row.get("Контактный телефон"))
                
                contact_email = clean_val(row.get("Email контактного лица"))
                if not contact_email or contact_email == 'Не указано':
                    contact_email = clean_val(row.get("Email работодателя"))
                    
                source_link = clean_val(row.get("Ссылка на вакансию"))
                
                conn.execute('''
                    INSERT INTO dashboard_vacancies 
                    (category, vacancy_name, employer, municipality, salary, jobs_count, hard_skills, soft_skills, lat, lng,
                     schedule, employment_type, education, requirements, bonuses, contact_person, contact_phone, contact_email, source_link)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (category, vac_name, employer, muni, int(salary), int(jobs), hard, soft, lat, lng,
                      schedule, employment_type, education, requirements, bonuses, contact_person, contact_phone, contact_email, source_link))
            
            conn.commit()
            
        flash(f"Файл {filename} для категории '{category}' успешно загружен и обработан!", "success")
    except Exception as e:
        flash(f"Ошибка при обработке файла: {e}", "error")
        
    return redirect(url_for('admin.dashboard', tab='prof_stats'))
