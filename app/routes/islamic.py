from flask import Blueprint, render_template, request, jsonify

islamic_bp = Blueprint('islamic', __name__)

@islamic_bp.route('/')
def index():
    """Main Islamic Astronomy & Timekeeping view."""
    return render_template('islamic/index.html')

@islamic_bp.route('/api/prayer-times', methods=['GET', 'POST'])
def prayer_times():
    """Endpoint for prayer times calculation based on coordinate and date."""
    lat = request.args.get('lat', -6.2088, type=float)
    lon = request.args.get('lon', 106.8456, type=float)
    return jsonify({
        'status': 'success',
        'message': 'Prayer calculation ready for ported falak logic.',
        'coords': {'lat': lat, 'lon': lon}
    })

@islamic_bp.route('/api/rasydulqiblat', methods=['GET'])
def rasydulqiblat():
    """Endpoint for Rasydulqiblat calculations (annual and daily)."""
    return jsonify({
        'status': 'success',
        'annual_events': [
            {'date': '27-28 Mei', 'time_utc': '09:18 UTC', 'time_wib': '16:18 WIB'},
            {'date': '15-16 Juli', 'time_utc': '09:27 UTC', 'time_wib': '16:27 WIB'}
        ],
        'note': 'Daily rashdulqiblah calculation to be powered by ported falak module.'
    })
