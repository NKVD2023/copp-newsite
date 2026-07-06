from flask import Blueprint

bp = Blueprint('main', __name__)

# Импорт должен быть строго ВНИЗУ, после создания bp, чтобы избежать циклических импортов
from app.main import routes