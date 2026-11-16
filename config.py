import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'astrolife-dev-secret-key-default')
    DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
    
    # Path Directories
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / 'data'
    CACHE_DIR = DATA_DIR / 'cache'
    DATASETS_DIR = DATA_DIR / 'datasets'
    KNOWLEDGE_BASE_DIR = DATA_DIR / 'knowledge_base'
    MODELS_DIR = DATA_DIR / 'trained_models'
    
    # External API Configuration
    GOOGLE_WEATHER_API_KEY = os.getenv('GOOGLE_WEATHER_API_KEY', '')
    
    # Cache settings (seconds)
    CACHE_EXPIRY_SECONDS = 3600 * 6  # 6 hours default cache for scraped data
