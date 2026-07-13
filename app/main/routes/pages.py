from flask import render_template, request, jsonify, redirect, url_for, abort
from app.main import bp
from app import limiter
from app.db import get_db_connection

@bp.route('/contact/submit', methods=['POST'])
@limiter.limit("5 per day")
@limiter.limit("1 per minute")
def contact_submit():
    """
    Обработчик AJAX-запроса (POST) с формы обратной связи.
    Принимает JSON данные, проверяет обязательные поля и сохраняет заявку в БД.
    """
    data = request.json
    first_name = data.get('firstName')
    middle_name = data.get('middleName', '')
    last_name = data.get('lastName')
    email = data.get('email')
    message = data.get('message')

    if not first_name or not last_name or not email or not message:
        return jsonify({'success': False, 'message': 'Пожалуйста, заполните все обязательные поля.'}), 400

    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO contact_requests (first_name, middle_name, last_name, email, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (first_name, middle_name, last_name, email, message))
        conn.commit()
    except Exception:
        return jsonify({'success': False, 'message': 'Ошибка сервера.'}), 500

    return jsonify({'success': True, 'message': 'Ваше сообщение успешно отправлено!'})


@bp.route('/contacts')
def contacts():
    return redirect(url_for('main.dynamic_page', slug='contacts'))


@bp.route('/page/<slug>')
def dynamic_page(slug):
    """
    Обработчик динамических страниц (созданных через админку).
    Ищет страницу по уникальному идентификатору (slug).
    """
    conn = get_db_connection()
    page = conn.execute('SELECT * FROM pages WHERE slug = ?', (slug,)).fetchone()

    if page is None:
        abort(404)

    page_form = conn.execute(
        "SELECT * FROM page_forms WHERE page_id = ? AND status = 'active'",
        (page['id'],)
    ).fetchone()

    if slug == 'contacts':
        contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
        return render_template('contacts.html', page=page, contact_settings=contact_settings, page_form=page_form)

    return render_template('page.html', page=page, page_form=page_form)


@bp.route('/submit_dynamic_form', methods=['POST'])
@limiter.limit("5 per day")
@limiter.limit("1 per minute")
def submit_dynamic_form():
    """
    Обработчик отправки динамических форм со страниц.
    Принимает ID формы и данные JSON, сохраняет в form_submissions.
    """
    import json as _json
    try:
        data = request.json
        form_id = data.get('form_id')
        submission_data = data.get('submission_data')

        if not form_id or not submission_data:
            return jsonify({'success': False, 'message': 'Некорректные данные.'}), 400

        json_data = _json.dumps(submission_data, ensure_ascii=False)

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO form_submissions (form_id, submission_data) VALUES (?, ?)',
            (form_id, json_data)
        )
        conn.commit()

        return jsonify({'success': True, 'message': 'Ваша заявка успешно отправлена!'})
    except Exception as e:
        print("Dynamic form submit error:", e)
        return jsonify({'success': False, 'message': 'Произошла ошибка при отправке.'}), 500
