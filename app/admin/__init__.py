from flask import Blueprint

bp = Blueprint('admin', __name__)

# Импортируем модули маршрутов (Они должны быть внизу, чтобы избежать циклических импортов)
from app.admin import auth, dashboard, news, contacts, documents, pages, projects, socials, statistics, database, prof_stats