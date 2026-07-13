"""
Утилита для сканирования директории загрузок (uploads).
Вынесено из трёх мест (admin/__init__.py, admin/dashboard.py, admin/professions.py),
где дублировался одинаковый код os.walk().
"""
import os
from datetime import datetime

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}


def scan_uploads_dir(uploads_dir: str = None) -> list:
    """
    Рекурсивно сканирует папку uploads и возвращает список словарей с метаданными файлов.
    Результат отсортирован по дате изменения (новые сверху).

    Args:
        uploads_dir: Путь к директории uploads. По умолчанию 'app/static/uploads'.

    Returns:
        Список словарей: [{'filename', 'filepath', 'folder', 'size_kb', 'date_str', 'is_image', 'timestamp'}]
    """
    if uploads_dir is None:
        uploads_dir = os.path.join('app', 'static', 'uploads')

    result = []

    if not os.path.exists(uploads_dir):
        return result

    static_root = os.path.join('app', 'static')

    for root, dirs, files in os.walk(uploads_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                rel_path = os.path.relpath(filepath, static_root).replace('\\', '/')
                folder = os.path.basename(root)
                stat = os.stat(filepath)
                size_kb = round(stat.st_size / 1024, 1)
                date_str = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                is_image = ext in IMAGE_EXTENSIONS
                result.append({
                    'filename': filename,
                    'filepath': rel_path,
                    'folder': folder,
                    'size_kb': size_kb,
                    'date_str': date_str,
                    'is_image': is_image,
                    'timestamp': stat.st_mtime,
                })
            except OSError:
                # Файл мог быть удален между walk и stat — пропускаем
                continue

    result.sort(key=lambda x: x['timestamp'], reverse=True)
    return result
