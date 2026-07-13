import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    # База данных будет создана в корневой папке проекта
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'coppdb.sqlite')