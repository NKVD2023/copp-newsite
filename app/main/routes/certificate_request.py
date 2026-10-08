import json
import re
from datetime import datetime
from flask import render_template, request, flash, redirect, url_for
from app.main import bp
from app.db import get_db_connection
from app import limiter

from app.constants import GROUPS


MAX_PERIODS = 10  # Максимальное количество периодов в одной заявке


def _err(msg):
    flash(msg, "danger")
    return render_template('main/certificate_request.html', groups=GROUPS)


@bp.route('/request/income-certificate-h7K9pQ', methods=['GET', 'POST'])
@limiter.limit("30 per hour", methods=["POST"])
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
        
        consent = request.form.get('consent_personal_data')
        if not consent:
            return _err("Необходимо дать согласие на обработку персональных данных для заказа справки.")

        # --- Валидация обязательных полей ---
        if not all([fio, group_number, birth_date, study_period_start, study_period_end, phone]):
            return _err("Пожалуйста, заполните все обязательные поля.")

        # Ограничения длины
        if len(fio) > 150:
            return _err("ФИО слишком длинное (максимум 150 символов).")
        if len(phone) > 20:
            return _err("Номер телефона слишком длинный.")

        # Группа должна быть из разрешённого списка
        if group_number not in GROUPS:
            return _err("Выбрана недопустимая группа. Пожалуйста, выберите из списка.")

        # Дата рождения: формат YYYY-MM-DD (Flatpickr отправляет именно так)
        try:
            datetime.strptime(birth_date, '%Y-%m-%d')
        except ValueError:
            return _err("Некорректный формат даты рождения.")

        # Период обучения: только 2 цифры
        if not re.fullmatch(r'\d{2}', study_period_start) or not re.fullmatch(r'\d{2}', study_period_end):
            return _err("Период обучения должен содержать только две цифры года (например, 23).")

        # --- Валидация периодов ---
        periods = []
        for s, e in zip(income_starts[:MAX_PERIODS], income_ends[:MAX_PERIODS]):
            s, e = s.strip(), e.strip()
            if not s or not e:
                continue
            try:
                datetime.strptime(s, '%Y-%m-%d')
                datetime.strptime(e, '%Y-%m-%d')
            except ValueError:
                return _err("Некорректный формат даты в одном из запрашиваемых периодов.")
            periods.append({"start": s, "end": e})

        if not periods:
            return _err("Добавьте хотя бы один запрашиваемый период для справки.")

        if len(periods) > MAX_PERIODS:
            return _err(f"Максимально допустимое количество периодов — {MAX_PERIODS}.")

        periods_json = json.dumps(periods, ensure_ascii=False)
        
        # Для обратной совместимости со старой схемой БД передаем первый период
        first_start = periods[0]['start']
        first_end = periods[0]['end']
            
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO income_cert_requests 
            (fio, group_number, birth_date, study_period_start, study_period_end, phone, income_period_start, income_period_end, income_periods, consent_personal_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (fio, group_number, birth_date, study_period_start, study_period_end, phone, first_start, first_end, periods_json))
        conn.commit()
        
        return render_template('main/certificate_success.html')

    return render_template('main/certificate_request.html', groups=GROUPS)
