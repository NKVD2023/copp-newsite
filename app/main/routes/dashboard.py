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
