"""
Инициализация Blueprint для панели администратора.
Все маршруты внутри этого Blueprint будут доступны по префиксу /admin.
"""
from flask import Blueprint

# Создаем Blueprint админки
bp = Blueprint('admin', __name__)

# Импортируем модули маршрутов админки. 
# Они должны быть строго внизу, чтобы избежать циклических импортов, 
# так как внутри этих файлов импортируется переменная `bp` из этого файла.
from app.admin import auth, dashboard, news, contacts, documents, pages, projects, socials, statistics, database, prof_stats, professions