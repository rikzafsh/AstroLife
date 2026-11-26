from datetime import datetime

from flask import Blueprint, current_app, render_template

from app.services.home_service import today_summary
from app.services.timezones import tz_from_lon, tz_label

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    loc = current_app.config['DEFAULT_LOCATION']
    tz = tz_from_lon(loc['lon'])
    return render_template('index.html', today=today_summary(datetime.utcnow(), tz), tz=tz, tz_label=tz_label(tz))


@main_bp.route('/about')
def about():
    return render_template('about.html')
