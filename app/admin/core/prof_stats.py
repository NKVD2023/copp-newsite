from flask import request, redirect, url_for, flash
from app.admin import bp
from app.db import get_db_connection
from app.admin.core.auth import login_required
import pandas as pd
import os
import threading
import json
from werkzeug.utils import secure_filename
from flask import current_app, jsonify
from app.utils.trudvsem_sync import run_trudvsem_sync

def clean_val(v):
    if pd.isna(v):
        return None
    return str(v)


@bp.route('/trudvsem_sync', methods=['POST'])
@login_required
def trudvsem_sync():
    """
    Запускает синхронизацию с API Работа в России в фоновом потоке.
    """
    # Мы используем абсолютный путь к БД для фонового потока
    db_path = current_app.config['DATABASE']
    
    # Запускаем в фоне, чтобы не блокировать веб-интерфейс
    thread = threading.Thread(target=run_trudvsem_sync, args=(db_path,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "message": "Синхронизация запущена"})


@bp.route('/trudvsem_sync/status', methods=['GET'])
@login_required
def trudvsem_sync_status():
    """
    Возвращает текущий статус синхронизации из JSON-файла.
    """
    status_file = os.path.join('app', 'static', 'data', 'sync_status.json')
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return jsonify(data)
        except Exception as e:
            return jsonify({"status": "error", "message": f"Ошибка чтения статуса: {str(e)}"})
    return jsonify({"status": "idle", "message": "Синхронизация не запущена"})
