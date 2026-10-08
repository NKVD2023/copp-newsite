import os
import re
from datetime import datetime
from flask import render_template, request, flash, redirect, url_for
from app.main import bp
from app.db import get_db_connection
from app import limiter

from app.constants import GROUPS, STUDY_PROGRAMS, PROGRAMS_BY_ID


def _err(msg):
    flash(msg, "danger")
    return render_template('main/study_certificate_request.html', programs=STUDY_PROGRAMS, groups=GROUPS)


@bp.route('/request/study-certificate-v9X4mK', methods=['GET', 'POST'])
@limiter.limit("30 per hour", methods=["POST"])
def request_study_certificate():
    if request.method == 'POST':
        fio = (request.form.get('fio') or '').strip()
        group_number = (request.form.get('group_number') or '').strip()
        birth_date = (request.form.get('birth_date') or '').strip()
        program_id = (request.form.get('program_id') or '').strip()
        copies_raw = request.form.get('copies_count', '1')
        consent = request.form.get('consent_personal_data')

        if not consent:
            return _err("Необходимо дать согласие на обработку персональных данных для заказа справки.")

        if not all([fio, group_number, birth_date, program_id]):
            return _err("Пожалуйста, заполните все обязательные поля формы.")

        if len(fio) > 150:
            return _err("ФИО слишком длинное (максимум 150 символов).")

        if group_number not in GROUPS:
            return _err("Выбрана недопустимая группа. Пожалуйста, выберите из списка.")

        if program_id not in PROGRAMS_BY_ID:
            return _err("Выбрано недопустимое направление подготовки. Выберите из списка.")

        # Проверка количества экземпляров (от 1 до 5)
        try:
            copies_count = int(copies_raw)
            if copies_count < 1 or copies_count > 5:
                copies_count = 1
        except (ValueError, TypeError):
            copies_count = 1

        # Проверка даты рождения
        try:
            # Flatpickr может отправлять YYYY-MM-DD или DD.MM.YYYY
            if '-' in birth_date:
                parsed_dt = datetime.strptime(birth_date, '%Y-%m-%d')
                birth_date_clean = parsed_dt.strftime('%d.%m.%Y')
            elif '.' in birth_date:
                parsed_dt = datetime.strptime(birth_date, '%d.%m.%Y')
                birth_date_clean = birth_date
            else:
                return _err("Некорректный формат даты рождения.")
        except ValueError:
            return _err("Некорректная дата рождения.")

        selected_prog = PROGRAMS_BY_ID[program_id]
        specialty_name = selected_prog['name']
        study_duration = selected_prog['duration']

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO study_cert_requests 
            (fio, group_number, birth_date, specialty, study_duration, copies_count, consent_personal_data, status)
            VALUES (?, ?, ?, ?, ?, ?, 1, 'new')
        ''', (fio, group_number, birth_date_clean, specialty_name, study_duration, copies_count))
        conn.commit()

        return render_template('main/study_certificate_success.html')

    return render_template('main/study_certificate_request.html', programs=STUDY_PROGRAMS, groups=GROUPS)
