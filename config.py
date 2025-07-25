import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una_clave_secreta_muy_segura'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///bodega.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False