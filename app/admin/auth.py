from flask import render_template, request, redirect, url_for, session, flash
from app.admin import bp

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == 'admin123': 
            session['is_admin'] = True
            return redirect(url_for('admin.dashboard'))
        flash('Неверный пароль', 'error')
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('main.index'))