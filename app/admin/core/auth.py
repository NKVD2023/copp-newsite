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
                import os
                from dotenv import load_dotenv
                load_dotenv()
                is_2fa_enabled = os.environ.get('ADMIN_2FA_ENABLED') == '1'
                
                if is_2fa_enabled:
                    session.clear()
                    session['2fa_pending_admin'] = True
                    return redirect(url_for('admin.verify_2fa'))

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
            if user['is_2fa_enabled']:
                session.clear()
                session['2fa_pending_user_id'] = user['id']
                return redirect(url_for('admin.verify_2fa'))

            # Обновляем last_login
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

@bp.route('/2fa_verify', methods=['GET', 'POST'])
def verify_2fa():
    # Проверяем, есть ли ожидающий вход
    if '2fa_pending_admin' not in session and '2fa_pending_user_id' not in session:
        return redirect(url_for('admin.login'))
        
    if request.method == 'POST':
        code = request.form.get('code', '').strip().replace(' ', '')
        
        is_admin_pending = session.get('2fa_pending_admin')
        user_id = session.get('2fa_pending_user_id')
        
        import pyotp
        import os
        from dotenv import load_dotenv
        
        secret = None
        backup_codes_str = '[]'
        
        if is_admin_pending:
            load_dotenv()
            secret = os.environ.get('ADMIN_TOTP_SECRET')
            backup_codes_str = os.environ.get('ADMIN_BACKUP_CODES', '[]')
        else:
            from app.db import get_db_connection
            with get_db_connection() as conn:
                user = conn.execute('SELECT * FROM admin_users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return redirect(url_for('admin.login'))
            secret = user['totp_secret']
            backup_codes_str = user['backup_codes'] or '[]'
            
        import json
        try:
            backup_codes = json.loads(backup_codes_str)
        except:
            backup_codes = []

        is_valid = False
        used_backup = False
        
        # Проверяем как ТОТР
        if secret and code.isdigit() and len(code) == 6:
            totp = pyotp.TOTP(secret)
            if totp.verify(code):
                is_valid = True
                
        # Проверяем как резервный код
        if not is_valid and code in backup_codes:
            is_valid = True
            used_backup = True
            backup_codes.remove(code)
            
        if is_valid:
            if is_admin_pending:
                if used_backup:
                    from dotenv import set_key
                    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
                    set_key(dotenv_path, 'ADMIN_BACKUP_CODES', json.dumps(backup_codes))
                session.clear()
                session['is_admin'] = True
                log_admin_action('LOGIN', 'auth', details='Вход суперадмина (2FA)')
                return redirect(url_for('admin.dashboard'))
            else:
                if used_backup:
                    from app.db import get_db_connection
                    with get_db_connection() as conn:
                        conn.execute('UPDATE admin_users SET backup_codes = ? WHERE id = ?', (json.dumps(backup_codes), user_id))
                        conn.commit()
                        
                with get_db_connection() as conn:
                    conn.execute('UPDATE admin_users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
                    conn.commit()
                allowed = json.loads(user['allowed_modules'] or '[]')
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_role'] = user['role']
                session['allowed_modules'] = allowed
                log_admin_action('LOGIN', 'auth', details='Вход сотрудника (2FA)')
                first_tab = allowed[0] if allowed else 'news'
                return redirect(url_for('admin.dashboard', tab=first_tab))
        else:
            flash('Неверный код. Попробуйте еще раз или используйте резервный код.', 'error')

    return render_template('2fa_verify.html')


@bp.route('/logout')
def logout():
    """Сбрасывает сессию и перенаправляет на главную."""
    if session.get('is_admin') or session.get('user_id'):
        log_admin_action('LOGOUT', 'auth', details='Выход из системы')
    session.clear()
    return redirect(url_for('main.index'))
