"""
Katalog event astronomi hasil hitung sendiri (lihat catalog/generate.py) + keterlihatan & kelangkaan per lokasi.
Pembuatan katalog dapat dijalankan dari antarmuka (catalog/jobs.py): tidak perlu perintah terminal.
Waktu masukan/keluaran: UTC pada katalog; semua waktu tampilan dalam waktu lokal lokasi (zona dari tz atau bujur).
"""
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request

from app.services.timezones import tz_from_lon, tz_label
from catalog import jobs
from catalog import rarity as R
from catalog import service as S
from catalog import visibility as V
from prototype.find_events import BODY_ID

catalog_bp = Blueprint('catalog', __name__)


def _error(msg, code=400):
    return jsonify({'status': 'error', 'message': msg}), code


def parse_location(args):
    """(lat, lon, sky, tz) dari parameter permintaan; ValueError berisi pesan untuk pengguna."""
    d = current_app.config['DEFAULT_LOCATION']
    try:
        lat, lon = float(args.get('lat', d['lat'])), float(args.get('lon', d['lon']))
    except ValueError:
        raise ValueError('Koordinat harus berupa angka.') from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Koordinat di luar rentang.')
    sky = args.get('langit', 'pinggiran')
    if sky not in S.SKY_LIMITS:
        raise ValueError('Parameter langit: kota | pinggiran | gelap.')
    try:
        tz = float(args.get('tz')) if args.get('tz') else tz_from_lon(lon)
    except ValueError:
        raise ValueError('tz harus berupa angka (jam).') from None
    if not -12 <= tz <= 14:
        raise ValueError('tz di luar rentang -12..+14.')
    return lat, lon, sky, tz


def _missing():
    return jsonify({'status': 'empty', 'message': 'Katalog belum dibuat. Buat dari halaman Katalog (tombol "Buat katalog") '
                    'atau jalankan: python -m catalog.generate 2026 2027', 'options': jobs.options()}), 404


@catalog_bp.route('/')
def index():
    return render_template('catalog/index.html')


@catalog_bp.route('/api/events')
def api_events():
    doc = S.load(current_app.config['CATALOG_DIR'])
    if doc is None:
        return _missing()
    try:
        lat, lon, sky, tz = parse_location(request.args)
    except ValueError as e:
        return _error(str(e))
    year, month = request.args.get('year', type=int), request.args.get('month', type=int)
    items = []
    for ev in doc['events']:
        if year and not S.local(ev['time_utc'], tz).startswith(f'{year:04d}-' + (f'{month:02d}' if month else '')):
            continue
        items.append(S.decorate(ev, lat, lon, sky, tz))
    obs = [i for i in items if i['visibility']['observable']]
    summary = {
        'total': len(items), 'teramati': len(obs),
        'mata_telanjang': sum(1 for i in obs if i['visibility']['instrument'] == 'naked_eye'),
        'langka_ke_atas': sum(1 for i in items if R.TIERS.index(i['rarity']['tier']) >= 2),
    }
    return jsonify({'status': 'success', 'meta': doc['meta'],
                    'lokasi': {'lat': lat, 'lon': lon, 'tz': tz, 'tz_label': tz_label(tz), 'langit': sky, 'batas_magnitudo': S.SKY_LIMITS[sky]},
                    'summary': summary, 'events': items, 'tier_label': R.TIER_LABEL, 'body_names': BODY_ID,
                    'state_label': V.STATE_LABEL, 'instrument_label': {k: v for k, v in V.INSTRUMENT_LABEL.items() if k}})


@catalog_bp.route('/api/upcoming')
def api_upcoming():
    """Event mulai sekarang sampai N hari ke depan, sudah dievaluasi untuk lokasi (dipakai Beranda)."""
    doc = S.load(current_app.config['CATALOG_DIR'])
    if doc is None:
        return _missing()
    try:
        lat, lon, sky, tz = parse_location(request.args)
    except ValueError as e:
        return _error(str(e))
    days = max(1, min(request.args.get('days', 14, type=int), 90))
    limit = max(1, min(request.args.get('limit', 6, type=int), 100))
    obs_only = request.args.get('observable', '1') != '0'
    now = datetime.utcnow()
    items = S.upcoming(doc, lat, lon, sky, tz, now, days, obs_only)
    return jsonify({'status': 'success', 'meta': doc['meta'], 'covered': S.covers(doc, now, days),
                    'lokasi': {'lat': lat, 'lon': lon, 'tz': tz, 'tz_label': tz_label(tz)},
                    'events': items[:limit], 'total': len(items), 'body_names': BODY_ID})


# ---------------------------------------------------------------------------
# Pembuatan katalog dari antarmuka
# ---------------------------------------------------------------------------
@catalog_bp.route('/api/generate/options')
def api_generate_options():
    d = current_app.config['CATALOG_DIR']
    doc = S.load(d)
    y = datetime.now().year
    return jsonify({**jobs.options(), 'suggested': {'dari': y, 'sampai': y + 1}, 'limits': {'min': jobs.MIN_YEAR, 'max': jobs.MAX_YEAR, 'span': jobs.MAX_SPAN},
                    'catalog': doc['meta'] if doc else None, 'covers_now': S.covers(doc, datetime.utcnow(), 30), 'status': jobs.read_status(d)})


@catalog_bp.route('/api/generate', methods=['POST'])
def api_generate_start():
    body = request.get_json(silent=True) or {}
    d = current_app.config['CATALOG_DIR']
    try:
        st = jobs.start(d, body.get('dari'), body.get('sampai'), body.get('mesin'), bool(body.get('force')))
    except jobs.JobBusy as e:
        return _error(str(e), 409)
    except ValueError as e:
        return _error(str(e))
    except OSError as e:
        return _error(f'Tidak dapat memulai proses: {e}', 500)
    return jsonify({'status': 'started', 'job': st}), 202


@catalog_bp.route('/api/generate/status')
def api_generate_status():
    d = current_app.config['CATALOG_DIR']
    st = jobs.read_status(d)
    if st.get('state') == 'error' and not st.get('log_tail'):
        st['log_tail'] = jobs.log_tail(d)
    doc = S.load(d)
    return jsonify({'job': st, 'catalog': doc['meta'] if doc else None})
