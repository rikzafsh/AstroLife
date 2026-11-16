import threading
import time
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from app.services.scraper_service import scrape_in_the_sky_events
from app.services.weather_service import get_weather_forecast, calculate_observation_feasibility

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

@observation_bp.route('/api/feasibility', methods=['POST'])
def api_feasibility():
    """Evaluate observation feasibility given lat, lon, event difficulty, and type."""
    data = request.get_json() or {}
    lat = data.get('lat', -6.2088)
    lon = data.get('lon', 106.8456)
    difficulty = data.get('difficulty', 'naked_eye')
    event_type = data.get('event_type', 'General')
    
    weather = get_weather_forecast(lat, lon)
    score = calculate_observation_feasibility(weather, difficulty=difficulty, event_type=event_type)
    
    return jsonify({
        'status': 'success',
        'weather': weather,
        'feasibility': score
    })

@observation_bp.route('/api/sync', methods=['POST'])
def api_sync():
    """Triggers background scraping from in-the-sky.org without freezing the web app."""
    global sync_state

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
            run_multi_level_scraper(year=2026, month=11, max_details=25, headless=False)
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
