from flask import render_template, abort
from app.main import bp
from app.db import get_db_connection

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
