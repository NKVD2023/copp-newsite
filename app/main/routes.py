from flask import render_template, request, jsonify, redirect, url_for, abort, current_app
from app.main import bp
from app.db import get_db_connection
from app.utils.date_utils import format_date_ru, format_event_date_ru, enrich_news_list
from datetime import datetime


@bp.route('/')
def index():
    """
    Главная страница сайта.
    Загружает: 6 последних новостей (с учетом таймера публикации),
    блок статистики, контакты и передает это в шаблон index.html.
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    latest_news_rows = conn.execute(
        "SELECT * FROM news WHERE status = 'published' AND publish_date <= ? ORDER BY publish_date DESC LIMIT 6",
        (current_time,)
    ).fetchall()
    stats = conn.execute('SELECT * FROM statistics ORDER BY display_order ASC').fetchall()
    contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()

    latest_news = enrich_news_list(latest_news_rows)

    return render_template('index.html', latest_news=latest_news, stats=stats, contact_settings=contact_settings)


@bp.route('/contact/submit', methods=['POST'])
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


@bp.route('/news')
def news():
    """
    Страница списка всех новостей.
    Выводит только опубликованные новости, дата которых уже наступила.
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    news_rows = conn.execute(
        "SELECT * FROM news WHERE status = 'published' AND publish_date <= ? ORDER BY publish_date DESC",
        (current_time,)
    ).fetchall()

    news_list = enrich_news_list(news_rows)
    return render_template('news.html', news_list=news_list)


@bp.route('/news/<int:news_id>')
def news_detail(news_id):
    """
    Страница детального просмотра одной новости.
    Форматирует дату для красивого отображения и парсит дополнительные картинки.
    Если новость не найдена, выдает ошибку 404.
    """
    conn = get_db_connection()
    news_item = conn.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()

    if news_item is None:
        abort(404)

    extra_imgs = []
    if news_item['extra_images']:
        extra_imgs = [img.strip() for img in news_item['extra_images'].split(',') if img.strip()]

    human_publish_date = format_date_ru(news_item['publish_date'])
    human_event_date = format_event_date_ru(news_item['event_date'])

    return render_template(
        'news_detail.html',
        news=news_item,
        extra_imgs=extra_imgs,
        human_publish_date=human_publish_date,
        human_event_date=human_event_date
    )


@bp.route('/events')
def events():
    """
    Страница со списком предстоящих мероприятий.
    Фильтрует новости с флагом is_event=1 и сортирует их по дате проведения.
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    events_rows = conn.execute(
        "SELECT * FROM news WHERE status = 'published' AND is_event = 1 AND publish_date <= ? ORDER BY event_date ASC, id DESC",
        (current_time,)
    ).fetchall()

    events_list = [
        {
            'id': row['id'],
            'title': row['title'],
            'teaser': row['teaser'],
            'content': row['content'],
            'main_image': row['main_image'],
            'event_date': row['event_date'],
            'event_location': row['event_location'],
        }
        for row in events_rows
    ]

    return render_template('events.html', events_list=events_list)


@bp.route('/atlas')
def atlas():
    """
    Страница атласа профессий.
    Colleges загружаются из app-level кэша (один раз за жизнь процесса).
    """
    import json
    conn = get_db_connection()
    professions = conn.execute(
        "SELECT * FROM professions WHERE status = 'published' ORDER BY code ASC, name ASC"
    ).fetchall()

    colleges = current_app.get_colleges()
    return render_template('atlas.html', professions=professions, colleges=colleges)


@bp.route('/atlas/<int:prof_id>')
def profession_detail(prof_id):
    """
    Детальная страница профессии из Атласа.
    Colleges загружаются из app-level кэша.
    """
    import json
    from flask import session

    conn = get_db_connection()
    prof = conn.execute('SELECT * FROM professions WHERE id = ?', (prof_id,)).fetchone()

    if not prof or (prof['status'] != 'published' and not session.get('is_admin')):
        abort(404)

    colleges = current_app.get_colleges()

    # Разбираем привязанные учебные заведения
    selected_colleges = []
    inst_val = prof['institutions']
    if inst_val:
        val = inst_val.strip()
        if val.startswith('[') and val.endswith(']'):
            try:
                selected_colleges = json.loads(val)
            except Exception:
                selected_colleges = [val]
        else:
            selected_colleges = [c.strip() for c in val.split(',') if c.strip()]

    # Сопоставляем с ссылками на сайты
    colleges_with_links = [
        {'name': name, 'url': next((c['url'] for c in colleges if c['name'] == name), None)}
        for name in selected_colleges
    ]

    return render_template('profession_detail.html', prof=prof, colleges=colleges_with_links)


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


@bp.route('/project/<slug>')
def project(slug):
    """
    Страница детального просмотра проекта.
    Парсит JSON-массив с дополнительными картинками.
    """
    import json
    conn = get_db_connection()
    project_item = conn.execute(
        "SELECT * FROM projects WHERE slug = ? AND status = 'published'",
        (slug,)
    ).fetchone()

    if project_item is None:
        abort(404)

    try:
        extra_imgs = json.loads(project_item['extra_images']) if project_item['extra_images'] else []
    except Exception:
        extra_imgs = []

    return render_template('project.html', project=project_item, extra_imgs=extra_imgs)


@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@bp.route('/api/dashboard')
def api_dashboard():
    """
    API-эндпоинт для получения данных дашборда вакансий с серверной фильтрацией и пагинацией.
    Медиана зарплат вычисляется в SQL (ранее загружала все строки в Python).
    """
    import json as _json

    category = request.args.get('category', 'Полный список')
    search = request.args.get('search', '').strip().lower()
    munis = request.args.get('munis', '')
    emps = request.args.get('emps', '')

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    try:
        limit = int(request.args.get('limit', 24))
    except ValueError:
        limit = 24

    try:
        munis_list = _json.loads(munis) if munis else []
    except Exception:
        munis_list = []

    try:
        emps_list = _json.loads(emps) if emps else []
    except Exception:
        emps_list = []

    conn = get_db_connection()

    query_base = "FROM dashboard_vacancies WHERE category = ?"
    params = [category]

    if munis_list:
        placeholders = ','.join(['?'] * len(munis_list))
        query_base += f" AND municipality IN ({placeholders})"
        params.extend(munis_list)

    if emps_list:
        placeholders = ','.join(['?'] * len(emps_list))
        query_base += f" AND employer IN ({placeholders})"
        params.extend(emps_list)

    if search:
        query_base += " AND (LOWER(vacancy_name) LIKE ? OR LOWER(requirements) LIKE ? OR LOWER(employer) LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])

    # Подсчитываем общую статистику для текущих фильтров
    stats_row = conn.execute(
        f"SELECT COUNT(*) as count, SUM(jobs_count) as total_jobs {query_base}",
        params
    ).fetchone()

    total_count = stats_row['count']
    total_jobs = stats_row['total_jobs'] or 0

    # Медиана зарплат вычисляется прямо в SQL через оконные функции SQLite 3.25+.
    # Ранее: все зарплаты грузились в Python-список → sorted() → RAM.
    # Теперь: 1 SQL-строка вместо N строк в памяти.
    median_salary = 0
    salary_params = params + params  # дублируем params для подзапроса
    median_row = conn.execute(f"""
        SELECT AVG(salary) as median_salary
        FROM (
            SELECT salary,
                   ROW_NUMBER() OVER (ORDER BY salary) as rn,
                   COUNT(*) OVER ()                    as cnt
            {query_base} AND salary IS NOT NULL AND salary > 0
        )
        WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    """, params).fetchone()
    if median_row and median_row['median_salary']:
        median_salary = int(median_row['median_salary'])

    # Получаем пагинированные данные
    offset = (page - 1) * limit
    rows = conn.execute(
        f"SELECT * {query_base} ORDER BY id ASC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()

    data = [dict(r) for r in rows]

    return jsonify({
        "success": True,
        "data": data,
        "total_count": total_count,
        "total_jobs": total_jobs,
        "median_salary": median_salary,
    })


@bp.route('/api/dashboard_filters')
def api_dashboard_filters():
    """
    Эндпоинт для получения уникальных списков муниципалитетов и работодателей по выбранной категории.
    """
    category = request.args.get('category', 'Полный список')
    conn = get_db_connection()

    munis_rows = conn.execute(
        "SELECT DISTINCT municipality FROM dashboard_vacancies WHERE category = ? AND municipality IS NOT NULL AND municipality != 'None' AND municipality != ''",
        (category,)
    ).fetchall()
    emps_rows = conn.execute(
        "SELECT DISTINCT employer FROM dashboard_vacancies WHERE category = ? AND employer IS NOT NULL AND employer != 'None' AND employer != ''",
        (category,)
    ).fetchall()

    munis = sorted([r['municipality'] for r in munis_rows])
    emps = sorted([r['employer'] for r in emps_rows])

    return jsonify({"success": True, "munis": munis, "emps": emps})


@bp.route('/team')
def team():
    """
    Страница "Наша команда" со списком сотрудников.
    """
    conn = get_db_connection()
    team_members = conn.execute('SELECT * FROM team_members ORDER BY display_order ASC, id DESC').fetchall()
    return render_template('team.html', team_members=team_members)