from app.repositories.base import BaseRepository
from app.db import get_db_connection

class NewsRepository(BaseRepository):
    table_name = 'news'

    @classmethod
    def create(cls, data):
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO news (title, teaser, content, main_image, extra_images, status, is_event, event_date, event_location, publish_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data['title'], data['teaser'], data['content'], data['main_image_path'], data['extra_images_str'], data['status'], data['is_event'], data['event_date'], data['event_location'], data['publish_date']))
            conn.commit()
            return conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    @classmethod
    def update(cls, news_id, data):
        with get_db_connection() as conn:
            if data.get('publish_date'):
                conn.execute('''
                    UPDATE news 
                    SET title = ?, teaser = ?, content = ?, main_image = ?, extra_images = ?, status = ?, is_event = ?, event_date = ?, event_location = ?, publish_date = ?
                    WHERE id = ?
                ''', (data['title'], data['teaser'], data['content'], data['main_image_path'], data['extra_images_str'], data['status'], data['is_event'], data['event_date'], data['event_location'], data['publish_date'], news_id))
            else:
                conn.execute('''
                    UPDATE news 
                    SET title = ?, teaser = ?, content = ?, main_image = ?, extra_images = ?, status = ?, is_event = ?, event_date = ?, event_location = ?
                    WHERE id = ?
                ''', (data['title'], data['teaser'], data['content'], data['main_image_path'], data['extra_images_str'], data['status'], data['is_event'], data['event_date'], data['event_location'], news_id))
            conn.commit()

    @classmethod
    def update_status(cls, news_id, status):
        with get_db_connection() as conn:
            conn.execute('UPDATE news SET status = ? WHERE id = ?', (status, news_id))
            conn.commit()

    @classmethod
    def export(cls, month=None, status=None):
        query = 'SELECT * FROM news WHERE 1=1'
        params = []
        if month:
            query += ' AND publish_date LIKE ?'
            params.append(f'{month}%')
        if status:
            query += ' AND status = ?'
            params.append(status)
        query += ' ORDER BY publish_date DESC'
        with get_db_connection() as conn:
            return conn.execute(query, params).fetchall()

class PagesRepository(BaseRepository):
    table_name = 'pages'
    
    @classmethod
    def get_menu_groups(cls):
        with get_db_connection() as conn:
            return conn.execute('SELECT DISTINCT menu_group FROM pages WHERE menu_group IS NOT NULL AND menu_group != ""').fetchall()

class DocumentsRepository(BaseRepository):
    table_name = 'documents'

class ProjectsRepository(BaseRepository):
    table_name = 'projects'

class StatisticsRepository(BaseRepository):
    table_name = 'statistics'

class SocialNetworksRepository(BaseRepository):
    table_name = 'social_networks'

class ContactSettingsRepository(BaseRepository):
    table_name = 'contact_settings'

    @classmethod
    def get_settings(cls):
        with get_db_connection() as conn:
            return conn.execute('SELECT * FROM contact_settings WHERE id = 1').fetchone()

class ContactRequestsRepository(BaseRepository):
    table_name = 'contact_requests'

class MenuItemsRepository(BaseRepository):
    table_name = 'menu_items'

class PageFormsRepository(BaseRepository):
    table_name = 'page_forms'

class FormSubmissionsRepository(BaseRepository):
    table_name = 'form_submissions'
    
    @classmethod
    def get_all_with_form_titles(cls):
        with get_db_connection() as conn:
            return conn.execute('''
                SELECT s.*, f.title as form_title, f.year
                FROM form_submissions s
                JOIN page_forms f ON s.form_id = f.id
                ORDER BY s.id DESC
            ''').fetchall()

class DashboardUploadsRepository(BaseRepository):
    table_name = 'dashboard_uploads'
    
    @classmethod
    def get_all(cls):
        return super().get_all(order_by='upload_date DESC')

class ProfessionsRepository(BaseRepository):
    table_name = 'professions'

class TeamMembersRepository(BaseRepository):
    table_name = 'team_members'
    
    @classmethod
    def get_all(cls):
        return super().get_all(order_by='display_order ASC, id DESC')

class CareerTestResultsRepository(BaseRepository):
    table_name = 'career_test_results'
    
    @classmethod
    def get_recent_stats(cls, limit=50):
        with get_db_connection() as conn:
            return conn.execute('''
                SELECT c.id, c.created_at, p.name as profession_name 
                FROM career_test_results c
                LEFT JOIN professions p ON c.top_profession_id = p.id
                ORDER BY c.created_at DESC
                LIMIT ?
            ''', (limit,)).fetchall()

class AdminUsersRepository(BaseRepository):
    table_name = 'admin_users'
    
    @classmethod
    def get_all(cls):
        return super().get_all(order_by='created_at DESC')

class SystemRepository:
    @staticmethod
    def get_all_tables():
        with get_db_connection() as conn:
            return conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
