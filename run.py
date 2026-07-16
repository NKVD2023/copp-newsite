"""
Главный файл запуска приложения.
Используется для старта локального веб-сервера (development server).
Не рекомендуется для использования в production-среде (там лучше использовать Gunicorn/uWSGI).
"""
import os
import sys
import subprocess
from app import create_app
from apscheduler.schedulers.background import BackgroundScheduler

# Создаем экземпляр приложения через фабрику (Application Factory)
app = create_app()

def run_sync_task():
    print("Запуск ночной синхронизации данных (4:00 AM)...")
    try:
        # Запускаем скрипт синхронизации
        subprocess.run([sys.executable, os.path.join("app", "utils", "trudvsem_sync.py")], check=True)
        print("Синхронизация успешно завершена!")
    except Exception as e:
        print(f"Ошибка при фоновой синхронизации: {e}")

if __name__ == '__main__':
    # Чтобы планировщик не запускался дважды при debug=True (из-за werkzeug reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        scheduler = BackgroundScheduler()
        # Запуск каждый день в 04:00
        scheduler.add_job(func=run_sync_task, trigger="cron", hour=4, minute=0)
        scheduler.start()

    # Запуск сервера:
    # debug=True - включает автоперезагрузку при изменении кода и детальные ошибки
    # host='0.0.0.0' - делает сервер доступным извне (по локальной сети)
    # port=5000 - порт, на котором запускается приложение
    app.run(debug=True, host='0.0.0.0', port=5000)