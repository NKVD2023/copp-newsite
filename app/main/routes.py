from flask import render_template, request, jsonify
from app.main import bp
from app.db import get_db_connection

@bp.route('/')
def index():
    conn = get_db_connection()
    latest_news_rows = conn.execute("SELECT * FROM news WHERE status = 'published' ORDER BY id DESC LIMIT 5").fetchall()
    stats = conn.execute('SELECT * FROM statistics ORDER BY display_order ASC').fetchall()
    contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
    conn.close()
    
    from datetime import datetime
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    
    latest_news = []
    for row in latest_news_rows:
        n = dict(row)
        try:
            dt = datetime.strptime(n['publish_date'][:10], '%Y-%m-%d')
            n['human_date'] = f"{dt.day} {months[dt.month - 1]} {dt.year} г."
        except:
            n['human_date'] = n['publish_date'][:10] if n['publish_date'] else ""
        latest_news.append(n)

    return render_template('index.html', latest_news=latest_news, stats=stats, contact_settings=contact_settings)

@bp.route('/contact/submit', methods=['POST'])
def contact_submit():
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
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': 'Ошибка сервера.'}), 500
    
    conn.close()
    return jsonify({'success': True, 'message': 'Ваше сообщение успешно отправлено!'})

@bp.route('/news')
def news():
    conn = get_db_connection()
    news_rows = conn.execute("SELECT * FROM news WHERE status = 'published' ORDER BY id DESC").fetchall()
    conn.close()
    
    from datetime import datetime
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    
    news_list = []
    for row in news_rows:
        n = dict(row)
        try:
            dt = datetime.strptime(n['publish_date'][:10], '%Y-%m-%d')
            n['human_date'] = f"{dt.day} {months[dt.month - 1]} {dt.year} г."
        except:
            n['human_date'] = n['publish_date'][:10] if n['publish_date'] else ""
        news_list.append(n)
        
    return render_template('news.html', news_list=news_list)

@bp.route('/news/<int:news_id>')
def news_detail(news_id):
    conn = get_db_connection()
    news_item = conn.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()
    conn.close()
    
    if news_item is None:
        abort(404)
        
    import json
    from datetime import datetime
    
    extra_imgs = []
    if news_item['extra_images']:
        extra_imgs = [img.strip() for img in news_item['extra_images'].split(',') if img.strip()]

    # Format dates
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    
    human_publish_date = ""
    if news_item['publish_date']:
        try:
            # Parse '2026-06-01 12:00:00' or '2026-06-01'
            dt_str = news_item['publish_date'][:10]
            dt = datetime.strptime(dt_str, '%Y-%m-%d')
            human_publish_date = f"{dt.day} {months[dt.month - 1]} {dt.year} г."
        except:
            human_publish_date = news_item['publish_date']
            
    human_event_date = ""
    if news_item['event_date']:
        try:
            if 'T' in news_item['event_date']:
                dt = datetime.strptime(news_item['event_date'], '%Y-%m-%dT%H:%M')
                human_event_date = f"{dt.day} {months[dt.month - 1]} {dt.year} г., {dt.hour:02d}:{dt.minute:02d}"
            else:
                dt = datetime.strptime(news_item['event_date'][:10], '%Y-%m-%d')
                human_event_date = f"{dt.day} {months[dt.month - 1]} {dt.year} г."
        except:
            human_event_date = news_item['event_date']
        
    return render_template('news_detail.html', news=news_item, extra_imgs=extra_imgs, human_publish_date=human_publish_date, human_event_date=human_event_date)

@bp.route('/events')
def events():
    conn = get_db_connection()
    # Получаем опубликованные мероприятия, сортируем по дате создания (или дате проведения, но date - это строка)
    events_rows = conn.execute("SELECT * FROM news WHERE status = 'published' AND is_event = 1 ORDER BY event_date ASC, id DESC").fetchall()
    conn.close()
    
    events_list = []
    for row in events_rows:
        events_list.append({
            'id': row['id'],
            'title': row['title'],
            'teaser': row['teaser'],
            'content': row['content'],
            'main_image': row['main_image'],
            'event_date': row['event_date'],
            'event_location': row['event_location']
        })
        
    return render_template('events.html', events_list=events_list)

@bp.route('/atlas')
def atlas():
    return render_template('atlas.html')

@bp.route('/contacts')
def contacts():
    return render_template('contacts.html')

from flask import abort

@bp.route('/page/<slug>')
def dynamic_page(slug):
    conn = get_db_connection()
    page = conn.execute('SELECT * FROM pages WHERE slug = ?', (slug,)).fetchone()
    conn.close()
    
    if page is None:
        abort(404)
        
    return render_template('page.html', page=page)

@bp.route('/project/<slug>')
def project(slug):
    conn = get_db_connection()
    project = conn.execute("SELECT * FROM projects WHERE slug = ? AND status = 'published'", (slug,)).fetchone()
    conn.close()
    
    if project is None:
        abort(404)
        
    import json
    try:
        extra_imgs = json.loads(project['extra_images']) if project['extra_images'] else []
    except:
        extra_imgs = []
        
    return render_template('project.html', project=project, extra_imgs=extra_imgs)

@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@bp.route('/api/dashboard')
def api_dashboard():
    category = request.args.get('category', 'Полный список')
    
    conn = get_db_connection()
    # Fetch all vacancies for this category
    rows = conn.execute("SELECT * FROM dashboard_vacancies WHERE category = ?", (category,)).fetchall()
    conn.close()
    
    data = []
    for r in rows:
        data.append(dict(r))
        
    return jsonify({"success": True, "data": data})