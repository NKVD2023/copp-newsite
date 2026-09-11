import json
from flask import render_template, request, flash, redirect, url_for
from app.main import bp
from app.db import get_db_connection

# Актуальный список групп
GROUPS = [
    "1.01 ГРД", "1.05 ГРД (к)", "1.07 ДЗ (к)", "1.08 ДЗ (к)", "1.31 БПЛА", "1.100 А",
    "1.02 Ф", "1.03 ОБ", "1.10 ИК (к)", "1.09 ПКД (к)", "1.21 ПКД", "1.22 ПКД",
    "1.23 ПКД", "1.25 СТ", "1.11 ТГг (к)", "1.26 ТГг", "1.28 ТГп", "1.29 ТГЭ",
    "1.30 ТГт", "1.24 ПКД 11 кл", "2.02 ПКД", "2.17 ПКД (к)", "2.01 ПКД", "2.03 ПКД",
    "2.05 СТ", "1.27 ТГг 11 кл", "2.06 ТГг", "2.08 ТГп", "2.09 ТГп", "2.10 ТГт",
    "2.19 ТГг (к)", "2.20 ТГг (к)", "2.11 ОБ (к)", "1.06 ГРД (к) 11 кл", "2.12 ГРД (к)",
    "2.98 ГРД", "2.14 ДЗ (к)", "2.15 ДЗ (к)", "2.16 ДЗ (к)", "2.18 ИК (к)", "2.97 А",
    "2.99 Ф", "2.13 ГРД (к) 11 кл", "3.76 ГРД", "3.77 ГРД (к)", "3.78 ГРД (к)",
    "3.81 ДЗ (к)", "2.04 ПКД 11 кл", "3.86 ПКД (к)", "3.84 ПКД", "3.85 ПКД", "3.88 СТ",
    "3.90 ИК (к)", "2.07 ТГг 11 кл", "3.91 ТГг", "3.94 ТГп", "3.95 ТГт", "3.96 ТГЭ (к)",
    "4.56 ГРД", "4.57 ГРД (к)", "4.58 ГРД (к)", "4.59 ГРД (к)"
]

@bp.route('/request/income-certificate-h7K9pQ', methods=['GET', 'POST'])
def request_income_certificate():
    if request.method == 'POST':
        fio = request.form.get('fio')
        group_number = request.form.get('group_number')
        birth_date = request.form.get('birth_date')
        study_period_start = request.form.get('study_period_start')
        study_period_end = request.form.get('study_period_end')
        phone = request.form.get('phone')
        
        income_starts = request.form.getlist('income_period_start[]')
        income_ends = request.form.getlist('income_period_end[]')
        
        periods = []
        for s, e in zip(income_starts, income_ends):
            if s and e:
                periods.append({"start": s, "end": e})
        
        if not all([fio, group_number, birth_date, study_period_start, study_period_end, phone]) or not periods:
            flash("Пожалуйста, заполните все обязательные поля и добавьте хотя бы один период.", "danger")
            return render_template('main/certificate_request.html', groups=GROUPS)
            
        periods_json = json.dumps(periods)
        
        # Для обратной совместимости со старой схемой БД передаем первый период
        first_start = periods[0]['start']
        first_end = periods[0]['end']
            
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO income_cert_requests 
            (fio, group_number, birth_date, study_period_start, study_period_end, phone, income_period_start, income_period_end, income_periods)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fio, group_number, birth_date, study_period_start, study_period_end, phone, first_start, first_end, periods_json))
        conn.commit()
        
        return render_template('main/certificate_success.html')

    return render_template('main/certificate_request.html', groups=GROUPS)
