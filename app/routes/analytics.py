from flask import Blueprint, render_template, jsonify

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/')
def index():
    """Main Analytics and Data Visualization dashboard."""
    return render_template('analytics/index.html')

@analytics_bp.route('/api/stats')
def stats():
    """Returns analytics data for charts (clustering, weather regression trends, sentiments)."""
    return jsonify({
        'status': 'success',
        'metrics': {
            'total_events_tracked': 0,
            'weather_records_processed': 0,
            'sentiment_samples': 0
        }
    })
