import requests
from config import Config

def get_weather_forecast(lat: float, lon: float):
    """
    Retrieves weather forecast for given latitude and longitude.
    Uses Google Weather API if configured; otherwise provides fallback to Open-Meteo / default dataset.
    """
    api_key = Config.GOOGLE_WEATHER_API_KEY

    # 1. Google Weather API integration (if API Key provided)
    if api_key:
        try:
            # Google Maps / Weather API endpoint format
            url = f"https://weather.googleapis.com/v1/currentConditions:lookup?key={api_key}&location.latitude={lat}&location.longitude={lon}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'source': 'Google Weather API',
                    'temp_c': data.get('temperature', {}).get('degrees', 27),
                    'cloud_cover_pct': data.get('cloudCover', {}).get('percentage', 30),
                    'humidity_pct': data.get('relativeHumidity', 75),
                    'precipitation_prob': data.get('precipitationProbability', {}).get('percent', 10),
                    'condition': data.get('weatherCondition', 'Cerah Berawan')
                }
        except Exception as e:
            print(f"[Warning] Google Weather API call failed, falling back: {e}")

    # 2. Fallback using Open-Meteo API (Free, no key required for testing/development)
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,cloud_cover,precipitation,visibility&timezone=auto"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json().get('current', {})
            return {
                'source': 'Open-Meteo (Development Fallback)',
                'temp_c': data.get('temperature_2m', 28),
                'cloud_cover_pct': data.get('cloud_cover', 35),
                'humidity_pct': data.get('relative_humidity_2m', 70),
                'precipitation_prob': 100 if data.get('precipitation', 0) > 0 else 5,
                'visibility_meters': data.get('visibility', 10000),
                'condition': 'Cerah' if data.get('cloud_cover', 0) < 20 else 'Berawan'
            }
    except Exception as e:
        print(f"[Warning] Open-Meteo fallback failed: {e}")

    # 3. Default offline fallback
    return {
        'source': 'Offline Mock Data',
        'temp_c': 28.5,
        'cloud_cover_pct': 30,
        'humidity_pct': 72,
        'precipitation_prob': 10,
        'visibility_meters': 10000,
        'condition': 'Cerah Berawan'
    }

def calculate_observation_feasibility(weather_data: dict) -> dict:
    """
    Computes an astronomical observation feasibility score (0 - 100)
    based on cloud cover, precipitation, humidity, and visibility.
    """
    cloud_cover = weather_data.get('cloud_cover_pct', 50)
    precipitation = weather_data.get('precipitation_prob', 0)
    humidity = weather_data.get('humidity_pct', 70)

    # Cloud cover penalty (max 50 points penalty)
    cloud_penalty = (cloud_cover / 100.0) * 50

    # Precipitation penalty (max 30 points penalty)
    rain_penalty = (precipitation / 100.0) * 30

    # High humidity penalty (max 20 points penalty for condensation/fog risk above 80%)
    humidity_penalty = max(0, (humidity - 70) / 30.0) * 20 if humidity > 70 else 0

    score = max(0, min(100, round(100 - (cloud_penalty + rain_penalty + humidity_penalty), 1)))

    if score >= 80:
        status = "Sangat Baik"
        color = "emerald"
        recommendation = "Kondisi langit sangat mendukung! Minim awan dan potensi hujan rendah. Ideal untuk pengamatan teleskop atau astrofotografi."
    elif score >= 60:
        status = "Baik"
        color = "blue"
        recommendation = "Kondisi pengamatan cukup cerah. Disarankan tetap memantau pergerakan awan lokal."
    elif score >= 40:
        status = "Cukup / Terbatas"
        color = "amber"
        recommendation = "Tutupan awan cukup tebal atau kelembapan tinggi. Pengamatan objek redup (deep-sky) mungkin terganggu."
    else:
        status = "Buruk / Tidak Layak"
        color = "rose"
        recommendation = "Risiko hujan atau tutupan awan tinggi. Tidak direkomendasikan untuk pengamatan luar ruangan."

    return {
        'score': score,
        'status': status,
        'color': color,
        'recommendation': recommendation,
        'metrics': {
            'cloud_penalty': round(cloud_penalty, 1),
            'rain_penalty': round(rain_penalty, 1),
            'humidity_penalty': round(humidity_penalty, 1)
        }
    }
