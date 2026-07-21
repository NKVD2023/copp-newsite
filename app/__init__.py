"""
Модуль инициализации приложения Flask.
Содержит фабрику приложения, которая создает и настраивает экземпляр Flask,
регистрирует глобальные переменные для шаблонов (context processors),
кастомные фильтры Jinja и подключает Blueprint'ы (роуты).
"""
#fix
import json
import os
from flask import Flask
from flask_caching import Cache
from config import Config
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

# Глобальный объект кэша (инициализируется в create_app)
cache = Cache()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=Config):
    """
    Фабрика приложения (Application Factory).
    Паттерн, позволяющий безопасно создавать множество экземпляров приложения
    (полезно для тестов и масштабирования).
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Настройка ProxyFix для правильного определения IP-адресов за Nginx
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # ==========================================
    # КЭШИРОВАНИЕ (SimpleCache — хранится в RAM)
    # Не требует Redis/Memcached для базового использования.
    # ==========================================
    app.config.setdefault('CACHE_TYPE', 'SimpleCache')
    app.config.setdefault('CACHE_DEFAULT_TIMEOUT', 60)  # TTL по умолчанию 60 секунд
    cache.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {"success": False, "error": "Вы слишком часто отправляете запросы. Пожалуйста, подождите."}, 429

    # ==========================================
    # КЭШИРОВАНИЕ colleges.json В ПАМЯТИ ПРИЛОЖЕНИЯ
    # Файл читается один раз при первом обращении и кэшируется навсегда
    # (пока сервер не перезапущен). Это устраняет чтение файла с диска
    # при каждом открытии /atlas и /atlas/<id>.
    # ==========================================
    _colleges_cache = {}

    def get_colleges():
        """Возвращает список колледжей из кэша или загружает с диска."""
        if 'data' not in _colleges_cache:
            colleges_path = os.path.join(app.static_folder, 'data', 'colleges.json')
            try:
                with open(colleges_path, 'r', encoding='utf-8') as f:
                    _colleges_cache['data'] = json.load(f)
            except Exception:
                _colleges_cache['data'] = []
        return _colleges_cache['data']

    # Делаем get_colleges доступным через app для использования в routes
    app.get_colleges = get_colleges

    # ==========================================
    # РЕГИСТРАЦИЯ TEARDOWN: закрытие DB-соединения
    # close_db вызывается Flask автоматически после каждого HTTP-запроса.
    # Это позволяет переиспользовать одно соединение в пределах запроса (через flask.g).
    # ==========================================
    from app.db import close_db
    app.teardown_appcontext(close_db)

    # ==========================================
    # ГЛОБАЛЬНЫЙ КОНТЕКСТ ДЛЯ ШАБЛОНОВ
    # inject_dynamic_pages() выполняется для каждого HTTP-запроса,
    # поэтому кэшируем на 60 секунд чтобы не делать 4 DB-запроса на каждый хит.
    # ==========================================
    @app.context_processor
    def inject_dynamic_pages():
        """
        Глобальный процессор контекста Jinja2.
        Возвращает переменные, автоматически доступные ВО ВСЕХ HTML-шаблонах.
        Кэшируется на 60 секунд через Flask-Caching чтобы избежать
        повторных DB-запросов при каждом HTTP-запросе.
        """
        from datetime import datetime

        cached = cache.get('_global_context')
        if cached is not None:
            # Обновляем now_str (время не кэшируем) и возвращаем из кэша
            cached['now_str'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return cached

        from app.db import get_db_connection
        conn = get_db_connection()
        try:
            # Получаем все кастомные страницы, которые должны отображаться в меню
            dynamic_pages = conn.execute(
                'SELECT slug, title, menu_group FROM pages WHERE is_in_navbar = 1'
            ).fetchall()

            single_pages = []    # Страницы без выпадающего списка
            grouped_pages = {}   # Страницы, сгруппированные для выпадающего меню

            for page in dynamic_pages:
                mg = page['menu_group']
                page_dict = dict(page)
                if mg:
                    if mg not in grouped_pages:
                        grouped_pages[mg] = []
                    grouped_pages[mg].append(page_dict)
                else:
                    single_pages.append(page_dict)

            # Данные для футера и шапки
            dynamic_projects = [dict(row) for row in conn.execute(
                "SELECT slug, title, project_color FROM projects WHERE status = 'published' ORDER BY id DESC"
            ).fetchall()]
            
            cs_row = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
            contact_settings = dict(cs_row) if cs_row else None
            
            social_networks = [dict(row) for row in conn.execute(
                'SELECT * FROM social_networks WHERE is_active = 1 ORDER BY display_order ASC'
            ).fetchall()]

            # Получаем все активные пункты меню
            raw_menu_items = conn.execute(
                'SELECT * FROM menu_items WHERE is_active = 1 ORDER BY position ASC, id ASC'
            ).fetchall()
            
            menu_hierarchy = []
            menu_by_id = {}
            for row in raw_menu_items:
                item = dict(row)
                item['children'] = []
                menu_by_id[item['id']] = item
            
            for row in raw_menu_items:
                item = menu_by_id[row['id']]
                if item['parent_id']:
                    if item['parent_id'] in menu_by_id:
                        menu_by_id[item['parent_id']]['children'].append(item)
                else:
                    menu_hierarchy.append(item)

        except Exception:
            # В случае ошибки БД — возвращаем пустые структуры, сайт не упадёт
            single_pages = []
            grouped_pages = {}
            dynamic_projects = []
            contact_settings = None
            social_networks=[]
            menu_hierarchy=[]

        result = dict(
            single_pages=single_pages,
            grouped_pages=grouped_pages,
            dynamic_projects=dynamic_projects,
            contact_settings=contact_settings,
            social_networks=social_networks,
            menu_hierarchy=menu_hierarchy,
        )

        # Кэшируем на 60 секунд (не включая now_str — он всегда свежий)
        cache.set('_global_context', result, timeout=60)

        result['now_str'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return result

    # ==========================================
    # КАСТОМНЫЙ ФИЛЬТР JINJA: from_json
    # ==========================================
    @app.template_filter('from_json')
    def from_json_filter(value):
        """
        Кастомный фильтр Jinja: парсит JSON строку в Python объект (список/словарь).
        Используется в шаблонах так: {{ my_string | from_json }}
        """
        if not value:
            return []
        try:
            return json.loads(value)
        except Exception:
            return []

    @app.template_filter('datetime_format')
    def datetime_format_filter(value):
        """
        Форматирует строку даты из SQLite (YYYY-MM-DD HH:MM:SS) в человекочитаемый вид.
        Например: "21 июля 2026, 05:32"
        """
        if not value:
            return ""
        try:
            from datetime import datetime
            dt = datetime.strptime(value[:19], '%Y-%m-%d %H:%M:%S')
            months = ['', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            return f"{dt.day} {months[dt.month]} {dt.year}, {dt.strftime('%H:%M')}"
        except Exception:
            return value

    # ==========================================
    # РЕГИСТРАЦИЯ КОМПОНЕНТОВ (Blueprints)
    # ==========================================

    # Публичная часть сайта (Главная, Новости, Проекты)
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Панель администратора (со своим префиксом URL /admin)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Инициализация недостающих таблиц в БД
    from app.db import init_db
    init_db(app)

    return app