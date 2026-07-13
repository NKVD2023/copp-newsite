"""
Инициализация публичного Blueprint (основная часть сайта для обычных посетителей).
"""
from flask import Blueprint

# Создаем публичный Blueprint с именем 'main'
bp = Blueprint('main', __name__)

# Импорт маршрутов должен быть строго ВНИЗУ, после создания bp, 
# чтобы избежать ошибки циклических импортов (circular imports).
from app.main.routes import index, news, atlas, pages, projects, dashboard, team