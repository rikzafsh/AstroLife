"""
Observasi Langit: analisis cuaca untuk waktu & lokasi tertentu + rekomendasi event katalog yang cuacanya mendukung.
Semua event berasal dari katalog hasil hitung aplikasi (catalog/); tidak ada sumber data eksternal untuk event.
"""
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, render_template, request

from app.routes.catalog import _error, _missing, parse_location
from app.services import planner_service as planner
from app.services.timezones import tz_from_lon, tz_label
from app.services.weather_service import get_weather_at
from catalog import service as S

observation_bp = Blueprint('observation', __name__)


@observation_bp.route('/')
def index():
    return render_template('observation/index.html')


def _coords(data):
    try:
        lat, lon = float(data.get('lat', current_app.config['DEFAULT_LOCATION']['lat'])), float(data.get('lon', current_app.config['DEFAULT_LOCATION']['lon']))
    except (TypeError, ValueError):
        raise ValueError('Koordinat harus berupa angka.') from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Koordinat di luar rentang yang valid.')
    return lat, lon


@observation_bp.route('/api/feasibility', methods=['POST'])
def api_feasibility():
    """
    Kelayakan pengamatan di lokasi pada waktu tertentu.
    Waktu: `datetime_local` (YYYY-MM-DDTHH:MM, waktu lokal lokasi) + `tz` (jam, default dari bujur); bila kosong: sekarang.
    """
    data = request.get_json(silent=True) or {}
    try:
        lat, lon = _coords(data)
    except ValueError as e:
        return _error(str(e))
    difficulty = data.get('difficulty', 'naked_eye')
    event_type = data.get('event_type', 'General')
    try:
        tz = float(data['tz']) if data.get('tz') not in (None, '') else tz_from_lon(lon)
    except (TypeError, ValueError):
        return _error('tz harus berupa angka (jam).')
    if not -12 <= tz <= 14:
        return _error('tz di luar rentang -12..+14.')

    now = datetime.utcnow()
    when = now + timedelta(minutes=5)
    if data.get('datetime_local'):
        try:
            when = datetime.strptime(data['datetime_local'][:16], '%Y-%m-%dT%H:%M') - timedelta(hours=tz)
        except ValueError:
            return _error('Format waktu harus YYYY-MM-DDTHH:MM.')

    weather = get_weather_at(lat, lon, when, now)
    illum = planner.moon_illumination(when)
    malt = planner.moon_altitude_at(when, lat, lon)
    score = planner.calculate_observation_feasibility(weather, difficulty, event_type, illum, bool(data.get('involves_moon')), malt)
    return jsonify({'status': 'success', 'weather': weather, 'feasibility': score,
                    'moon_illumination_pct': round(illum * 100), 'moon_altitude_deg': round(malt),
                    'when_local': (when + timedelta(hours=tz)).strftime('%Y-%m-%d %H:%M'), 'tz': tz, 'tz_label': tz_label(tz)})


@observation_bp.route('/api/plan')
def api_plan():
    """Rekomendasi: event katalog yang dapat diamati dalam N hari, diberi skor cuaca pada waktu terbaiknya."""
    doc = S.load(current_app.config['CATALOG_DIR'])
    if doc is None:
        return _missing()
    try:
        lat, lon, sky, tz = parse_location(request.args)
    except ValueError as e:
        return _error(str(e))
    instrument = request.args.get('instrument', 'all')
    if instrument not in planner.GEAR_RANK:
        return _error('instrument: naked_eye | binoculars | telescope | all.')
    days = request.args.get('days', 14, type=int)
    limit = max(1, min(request.args.get('limit', 12, type=int), 50))
    now = datetime.utcnow()
    result = planner.plan(doc, lat, lon, sky, tz, instrument, now, days, limit)
    return jsonify({'status': 'success', 'lokasi': {'lat': lat, 'lon': lon, 'tz': tz, 'tz_label': tz_label(tz)},
                    'covered': S.covers(doc, now, result['days']), 'meta': doc['meta'], **result})


@observation_bp.route('/api/weather-batch', methods=['POST'])
def api_weather_batch():
    """Cuaca ringkas untuk banyak event sekaligus (Katalog Event). Hanya prakiraan per jam (satu pemanggilan Open-Meteo);
    klimatologi sengaja tidak dipakai di sini karena lambat untuk banyak item. Masukan: lat, lon, tz, items=[{id, dt}] (dt = waktu lokal ISO)."""
    from app.services.weather_service import FORECAST_DAYS, fetch_hourly_forecast
    data = request.get_json(silent=True) or {}
    try:
        lat, lon = _coords(data)
        tz = float(data['tz']) if data.get('tz') not in (None, '') else tz_from_lon(lon)
    except (TypeError, ValueError) as e:
        return _error(str(e))
    items = data.get('items') or []
    if not isinstance(items, list) or len(items) > 300:
        return _error('items harus berupa daftar (maksimal 300).')
    now = datetime.utcnow()
    fc = None
    hasil = {}
    for it in items:
        try:
            eid, dt = str(it['id']), str(it['dt'])[:16]
            when = datetime.strptime(dt, '%Y-%m-%dT%H:%M') - timedelta(hours=tz)
        except (KeyError, TypeError, ValueError):
            continue
        if when < now - timedelta(hours=1):
            hasil[eid] = {'status': 'lewat'}
        elif (when - now).total_seconds() / 86400.0 > FORECAST_DAYS - 0.5:
            hasil[eid] = {'status': 'jauh'}
        else:
            if fc is None:
                fc = fetch_hourly_forecast(lat, lon) or False
            w = get_weather_at(lat, lon, when, now) if fc else None
            if not w or w.get('kind') != 'forecast':
                hasil[eid] = {'status': 'tak_tersedia'}
            else:
                hasil[eid] = {'status': 'ok', 'awan': round(w['cloud_cover_pct']), 'hujan': round(w.get('precipitation_prob') or 0),
                              'kondisi': w['condition'], 'jam': w['valid_local'][11:16]}
    return jsonify({'status': 'success', 'hasil': hasil, 'tz_label': tz_label(tz)})
