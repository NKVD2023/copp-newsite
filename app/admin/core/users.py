"""
Модуль управления пользователями-администраторами.
Доступен только суперадмину.
"""
import json
import random
import string
from flask import render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash

from app.admin import bp
from app.admin.core.auth import login_required, superadmin_required
from app.admin.core.logger import log_admin_action
from app.db import get_db_connection


def generate_password(length=12):
    """Генерирует случайный пароль из букв и цифр."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))


@bp.route('/users/add', methods=['POST'])
@login_required
@superadmin_required
def add_user():
    """Создать нового пользователя."""
    username        = request.form.get('username', '').strip()
    role            = request.form.get('role', 'editor')
    allowed_modules = request.form.getlist('allowed_modules')

    if not username:
        flash('Логин не может быть пустым.', 'error')
        return redirect(url_for('admin.dashboard', tab='users'))

    password      = generate_password()
    password_hash = generate_password_hash(password)
    modules_json  = json.dumps(allowed_modules)

    try:
        with get_db_connection() as conn:
            conn.execute(
                '''INSERT INTO admin_users (username, password_hash, role, allowed_modules)
                   VALUES (?, ?, ?, ?)''',
                (username, password_hash, role, modules_json)
            )
            conn.commit()
            
            # Логируем создание пользователя (entity_id = id нового пользователя)
            user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            log_admin_action('CREATE', 'users', entity_id=user_id, details=f'Создан пользователь "{username}" (роль: {role})')

        # Возвращаем пароль один раз через flash — после этого восстановить нельзя
        flash(f'Пользователь «{username}» создан. Пароль (сохраните!): {password}', 'password_reveal')
    except Exception as e:
        if 'UNIQUE constraint failed' in str(e):
            flash(f'Пользователь с логином «{username}» уже существует.', 'error')
        else:
            flash(f'Ошибка при создании пользователя: {e}', 'error')

    return redirect(url_for('admin.dashboard', tab='users'))


@bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@superadmin_required
def edit_user(user_id):
    """Изменить роль и список доступных модулей."""
    role            = request.form.get('role', 'editor')
    allowed_modules = request.form.getlist('allowed_modules')
    modules_json    = json.dumps(allowed_modules)

    with get_db_connection() as conn:
        conn.execute(
            'UPDATE admin_users SET role = ?, allowed_modules = ? WHERE id = ?',
            (role, modules_json, user_id)
        )
        conn.commit()
        
        user_info = conn.execute('SELECT username FROM admin_users WHERE id = ?', (user_id,)).fetchone()
        if user_info:
            log_admin_action('UPDATE', 'users', entity_id=user_id, details=f'Обновлены права пользователя "{user_info["username"]}" (новая роль: {role})')

    flash('Права пользователя обновлены.', 'success')
    return redirect(url_for('admin.dashboard', tab='users'))


@bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@superadmin_required
def toggle_user(user_id):
    """Активировать / деактивировать пользователя."""
    with get_db_connection() as conn:
        user = conn.execute('SELECT is_active FROM admin_users WHERE id = ?', (user_id,)).fetchone()
        if user:
            new_state = 0 if user['is_active'] else 1
            conn.execute('UPDATE admin_users SET is_active = ? WHERE id = ?', (new_state, user_id))
            conn.commit()
            
            action_name = "Активирован" if new_state else "Деактивирован"
            user_info = conn.execute('SELECT username FROM admin_users WHERE id = ?', (user_id,)).fetchone()
            log_admin_action('UPDATE', 'users', entity_id=user_id, details=f'{action_name} пользователь "{user_info["username"]}"')

    flash('Статус пользователя изменён.', 'success')
    return redirect(url_for('admin.dashboard', tab='users'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@superadmin_required
def delete_user(user_id):
    """Удалить пользователя."""
    with get_db_connection() as conn:
        user_info = conn.execute('SELECT username FROM admin_users WHERE id = ?', (user_id,)).fetchone()
        conn.execute('DELETE FROM admin_users WHERE id = ?', (user_id,))
        conn.commit()
        
        if user_info:
            log_admin_action('DELETE', 'users', entity_id=user_id, details=f'Удалён пользователь "{user_info["username"]}"')

    flash('Пользователь удалён.', 'success')
    return redirect(url_for('admin.dashboard', tab='users'))


@bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
@login_required
@superadmin_required
def reset_user_password(user_id):
    """Сгенерировать новый пароль для пользователя."""
    new_password  = generate_password()
    password_hash = generate_password_hash(new_password)
    with get_db_connection() as conn:
        user = conn.execute('SELECT username FROM admin_users WHERE id = ?', (user_id,)).fetchone()
        conn.execute('UPDATE admin_users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        conn.commit()
        if user:
            log_admin_action('UPDATE', 'users', entity_id=user_id, details=f'Сброшен пароль пользователя "{user["username"]}"')
            
    if user:
        flash(f'Новый пароль для «{user["username"]}» (сохраните!): {new_password}', 'password_reveal')
    return redirect(url_for('admin.dashboard', tab='users'))
