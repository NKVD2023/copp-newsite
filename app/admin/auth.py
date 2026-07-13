"""
Модуль аутентификации администратора.
Отвечает за вход (логин) и выход (логаут) из админ-панели.
"""
from functools import wraps
from flask import render_template, request, redirect, url_for, session, flash
from app.admin import bp


def login_required(f):
    """
    Декоратор для защиты маршрутов админ-панели.
    Заменяет повторяющуюся проверку:
        if not session.get('is_admin'):
            return redirect(url_for('admin.login'))
    которая дублировалась во всех admin-роутах.

    Использование:
        @bp.route('/some_route')
        @login_required
        def some_view():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Страница входа в админ-панель.
    При POST-запросе проверяет пароль. При успехе записывает флаг 'is_admin' в сессию.
    (Пароль временно захардкожен, для продакшена следует использовать хэширование БД)
    """
    if request.method == 'POST':
        if request.form['password'] == 'admin123':
            session['is_admin'] = True
            return redirect(url_for('admin.dashboard'))
        flash('Неверный пароль', 'error')
    return render_template('login.html')


@bp.route('/logout')
def logout():
    """
    Сбрасывает сессию администратора и перенаправляет на главную страницу.
    """
    session.pop('is_admin', None)
    return redirect(url_for('main.index'))