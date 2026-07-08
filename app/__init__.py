"""
Модуль инициализации приложения Flask.
Содержит фабрику приложения, которая создает и настраивает экземпляр Flask,
регистрирует глобальные переменные для шаблонов (context processors), 
кастомные фильтры Jinja и подключает Blueprint'ы (роуты).
"""
from flask import Flask
from config import Config

def create_app(config_class=Config):
    """
    Фабрика приложения (Application Factory).
    Паттерн, позволяющий безопасно создавать множество экземпляров приложения 
    (полезно для тестов и масштабирования).
    """
    app = Flask(__name__)
    app.config.from_object(config_class) # Применяем настройки из config.py

    @app.context_processor
    def inject_dynamic_pages():
        """
        Глобальный процессор контекста Jinja2.
        Функция возвращает словарь переменных, которые будут автоматически 
        доступны ВО ВСЕХ HTML-шаблонах сайта (без необходимости передавать их из каждого роута).
        Используется для меню, футера и глобальных настроек.
        """
        from app.db import get_db_connection
        conn = get_db_connection()
        try:
            # Получаем все кастомные страницы, которые должны отображаться в меню
            dynamic_pages = conn.execute('SELECT slug, title, menu_group FROM pages WHERE is_in_navbar = 1').fetchall()
            
            single_pages = [] # Страницы без выпадающего списка
            grouped_pages = {} # Страницы, сгруппированные для выпадающего списка
            
            # Сортируем страницы по группам (для выпадающего меню)
            for page in dynamic_pages:
                mg = page['menu_group']
                if mg:
                    if mg not in grouped_pages:
                        grouped_pages[mg] = []
                    grouped_pages[mg].append(page)
                else:
                    single_pages.append(page)
                    
            # Получаем опубликованные проекты и настройки контактов/соцсетей для футера и шапки
            dynamic_projects = conn.execute("SELECT slug, title FROM projects WHERE status = 'published' ORDER BY id DESC").fetchall()
            contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
            social_networks = conn.execute('SELECT * FROM social_networks WHERE is_active = 1 ORDER BY display_order ASC').fetchall()
        except Exception:
            # В случае ошибки базы данных возвращаем пустые структуры, чтобы сайт не упал полностью
            single_pages = []
            grouped_pages = {}
            dynamic_projects = []
            contact_settings = None
            social_networks = []
        finally:
            conn.close()
            
        # Эти переменные теперь можно использовать в любом месте, например {{ contact_settings.phone }}
        return dict(single_pages=single_pages, grouped_pages=grouped_pages, dynamic_projects=dynamic_projects, contact_settings=contact_settings, social_networks=social_networks)

    import json
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