from flask import render_template
from app.main import bp
from app.db import get_db_connection
from app.utils.date_utils import enrich_news_list
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
