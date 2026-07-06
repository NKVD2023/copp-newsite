from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    @app.context_processor
    def inject_dynamic_pages():
        from app.db import get_db_connection
        conn = get_db_connection()
        try:
            dynamic_pages = conn.execute('SELECT slug, title, menu_group FROM pages WHERE is_in_navbar = 1').fetchall()
            
            single_pages = []
            grouped_pages = {}
            for page in dynamic_pages:
                mg = page['menu_group']
                if mg:
                    if mg not in grouped_pages:
                        grouped_pages[mg] = []
                    grouped_pages[mg].append(page)
                else:
                    single_pages.append(page)
                    
            dynamic_projects = conn.execute("SELECT slug, title FROM projects WHERE status = 'published' ORDER BY id DESC").fetchall()
            contact_settings = conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()
            social_networks = conn.execute('SELECT * FROM social_networks WHERE is_active = 1 ORDER BY display_order ASC').fetchall()
        except Exception:
            single_pages = []
            grouped_pages = {}
            dynamic_projects = []
            contact_settings = None
            social_networks = []
        finally:
            conn.close()
        return dict(single_pages=single_pages, grouped_pages=grouped_pages, dynamic_projects=dynamic_projects, contact_settings=contact_settings, social_networks=social_networks)

    import json
    @app.template_filter('from_json')
    def from_json_filter(value):
        if not value:
            return []
        try:
            return json.loads(value)
        except Exception:
            return []

    # Регистрация компонентов (Blueprints)
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app