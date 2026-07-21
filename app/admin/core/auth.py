"""
Модуль аутентификации администратора.
Поддерживает два режима входа:
  1. Суперадмин — только пароль из .env (session['is_admin'] = True)
  2. Субадмин   — логин + пароль из таблицы admin_users
"""
import json
from functools import wraps
from flask import render_template, request, redirect, url_for, session, flash, current_app
from app.admin import bp
from app.admin.core.logger import log_admin_action


# ---------------------------------------------------------------------------
# Список всех доступных модулей (порядок = порядок вкладок в шапке)
# ---------------------------------------------------------------------------
ALL_MODULES = [
    ('news',       'Новости',               'fa-newspaper'),
    ('prof_stats', 'Статистика дашборда',   'fa-chart-bar'),
    ('prof_atlas', 'Атлас профессий',       'fa-graduation-cap'),
    ('projects',   'Проекты',              'fa-folder-open'),
    ('pages',      'Страницы',             'fa-file-lines'),
    ('documents',  'Файлы',                'fa-paperclip'),
    ('statistics', 'Показатели',           'fa-square-poll-vertical'),
    ('contacts',   'Обратная связь',       'fa-envelope'),
    ('forms_data', 'Данные форм',          'fa-table-list'),
    ('socials',    'Соцсети',              'fa-share-nodes'),
    ('menu',       'Меню сайта',           'fa-bars'),
    ('team',       'Команда',              'fa-users'),
    ('database',   'База данных',          'fa-database'),
]

ROLE_LABELS = {
    'editor':    'Редактор',
    'analyst':   'Аналитик',
    'admin':     'Администратор',
}


# ---------------------------------------------------------------------------
# Хелпер: список разрешённых модулей для текущего пользователя
# ---------------------------------------------------------------------------
def get_current_user_modules():
    """
    Возвращает список ID модулей, доступных текущему пользователю.
    Суперадмин получает все модули + 'users'.
    """
    if session.get('is_admin'):
        return [m[0] for m in ALL_MODULES] + ['users']
    return session.get('allowed_modules', [])


# ---------------------------------------------------------------------------
# Декораторы
# ---------------------------------------------------------------------------
def login_required(f):
    """
    Защищает роут: пропускает суперадмина (is_admin) и субадминов (user_id).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_admin') or session.get('user_id'):
            return f(*args, **kwargs)
        return redirect(url_for('admin.login'))
    return decorated_function


def module_required(module_id):
    """
    Проверяет, что текущий пользователь имеет доступ к указанному модулю.
    Суперадмин пропускается всегда.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('is_admin'):
                return f(*args, **kwargs)
            if not session.get('user_id'):
                return redirect(url_for('admin.login'))
            allowed = session.get('allowed_modules', [])
            if module_id not in allowed:
                flash('У вас нет доступа к этому разделу.', 'error')
                return redirect(url_for('admin.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def superadmin_required(f):
    """Только суперадмин (is_admin из .env)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Доступ только для суперадминистратора.', 'error')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Маршруты
# ---------------------------------------------------------------------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Страница входа. Два режима:
      - только пароль → суперадмин (сравниваем с ADMIN_PASSWORD из .env)
      - логин + пароль → субадмин (ищем в таблице admin_users)
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # --- Режим суперадмина: поле username пустое ---
        if not username:
            admin_password = current_app.config.get('ADMIN_PASSWORD', 'admin123')
            if password == admin_password:
                session.clear()
                session['is_admin'] = True
                log_admin_action('LOGIN', 'auth', details='Вход суперадмина')
                return redirect(url_for('admin.dashboard'))
            flash('Неверный пароль суперадминистратора.', 'error')
            return render_template('login.html')

        # --- Режим субадмина: логин + пароль ---
        from werkzeug.security import check_password_hash
        from app.db import get_db_connection
        with get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM admin_users WHERE username = ? AND is_active = 1',
                (username,)
            ).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            # Обновляем last_login
            from app.db import get_db_connection
            with get_db_connection() as conn:
                conn.execute(
                    'UPDATE admin_users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                    (user['id'],)
                )
                conn.commit()

            allowed = json.loads(user['allowed_modules'] or '[]')
            session.clear()
            session['user_id']       = user['id']
            session['username']      = user['username']
            session['user_role']     = user['role']
            session['allowed_modules'] = allowed

            log_admin_action('LOGIN', 'auth', details='Вход сотрудника')

            # Перенаправляем на первый доступный модуль
            first_tab = allowed[0] if allowed else 'news'
            return redirect(url_for('admin.dashboard', tab=first_tab))

        flash('Неверный логин или пароль.', 'error')

    return render_template('login.html')


@bp.route('/logout')
def logout():
    """Сбрасывает сессию и перенаправляет на главную."""
    if session.get('is_admin') or session.get('user_id'):
        log_admin_action('LOGOUT', 'auth', details='Выход из системы')
    session.clear()
    return redirect(url_for('main.index'))
