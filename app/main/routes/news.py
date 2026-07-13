from flask import render_template, abort
from app.main import bp
from app.db import get_db_connection
from app.utils.date_utils import format_date_ru, format_event_date_ru, enrich_news_list
from datetime import datetime

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
