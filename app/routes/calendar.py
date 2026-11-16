from flask import Blueprint, render_template, request, jsonify

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/')
def index():
    """Main Calendar Laboratory view."""
    return render_template('calendar/index.html')

@calendar_bp.route('/api/convert', methods=['POST'])
def convert():
    """Endpoint to convert between Gregorian, Hijri, Javanese, and Jyotisa."""
    data = request.get_json() or {}
    # Placeholder: Will connect to calendar_service.py once JS module is ported
    return jsonify({
        'status': 'success',
        'message': 'Calendar conversion engine ready. Waiting for JS module integration.',
        'input': data
    })
