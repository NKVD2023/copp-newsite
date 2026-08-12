from flask import render_template, request, redirect, url_for, flash, session, current_app
from app.admin import bp
from app.admin.core.auth import login_required
from app.db import get_db_connection
import pyotp
import os
import json
import base64
import io
import qrcode
import string
import secrets
from dotenv import load_dotenv, set_key

@bp.route('/profile')
@login_required
def profile():
    is_admin = session.get('is_admin')
    is_2fa_enabled = False
    
    if is_admin:
        load_dotenv()
        is_2fa_enabled = os.environ.get('ADMIN_2FA_ENABLED') == '1'
    else:
        user_id = session.get('user_id')
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM admin_users WHERE id = ?', (user_id,)).fetchone()
            if user:
                is_2fa_enabled = bool(user['is_2fa_enabled'])
                
    return render_template('admin_profile.html', is_2fa_enabled=is_2fa_enabled)

@bp.route('/profile/setup_2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    is_admin = session.get('is_admin')
    username = 'Суперадмин' if is_admin else session.get('username')
    
    # Генерируем новый секрет
    secret = pyotp.random_base32()
    
    # Формируем URL для Яндекс.Ключа
    issuer = "ЦОПП РК"
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)
    
    # Генерируем QR-код в base64
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    qr_code_data = f"data:image/png;base64,{b64}"
    
    # Генерируем 8 резервных кодов (формат xxxx-xxxx)
    backup_codes = []
    for _ in range(8):
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        backup_codes.append(code)
        
    session['pending_2fa_secret'] = secret
    session['pending_2fa_backup_codes'] = backup_codes
    
    return render_template('admin_setup_2fa.html', secret=secret, qr_code_data=qr_code_data, backup_codes=backup_codes)

@bp.route('/profile/confirm_2fa', methods=['POST'])
@login_required
def confirm_2fa():
    code = request.form.get('code', '').strip().replace(' ', '')
    secret = session.get('pending_2fa_secret')
    backup_codes = session.get('pending_2fa_backup_codes', [])
    
    if not secret:
        flash('Сессия настройки 2FA истекла. Попробуйте снова.', 'error')
        return redirect(url_for('admin.profile'))
        
    totp = pyotp.TOTP(secret)
    if not totp.verify(code):
        flash('Неверный код. Попробуйте еще раз.', 'error')
        return redirect(url_for('admin.setup_2fa'))
        
    is_admin = session.get('is_admin')
    if is_admin:
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
        set_key(dotenv_path, 'ADMIN_TOTP_SECRET', secret)
        set_key(dotenv_path, 'ADMIN_BACKUP_CODES', json.dumps(backup_codes))
        set_key(dotenv_path, 'ADMIN_2FA_ENABLED', '1')
    else:
        user_id = session.get('user_id')
        with get_db_connection() as conn:
            conn.execute('''
                UPDATE admin_users 
                SET totp_secret = ?, is_2fa_enabled = 1, backup_codes = ?
                WHERE id = ?
            ''', (secret, json.dumps(backup_codes), user_id))
            conn.commit()
            
    # Очищаем сессию
    session.pop('pending_2fa_secret', None)
    session.pop('pending_2fa_backup_codes', None)
    
    flash('Двухэтапная аутентификация успешно включена!', 'success')
    return redirect(url_for('admin.profile'))

@bp.route('/profile/disable_2fa', methods=['POST'])
@login_required
def disable_2fa():
    is_admin = session.get('is_admin')
    if is_admin:
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
        set_key(dotenv_path, 'ADMIN_2FA_ENABLED', '0')
        set_key(dotenv_path, 'ADMIN_TOTP_SECRET', '')
        set_key(dotenv_path, 'ADMIN_BACKUP_CODES', '[]')
    else:
        user_id = session.get('user_id')
        with get_db_connection() as conn:
            conn.execute('''
                UPDATE admin_users 
                SET is_2fa_enabled = 0, totp_secret = NULL, backup_codes = NULL
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            
    flash('Двухэтапная аутентификация отключена.', 'info')
    return redirect(url_for('admin.profile'))
