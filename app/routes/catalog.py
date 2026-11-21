"""
Katalog event astronomi hasil hitung sendiri (lihat catalog/generate.py) + keterlihatan & kelangkaan per lokasi.
Waktu masukan/keluaran: UTC dan waktu lokal (zona dari parameter tz atau dari bujur).
"""
import json
from datetime import datetime, timedelta
from functools import lru_cache

from flask import Blueprint, current_app, jsonify, render_template, request

from catalog import rarity as R
from app.services.timezones import tz_from_lon, tz_label
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
    with open(path, encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=20000)
def _evaluate(ev_json: str, lat: float, lon: float, limit: float, tz: float):
    ev = json.loads(ev_json)
    vis = V.evaluate(ev, lat, lon, limit, tz)
    rar = R.rarity(ev, vis)
    return vis, rar


def _local(utc_iso: str, tz: float) -> str:
    return (datetime.strptime(utc_iso[:19], '%Y-%m-%dT%H:%M:%S') + timedelta(hours=tz)).strftime('%Y-%m-%d %H:%M')


TIME_LABELS = [('start_utc', 'Mulai'), ('end_utc', 'Selesai')]
DETAIL_TIME_LABELS = {
    'pendekatan_terdekat_utc': 'Pendekatan terdekat', 'konjungsi_asensio_rekta_utc': 'Konjungsi (asensio rekta)',
    'umbra_mulai_utc': 'Umbra mulai', 'umbra_selesai_utc': 'Umbra selesai',
    'total_mulai_utc': 'Totalitas mulai', 'total_selesai_utc': 'Totalitas selesai',
}


def _times_local(ev: dict, vis: dict, tz: float) -> list:
    """Semua jam yang ditampilkan di UI, SUDAH dalam waktu lokal lokasi (UI tidak menampilkan UTC)."""
    out = []
    for key, label in TIME_LABELS:
        if ev.get(key):
            out.append({'label': label + (' (jendela global)' if ev['category'] == 'okultasi' else ''), 'value': _local(ev[key], tz)})
    for key, label in DETAIL_TIME_LABELS.items():
        if ev.get('details', {}).get(key):
            out.append({'label': label, 'value': _local(ev['details'][key], tz)})
    le = vis.get('local_eclipse')
    if le and le.get('terlihat'):
        out.append({'label': 'Puncak gerhana di lokasi', 'value': _local(le['waktu_maks_utc'], tz)})
    return out


def _wx(ev: dict, vis: dict, tz: float) -> dict:
    """Bahan tautan ke analisis cuaca: waktu puncak event & waktu terbaik (bila dapat diamati), format lokal ISO."""
    peak = _local(ev['time_utc'], tz).replace(' ', 'T')
    best = _local(vis['best_time_utc'], tz).replace(' ', 'T') if vis.get('observable') and vis.get('best_time_utc') else None
    return {'peak': peak, 'best': best, 'default': best or peak}


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
        tz = float(request.args.get('tz')) if request.args.get('tz') else tz_from_lon(lon)
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
                      'visibility': vis, 'rarity': rar, 'times_local': _times_local(ev, vis, tz), 'wx': _wx(ev, vis, tz)})
    obs = [i for i in items if i['visibility']['observable']]
    summary = {
        'total': len(items),
        'teramati': len(obs),
        'mata_telanjang': sum(1 for i in obs if i['visibility']['instrument'] == 'naked_eye'),
        'langka_ke_atas': sum(1 for i in items if R.TIERS.index(i['rarity']['tier']) >= 2),
    }
    return jsonify({'status': 'success', 'meta': doc['meta'], 'lokasi': {'lat': lat, 'lon': lon, 'tz': tz, 'tz_label': tz_label(tz), 'langit': sky,
                    'batas_magnitudo': SKY_LIMITS[sky]}, 'summary': summary, 'events': items,
                    'tier_label': R.TIER_LABEL, 'body_names': BODY_ID, 'state_label': V.STATE_LABEL, 'instrument_label': {k: v for k, v in V.INSTRUMENT_LABEL.items() if k}})
