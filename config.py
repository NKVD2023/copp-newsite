import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'copp_crimea_secret_key_2026'
    # База данных будет создана в корневой папке проекта
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'coppdb.sqlite')