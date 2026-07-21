from flask import session, request
from app.db import get_db_connection

def log_admin_action(action, module, entity_id=None, details=None):
    """
    Записывает действие администратора в базу данных.
    
    :param action: Строка. Тип действия (например, 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT').
    :param module: Строка. Имя модуля, в котором произошло действие (например, 'news', 'users', 'auth').
    :param entity_id: Целое число (необязательно). Идентификатор объекта, над которым произведено действие.
    :param details: Строка (необязательно). Текстовое описание действия или JSON.
    """
    # Получаем данные о текущем пользователе
    username = session.get('username', 'Система')
    
    # Роль пользователя
    if session.get('is_admin'):
        role = 'superadmin'
    else:
        role = session.get('user_role', 'unknown')

    # Получаем IP-адрес пользователя
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO admin_logs (username, role, action, module, entity_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, role, action, module, entity_id, details, ip_address))
        conn.commit()
    except Exception as e:
        print(f"Ошибка при записи лога: {e}")
