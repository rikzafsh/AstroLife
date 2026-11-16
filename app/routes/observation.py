from flask import Blueprint, render_template, request, jsonify
from app.services.scraper_service import scrape_in_the_sky_events
from app.services.weather_service import get_weather_forecast, calculate_observation_feasibility

observation_bp = Blueprint('observation', __name__)

@observation_bp.route('/')
def index():
    """Main observation planner dashboard."""
    return render_template('observation/index.html')

@observation_bp.route('/api/events')
def api_events():
    """Fetch scraped astronomical events (supports year/month params)."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    events = scrape_in_the_sky_events(year=year, month=month)
    return jsonify({'status': 'success', 'events': events})

@observation_bp.route('/api/feasibility', methods=['POST'])
def api_feasibility():
    """Evaluate observation feasibility given lat, lon, and event time."""
    data = request.get_json() or {}
    lat = data.get('lat', -6.2088) # Default: Jakarta
    lon = data.get('lon', 106.8456)
    
    weather = get_weather_forecast(lat, lon)
    score = calculate_observation_feasibility(weather)
    
    return jsonify({
        'status': 'success',
        'weather': weather,
        'feasibility': score
    })
