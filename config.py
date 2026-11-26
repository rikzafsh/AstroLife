import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Konfigurasi dasar aplikasi."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'astrolife-dev-secret-key-default')
    DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'

    # Direktori
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / 'data'
    CATALOG_DIR = DATA_DIR / 'catalog'          # katalog event hasil hitung (events.json, status pembuatan)
    KNOWLEDGE_BASE_DIR = DATA_DIR / 'knowledge_base'

    # Lokasi pengamat bawaan (dipakai di bilah atas, beranda, katalog, dan observasi)
    DEFAULT_LOCATION = {'name': 'Yogyakarta', 'lat': -7.7956, 'lon': 110.3695}
