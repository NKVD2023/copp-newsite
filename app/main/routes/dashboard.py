from flask import render_template, request, jsonify
from app.main import bp
from app.db import get_db_connection

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

    category = request.args.get('category', 'Все отрасли')
    search = request.args.get('search', '').strip().lower()
    munis = request.args.get('munis', '')
    emps = request.args.get('emps', '')
    schedule = request.args.get('schedule', '')
    exp = request.args.get('exp', '')

    try:
        exp = int(exp) if exp else None
    except ValueError:
        exp = None

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

    query_base = "FROM dashboard_vacancies WHERE 1=1"
    params = []
    
    if category and category != 'Все отрасли':
        query_base += " AND category = ?"
        params.append(category)

    if munis_list:
        placeholders = ','.join(['?'] * len(munis_list))
        query_base += f" AND municipality IN ({placeholders})"
        params.extend(munis_list)

    if emps_list:
        placeholders = ','.join(['?'] * len(emps_list))
        query_base += f" AND employer IN ({placeholders})"
        params.extend(emps_list)

    if schedule and schedule != 'Любой график':
        query_base += " AND schedule = ?"
        params.append(schedule)

    if exp is not None:
        if exp == 0:
            query_base += " AND (experience_length = 0 OR experience_length IS NULL)"
        else:
            query_base += " AND experience_length >= ?"
            params.append(exp)

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

    import os
    import datetime
    last_updated = "Неизвестно"
    status_file = os.path.join('app', 'static', 'data', 'sync_status.json')
    if os.path.exists(status_file):
        try:
            mtime = os.path.getmtime(status_file)
            dt = datetime.datetime.fromtimestamp(mtime)
            last_updated = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass

    return jsonify({
        "success": True,
        "data": data,
        "total_count": total_count,
        "total_jobs": total_jobs,
        "median_salary": median_salary,
        "last_updated": last_updated
    })


@bp.route('/api/dashboard_filters')
def api_dashboard_filters():
    """
    Эндпоинт для получения уникальных списков муниципалитетов и работодателей по выбранной категории.
    """
    category = request.args.get('category', 'Все отрасли')
    conn = get_db_connection()
    
    # We ignore category when fetching categories
    categories_rows = conn.execute(
        "SELECT DISTINCT category FROM dashboard_vacancies WHERE category IS NOT NULL AND category != 'None' AND category != ''"
    ).fetchall()

    # Filtering logic for municipalities and employers should also respect the category filter
    muni_query = "SELECT DISTINCT municipality FROM dashboard_vacancies WHERE municipality IS NOT NULL AND municipality != 'None' AND municipality != ''"
    emp_query = "SELECT DISTINCT employer FROM dashboard_vacancies WHERE employer IS NOT NULL AND employer != 'None' AND employer != ''"
    schedule_query = "SELECT DISTINCT schedule FROM dashboard_vacancies WHERE schedule IS NOT NULL AND schedule != 'None' AND schedule != ''"
    
    cat_params = []
    if category and category != 'Все отрасли':
        muni_query += " AND category = ?"
        emp_query += " AND category = ?"
        schedule_query += " AND category = ?"
        cat_params.append(category)
        
    munis_rows = conn.execute(muni_query, cat_params).fetchall()
    emps_rows = conn.execute(emp_query, cat_params).fetchall()
    schedules_rows = conn.execute(schedule_query, cat_params).fetchall()

    categories = sorted([r['category'] for r in categories_rows])
    munis = sorted([r['municipality'] for r in munis_rows])
    emps = sorted([r['employer'] for r in emps_rows])
    schedules = sorted([r['schedule'] for r in schedules_rows])

    return jsonify({
        "success": True, 
        "categories": categories, 
        "munis": munis, 
        "emps": emps, 
        "schedules": schedules
    })
