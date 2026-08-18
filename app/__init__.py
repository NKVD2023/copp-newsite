"""
Модуль инициализации приложения Flask.
Содержит фабрику приложения, которая создает и настраивает экземпляр Flask,
регистрирует глобальные переменные для шаблонов (context processors),
кастомные фильтры Jinja и подключает Blueprint'ы (роуты).
"""
import json
import os
from flask import Flask
from config import Config
from werkzeug.middleware.proxy_fix import ProxyFix

# Импортируем глобальные объекты из extensions
from app.extensions import cache, csrf, limiter

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
    # ИНИЦИАЛИЗАЦИЯ РАСШИРЕНИЙ
    # ==========================================
    app.config.setdefault('CACHE_TYPE', 'SimpleCache')
    app.config.setdefault('CACHE_DEFAULT_TIMEOUT', 60)
    
    cache.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {"success": False, "error": "Вы слишком часто отправляете запросы. Пожалуйста, подождите."}, 429

    # ==========================================
    # КЭШИРОВАНИЕ colleges.json
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

    app.get_colleges = get_colleges

    # ==========================================
    # РЕГИСТРАЦИЯ ТЕАРДАУНОВ, КОНТЕКСТОВ И ФИЛЬТРОВ
    # ==========================================
    from app.db import close_db
    app.teardown_appcontext(close_db)

    from app.context_processors import inject_dynamic_pages
    from app.template_filters import from_json_filter, datetime_format_filter

    app.context_processor(inject_dynamic_pages)
    app.template_filter('from_json')(from_json_filter)
    app.template_filter('datetime_format')(datetime_format_filter)

    # ==========================================
    # РЕГИСТРАЦИЯ КОМПОНЕНТОВ (Blueprints)
    # ==========================================
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Инициализация недостающих таблиц в БД
    from app.db import init_db
    init_db(app)

    return app