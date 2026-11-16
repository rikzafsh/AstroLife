import threading
import time
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from app.services.scraper_service import scrape_in_the_sky_events
from app.services.weather_service import get_weather_at
from app.services import planner_service as planner

observation_bp = Blueprint('observation', __name__)

# State tracking for background scraper task
sync_lock = threading.Lock()
sync_state = {
    'is_running': False,
    'started_at': None,
    'completed_at': None,
    'last_status': 'idle',
    'message': 'Belum ada proses sinkronisasi aktif.'
}

@observation_bp.route('/')
def index():
    """Main observation planner dashboard."""
    return render_template('observation/index.html')

@observation_bp.route('/api/events')
def api_events():
    """Fetch astronomical events from cache/dataset instantly."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    events = scrape_in_the_sky_events(year=year, month=month)
    return jsonify({
        'status': 'success',
        'count': len(events),
        'events': events,
        'sync_state': sync_state
    })

def _coords(data):
    """Validasi lat/lon dari request (JSON atau query)."""
    try:
        lat = float(data.get('lat', -6.2088))
        lon = float(data.get('lon', 106.8456))
    except (TypeError, ValueError):
        raise ValueError('Koordinat harus berupa angka.')
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Koordinat di luar rentang yang valid.')
    return lat, lon


@observation_bp.route('/api/feasibility', methods=['POST'])
def api_feasibility():
    """Kelayakan pengamatan di lokasi untuk waktu tertentu (default: malam ini 20:00 WIB / waktu terdekat)."""
    data = request.get_json(silent=True) or {}
    try:
        lat, lon = _coords(data)
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    difficulty = data.get('difficulty', 'naked_eye')
    event_type = data.get('event_type', 'General')

    now = datetime.utcnow()
    when = now + timedelta(minutes=5)
    if data.get('datetime_wib'):           # contoh: 2026-11-18T20:00
        try:
            when = planner.wib_to_utc(data['datetime_wib'])
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Format waktu harus YYYY-MM-DDTHH:MM (WIB).'}), 400

    weather = get_weather_at(lat, lon, when, now)
    illum = planner.moon_illumination(when)
    malt = planner.moon_altitude_at(when, lat, lon)
    score = planner.calculate_observation_feasibility(weather, difficulty, event_type, illum, False, malt)
    return jsonify({'status': 'success', 'weather': weather, 'feasibility': score,
                    'moon_illumination_pct': round(illum * 100)})


@observation_bp.route('/api/event-forecast', methods=['POST'])
def api_event_forecast():
    """Prakiraan cuaca + skor untuk SATU fenomena (waktu dari fenomena itu sendiri)."""
    data = request.get_json(silent=True) or {}
    try:
        lat, lon = _coords(data)
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    events = scrape_in_the_sky_events(year=data.get('year'), month=data.get('month'))
    event = next((e for e in events if e['id'] == data.get('event_id')), None)
    if not event:
        return jsonify({'status': 'error', 'message': 'Fenomena tidak ditemukan.'}), 404
    result = planner.evaluate_event(event, lat, lon, data.get('instrument'))
    result['event'] = {k: event[k] for k in ('id', 'title', 'type', 'date', 'obs_note', 'peak_time')}
    return jsonify({'status': 'success', **result})


@observation_bp.route('/api/plan')
def api_plan():
    """Skor semua fenomena untuk lokasi + rekomendasi terbaik."""
    try:
        lat, lon = _coords(request.args)
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    result = planner.plan(lat, lon, request.args.get('instrument'),
                          request.args.get('year', type=int), request.args.get('month', type=int))
    return jsonify({'status': 'success', **result})


@observation_bp.route('/api/sync', methods=['POST'])
def api_sync():
    """Triggers background scraping from in-the-sky.org without freezing the web app."""
    global sync_state
    body = request.get_json(silent=True) or {}
    now = datetime.now()
    sync_year = int(body.get('year') or now.year)
    sync_month = int(body.get('month') or now.month)

    with sync_lock:
        if sync_state['is_running']:
            return jsonify({
                'status': 'busy',
                'message': 'Sinkronisasi in-the-sky.org sedang berlangsung di latar belakang. Silakan tunggu.',
                'started_at': sync_state['started_at']
            }), 429

        # Cooldown check: Hindari trigger berulang kurang dari 60 detik
        if sync_state['completed_at']:
            elapsed = time.time() - sync_state['completed_at']
            if elapsed < 60:
                return jsonify({
                    'status': 'cooldown',
                    'message': f'Data baru saja diperbarui {int(elapsed)} detik lalu. Beri jeda minimal 1 menit.',
                    'cooldown_remaining': int(60 - elapsed)
                }), 429

        sync_state['is_running'] = True
        sync_state['started_at'] = time.time()
        sync_state['last_status'] = 'running'
        sync_state['message'] = 'Sedang mengekstrak data astronomi terbaru dari in-the-sky.org...'

    def run_worker():
        global sync_state
        try:
            from scripts.scrape_playwright import run_multi_level_scraper
            # Jalankan multi-level scraper dengan Edge di background
            run_multi_level_scraper(year=sync_year, month=sync_month, max_details=25, headless=False)
            with sync_lock:
                sync_state['last_status'] = 'success'
                sync_state['message'] = 'Sinkronisasi berhasil! Data astronomi telah diperbarui.'
        except Exception as e:
            with sync_lock:
                sync_state['last_status'] = 'error'
                sync_state['message'] = f'Sinkronisasi gagal: {str(e)}'
        finally:
            with sync_lock:
                sync_state['is_running'] = False
                sync_state['completed_at'] = time.time()

    thread = threading.Thread(target=run_worker)
    thread.daemon = True
    thread.start()

    return jsonify({
        'status': 'started',
        'message': 'Sinkronisasi live dimulai di latar belakang. Anda dapat terus menggunakan aplikasi.'
    })

@observation_bp.route('/api/sync-status')
def api_sync_status():
    """Returns live status of the background scraper."""
    return jsonify({
        'status': 'success',
        'sync_state': sync_state
    })
