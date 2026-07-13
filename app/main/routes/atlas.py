from flask import render_template, abort, current_app, session
from app.main import bp
from app.db import get_db_connection

@bp.route('/atlas')
def atlas():
    """
    Страница атласа профессий.
    Colleges загружаются из app-level кэша (один раз за жизнь процесса).
    """
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
