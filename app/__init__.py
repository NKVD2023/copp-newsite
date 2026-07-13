"""
Модуль инициализации приложения Flask.
Содержит фабрику приложения, которая создает и настраивает экземпляр Flask,
регистрирует глобальные переменные для шаблонов (context processors),
кастомные фильтры Jinja и подключает Blueprint'ы (роуты).
"""
import json
import os
from flask import Flask
from flask_caching import Cache
from config import Config

# Глобальный объект кэша (инициализируется в create_app)
cache = Cache()


def create_app(config_class=Config):
    """
    Фабрика приложения (Application Factory).
    Паттерн, позволяющий безопасно создавать множество экземпляров приложения
    (полезно для тестов и масштабирования).
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ==========================================
    # КЭШИРОВАНИЕ (SimpleCache — хранится в RAM)
    # Не требует Redis/Memcached для базового использования.
    # ==========================================
    app.config.setdefault('CACHE_TYPE', 'SimpleCache')
    app.config.setdefault('CACHE_DEFAULT_TIMEOUT', 60)  # TTL по умолчанию 60 секунд
    cache.init_app(app)

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
        except Exception:
            # В случае ошибки БД — возвращаем пустые структуры, сайт не упадёт
            single_pages = []
            grouped_pages = {}
            dynamic_projects = []
            contact_settings = None
            social_networks = []

        result = dict(
            single_pages=single_pages,
            grouped_pages=grouped_pages,
            dynamic_projects=dynamic_projects,
            contact_settings=contact_settings,
            social_networks=social_networks,
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

    # ==========================================
    # РЕГИСТРАЦИЯ КОМПОНЕНТОВ (Blueprints)
    # ==========================================

    # Публичная часть сайта (Главная, Новости, Проекты)
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Панель администратора (со своим префиксом URL /admin)
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app