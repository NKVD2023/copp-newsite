from flask import render_template
from app.main import bp
from app.db import get_db_connection

@bp.route('/team')
def team():
    """
    Страница "Наша команда" со списком сотрудников.
    """
    conn = get_db_connection()
    team_members = conn.execute('SELECT * FROM team_members ORDER BY display_order ASC, id DESC').fetchall()
    return render_template('team.html', team_members=team_members)
