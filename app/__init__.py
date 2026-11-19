from flask import Flask
from config import Config

def create_app(config_class=Config):
    """Factory function to initialize and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure necessary runtime data directories exist
    for directory in [
        app.config['DATA_DIR'],
        app.config['CACHE_DIR'],
        app.config['DATASETS_DIR'],
        app.config['CATALOG_DIR'],
        app.config['KNOWLEDGE_BASE_DIR'],
        app.config['MODELS_DIR']
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.observation import observation_bp
    from app.routes.catalog import catalog_bp
    from app.routes.calendar import calendar_bp
    from app.routes.islamic import islamic_bp
    from app.routes.analytics import analytics_bp
    from app.routes.bot import bot_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(observation_bp, url_prefix='/observation')
    app.register_blueprint(catalog_bp, url_prefix='/catalog')
    app.register_blueprint(calendar_bp, url_prefix='/calendar')
    app.register_blueprint(islamic_bp, url_prefix='/islamic')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(bot_bp, url_prefix='/bot')

    return app
