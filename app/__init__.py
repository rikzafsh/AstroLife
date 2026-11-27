"""Pabrik aplikasi Flask AstroLife: mendaftarkan blueprint tiap modul dan variabel templat bersama."""
from flask import Flask

from config import Config


KET_KRITERIA = {
    'aritmetis': 'Tabel hisab urfi, tanpa pengamatan hilal. Cepat dan tetap; bisa berbeda 1–2 hari dari penetapan resmi.',
    'mabims': 'Elongasi ≥ 6,4° dan tinggi hilal ≥ 3° (titik acuan Indonesia/Asia Tenggara).',
    'ummulqura': 'Ijtimak sebelum matahari terbenam di Makkah dan Bulan terbenam sesudahnya.',
    'wujudulhilal': 'Ijtimak sebelum matahari terbenam dan hilal di atas ufuk (acuan Yogyakarta).',
    'turki': 'KHGT: elongasi ≥ 8° dan tinggi ≥ 5° di titik mana pun di dunia (kalender global).',
}


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
        from app.persis import salat
        from app.services import falak_service as F
        return {'default_location': {**loc, 'tz_label': tz_label(tz_from_lon(loc['lon']))},
                'pref_metode': [{'kunci': k, 'nama': m.name} for k, m in salat.METODE.items()],
                'pref_kriteria': [{'kunci': k, 'nama': F.nama_kriteria(k), 'ket': KET_KRITERIA[k]}
                                  for k in ('aritmetis', 'mabims', 'ummulqura', 'wujudulhilal', 'turki')]}

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
