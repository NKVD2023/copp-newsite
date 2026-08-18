from app.db import get_db_connection

class BaseRepository:
    table_name = None

    @classmethod
    def get_all(cls, order_by='id DESC'):
        with get_db_connection() as conn:
            return conn.execute(f'SELECT * FROM {cls.table_name} ORDER BY {order_by}').fetchall()

    @classmethod
    def get_by_id(cls, entity_id):
        with get_db_connection() as conn:
            return conn.execute(f'SELECT * FROM {cls.table_name} WHERE id = ?', (entity_id,)).fetchone()

    @classmethod
    def delete(cls, entity_id):
        with get_db_connection() as conn:
            conn.execute(f'DELETE FROM {cls.table_name} WHERE id = ?', (entity_id,))
            conn.commit()

    @classmethod
    def count(cls):
        with get_db_connection() as conn:
            return conn.execute(f'SELECT COUNT(*) FROM {cls.table_name}').fetchone()[0]
