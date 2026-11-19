"""
Katalog event astronomi hasil hitung sendiri (lihat catalog/generate.py) + keterlihatan & kelangkaan per lokasi.
Waktu masukan/keluaran: UTC dan waktu lokal (zona dari parameter tz atau dari bujur).
"""
import json
from datetime import datetime, timedelta
from functools import lru_cache

from flask import Blueprint, current_app, jsonify, render_template, request

from catalog import rarity as R
from prototype.find_events import BODY_ID
from catalog import visibility as V

catalog_bp = Blueprint('catalog', __name__)

SKY_LIMITS = {'kota': 4.0, 'pinggiran': 5.0, 'gelap': 6.0}
CATEGORY_LABEL = {'fase_bulan': 'Fase Bulan', 'konjungsi': 'Konjungsi', 'okultasi': 'Okultasi', 'gerhana_bulan': 'Gerhana Bulan',
                  'gerhana_matahari': 'Gerhana Matahari', 'elongasi': 'Elongasi', 'oposisi': 'Oposisi',
                  'fase_planet': 'Fase/Kecerahan Planet', 'hujan_meteor': 'Hujan Meteor'}


def _load():
    path = current_app.config['CATALOG_DIR'] / 'events.json'
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    return _read(str(path), mtime)


@lru_cache(maxsize=2)
def _read(path: str, mtime: float):
    return json.loads(open(path, encoding='utf-8').read())


@lru_cache(maxsize=20000)
def _evaluate(ev_json: str, lat: float, lon: float, limit: float, tz: float):
    ev = json.loads(ev_json)
    vis = V.evaluate(ev, lat, lon, limit, tz)
    rar = R.rarity(ev, vis)
    return vis, rar


def _tz_from_lon(lon: float) -> float:
    if 95 <= lon < 115:
        return 7.0
    if 115 <= lon < 130:
        return 8.0
    if 130 <= lon <= 141.5:
        return 9.0
    return float(round(lon / 15.0))


def _local(utc_iso: str, tz: float) -> str:
    return (datetime.strptime(utc_iso[:19], '%Y-%m-%dT%H:%M:%S') + timedelta(hours=tz)).strftime('%Y-%m-%d %H:%M')


@catalog_bp.route('/')
def index():
    return render_template('catalog/index.html')


@catalog_bp.route('/api/events')
def api_events():
    doc = _load()
    if doc is None:
        return jsonify({'status': 'empty', 'message': 'Katalog belum dibuat. Jalankan: python -m catalog.generate 2026 2027'}), 404
    try:
        lat = float(request.args.get('lat', -7.7956))
        lon = float(request.args.get('lon', 110.3695))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Koordinat harus berupa angka.'}), 400
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({'status': 'error', 'message': 'Koordinat di luar rentang.'}), 400
    sky = request.args.get('langit', 'pinggiran')
    if sky not in SKY_LIMITS:
        return jsonify({'status': 'error', 'message': 'Parameter langit: kota | pinggiran | gelap.'}), 400
    try:
        tz = float(request.args.get('tz')) if request.args.get('tz') else _tz_from_lon(lon)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'tz harus berupa angka (jam).'}), 400

    year, month = request.args.get('year', type=int), request.args.get('month', type=int)
    items = []
    for ev in doc['events']:
        local_t = _local(ev['time_utc'], tz)
        if year and not local_t.startswith(f'{year:04d}-' + (f'{month:02d}' if month else '')):
            continue
        vis, rar = _evaluate(json.dumps(ev, sort_keys=True), round(lat, 3), round(lon, 3), SKY_LIMITS[sky], tz)
        items.append({**ev, 'time_local': local_t, 'kategori_label': CATEGORY_LABEL.get(ev['category'], ev['category']),
                      'visibility': vis, 'rarity': rar})
    summary = {
        'total': len(items),
        'teramati': sum(1 for i in items if i['visibility']['state'] in ('visible', 'twilight')),
        'mata_telanjang': sum(1 for i in items if i['visibility']['instrument'] == 'naked_eye' and i['visibility']['state'] in ('visible', 'twilight')),
        'langka_ke_atas': sum(1 for i in items if R.TIERS.index(i['rarity']['tier']) >= 2),
    }
    return jsonify({'status': 'success', 'meta': doc['meta'], 'lokasi': {'lat': lat, 'lon': lon, 'tz': tz, 'langit': sky,
                    'batas_magnitudo': SKY_LIMITS[sky]}, 'summary': summary, 'events': items,
                    'tier_label': R.TIER_LABEL, 'body_names': BODY_ID, 'state_label': V.STATE_LABEL, 'instrument_label': {k: v for k, v in V.INSTRUMENT_LABEL.items() if k}})
