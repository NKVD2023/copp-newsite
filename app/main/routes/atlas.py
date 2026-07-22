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

    # Нормализация для поиска (игнорируем тип кавычек, двойные пробелы, регистр)
    import re
    def norm_s(s):
        if not s: return ""
        return re.sub(r'["\'«»]', '', s).replace('  ', ' ').strip().lower()

    colleges_with_links = []
    inst_val = prof['institutions']
    if inst_val:
        val = inst_val.strip()
        if val.startswith('[') and val.endswith(']'):
            try:
                selected_colleges = json.loads(val)
                for name in selected_colleges:
                    url = next((c['url'] for c in colleges if norm_s(c['name']) == norm_s(name)), None)
                    colleges_with_links.append({'name': name, 'url': url})
            except Exception:
                pass
        elif ',' in val:
            for part in val.split(','):
                part = part.strip()
                if not part: continue
                url = next((c['url'] for c in colleges if norm_s(c['name']) == norm_s(part)), None)
                colleges_with_links.append({'name': part, 'url': url})
        else:
            # Сплошной текст без запятых. Ищем известные колледжи как подстроки.
            norm_val = norm_s(val)
            for c in colleges:
                if norm_s(c['name']) in norm_val:
                    colleges_with_links.append({'name': c['name'], 'url': c['url']})
            if not colleges_with_links:
                colleges_with_links.append({'name': val, 'url': None})

    return render_template('profession_detail.html', prof=prof, colleges=colleges_with_links)
