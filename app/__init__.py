from flask import Flask

from config import Config


def create_app(config_class=Config):
    """Factory function to initialize and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Pastikan direktori data runtime ada
    for key in ('DATA_DIR', 'CATALOG_DIR', 'KNOWLEDGE_BASE_DIR'):
        app.config[key].mkdir(parents=True, exist_ok=True)

    @app.context_processor
    def inject_defaults():
        from app.services.timezones import tz_from_lon, tz_label
        loc = app.config['DEFAULT_LOCATION']
        return {'default_location': {**loc, 'tz_label': tz_label(tz_from_lon(loc['lon']))}}

    from app.routes.main import main_bp
    from app.routes.observation import observation_bp
    from app.routes.catalog import catalog_bp
    from app.routes.calendar import calendar_bp
    from app.routes.islamic import islamic_bp
    from app.routes.bot import bot_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(observation_bp, url_prefix='/observation')
    app.register_blueprint(catalog_bp, url_prefix='/catalog')
    app.register_blueprint(calendar_bp, url_prefix='/calendar')
    app.register_blueprint(islamic_bp, url_prefix='/islamic')
    app.register_blueprint(bot_bp, url_prefix='/bot')

    return app
