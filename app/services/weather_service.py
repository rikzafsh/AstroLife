"""
Weather Service
===============
Prakiraan cuaca untuk perencanaan pengamatan, memakai Open-Meteo (gratis, tanpa API key):

1. PRAKIRAAN per jam (maks. 16 hari ke depan): tutupan awan total + lapisan rendah/menengah/tinggi,
   kelembapan, peluang hujan, curah hujan, jarak pandang, suhu.
2. KLIMATOLOGI (cadangan untuk tanggal di luar jangkauan prakiraan): rata-rata jam & tanggal yang sama
   pada beberapa tahun sebelumnya (arsip ERA5 Open-Meteo). Sifatnya indikatif, bukan prakiraan.
3. TIDAK TERSEDIA: bila keduanya gagal. Sistem TIDAK memalsukan data; skor kelayakan tidak dihitung.

Waktu masukan: datetime UTC (naive). Waktu lokal lokasi diambil dari utc_offset_seconds respons.
"""
import logging
import time
from datetime import datetime, timedelta, date

import requests

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'
HOURLY_VARS = ('temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,'
               'cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,visibility')
FORECAST_DAYS = 16
CACHE_TTL = 3600
TIMEOUT = 8

log = logging.getLogger(__name__)
_cache = {}


def _cached(key, loader):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    value = loader()
    if value is not None:                 # kegagalan tidak disimpan agar bisa dicoba lagi
        _cache[key] = (time.time(), value)
    return value


def _loc_key(lat, lon):
    return round(lat, 1), round(lon, 1)   # ~11 km: cukup untuk cuaca, hemat panggilan API


# ---------------------------------------------------------------------------
# Pengambilan data
# ---------------------------------------------------------------------------
def fetch_hourly_forecast(lat: float, lon: float):
    """Dict {'offset': detik, 'hours': {'YYYY-MM-DDTHH:00': {...}}} atau None."""
    def load():
        try:
            r = requests.get(FORECAST_URL, params={
                'latitude': lat, 'longitude': lon, 'hourly': HOURLY_VARS,
                'forecast_days': FORECAST_DAYS, 'past_days': 1, 'timezone': 'auto'}, timeout=TIMEOUT)
            r.raise_for_status()
            return parse_hourly(r.json())
        except Exception as e:
            log.warning('Open-Meteo forecast gagal: %s', e)
            return None
    return _cached(('fc',) + _loc_key(lat, lon), load)


def parse_hourly(payload: dict):
    """Respons Open-Meteo -> {'offset': detik, 'hours': {'YYYY-MM-DDTHH:00': {...}}}; None bila tidak ada data."""
    h = payload.get('hourly') or {}
    times = h.get('time') or []
    if not times:
        return None

    def nilai(nama: str, i: int):
        """Nilai variabel `nama` pada jam ke-i; None bila variabel/entri tidak ada (Open-Meteo kadang memotong larik)."""
        arr = h.get(nama)
        return arr[i] if arr and i < len(arr) else None

    hours = {}
    for i, t in enumerate(times):
        hours[t] = {
            'temp_c': nilai('temperature_2m', i), 'humidity_pct': nilai('relative_humidity_2m', i),
            'precipitation_prob': nilai('precipitation_probability', i), 'precipitation_mm': nilai('precipitation', i),
            'cloud_cover_pct': nilai('cloud_cover', i), 'cloud_low': nilai('cloud_cover_low', i),
            'cloud_mid': nilai('cloud_cover_mid', i), 'cloud_high': nilai('cloud_cover_high', i),
            'visibility_m': nilai('visibility', i),
        }
    return {'offset': int(payload.get('utc_offset_seconds', 0)), 'hours': hours}


def fetch_climatology(lat: float, lon: float, month: int, day: int, local_hour: int, years: int = 3):
    """Rata-rata historis (+-7 hari, jam yang sama) dari arsip; None bila gagal."""
    def load():
        samples = []
        offset = 0
        this_year = date.today().year
        for y in range(this_year - years, this_year):
            try:
                c = datetime(y, month, min(day, 28))
                r = requests.get(ARCHIVE_URL, params={
                    'latitude': lat, 'longitude': lon,
                    'start_date': (c - timedelta(days=7)).strftime('%Y-%m-%d'),
                    'end_date': (c + timedelta(days=7)).strftime('%Y-%m-%d'),
                    'hourly': 'temperature_2m,relative_humidity_2m,precipitation,cloud_cover',
                    'timezone': 'auto'}, timeout=TIMEOUT + 4)
                r.raise_for_status()
                p = r.json()
                offset = int(p.get('utc_offset_seconds', 0))
                hr = p['hourly']
                for i, t in enumerate(hr['time']):
                    if int(t[11:13]) == local_hour:
                        samples.append((hr['cloud_cover'][i], hr['relative_humidity_2m'][i],
                                        hr['precipitation'][i], hr['temperature_2m'][i]))
            except Exception as e:
                log.warning('Arsip cuaca %s gagal: %s', y, e)
        samples = [s for s in samples if None not in s]
        if len(samples) < 5:
            return None
        n = len(samples)
        return {
            'offset': offset, 'n': n,
            'cloud_cover_pct': sum(s[0] for s in samples) / n,
            'humidity_pct': sum(s[1] for s in samples) / n,
            'precipitation_prob': 100.0 * sum(1 for s in samples if s[2] >= 0.1) / n,
            'temp_c': sum(s[3] for s in samples) / n,
        }
    return _cached(('cl', month, day, local_hour) + _loc_key(lat, lon), load)


# ---------------------------------------------------------------------------
# Antarmuka utama
# ---------------------------------------------------------------------------
def _condition_label(cloud, rain_prob):
    if rain_prob is not None and rain_prob >= 60:
        return 'Hujan'
    if cloud is None:
        return 'Tidak diketahui'
    if cloud < 20:
        return 'Cerah'
    if cloud < 50:
        return 'Cerah Berawan'
    if cloud < 80:
        return 'Berawan'
    return 'Mendung'


def unavailable(reason: str) -> dict:
    return {'available': False, 'kind': 'unavailable', 'source': 'Tidak tersedia', 'reason': reason}


def get_weather_at(lat: float, lon: float, when_utc: datetime, now_utc: datetime = None) -> dict:
    """Cuaca di lokasi pada waktu when_utc (datetime UTC naive)."""
    now_utc = now_utc or datetime.utcnow()
    if when_utc < now_utc - timedelta(hours=1):
        return unavailable('Waktu pengamatan sudah lewat.')
    horizon_days = (when_utc - now_utc).total_seconds() / 86400.0

    fc = fetch_hourly_forecast(lat, lon)
    if fc and horizon_days <= FORECAST_DAYS - 0.5:
        local = when_utc + timedelta(seconds=fc['offset'])
        key = local.replace(minute=0, second=0, microsecond=0)
        # pilih jam terdekat (bulatkan menit >=30 ke jam berikutnya)
        if local.minute >= 30:
            key += timedelta(hours=1)
        row = fc['hours'].get(key.strftime('%Y-%m-%dT%H:00'))
        if row and row['cloud_cover_pct'] is not None:
            window = []
            for dh in range(-3, 4):
                k = (key + timedelta(hours=dh)).strftime('%Y-%m-%dT%H:00')
                if k in fc['hours']:
                    window.append({'jam': k[11:16], 'awan': fc['hours'][k]['cloud_cover_pct'],
                                   'hujan': fc['hours'][k]['precipitation_prob'], 'sekarang': dh == 0})
            return {
                'available': True, 'kind': 'forecast', 'source': 'Open-Meteo (prakiraan per jam)',
                'horizon_days': round(horizon_days, 1),
                'valid_local': key.strftime('%Y-%m-%d %H:%M'),
                'local_hour': key.hour + key.minute / 60.0,
                **row,
                'condition': _condition_label(row['cloud_cover_pct'], row['precipitation_prob']),
                'window': window,
            }

    # Cadangan: klimatologi
    offset_guess = int(round(lon / 15.0)) * 3600 if not fc else fc['offset']
    local = when_utc + timedelta(seconds=offset_guess)
    cl = fetch_climatology(lat, lon, local.month, local.day, local.hour)
    if cl:
        return {
            'available': True, 'kind': 'climatology',
            'source': f"Klimatologi Open-Meteo (rata-rata {cl['n']} sampel, bukan prakiraan)",
            'horizon_days': round(horizon_days, 1),
            'valid_local': local.strftime('%Y-%m-%d %H:%M'), 'local_hour': local.hour,
            'temp_c': round(cl['temp_c'], 1), 'humidity_pct': round(cl['humidity_pct']),
            'cloud_cover_pct': round(cl['cloud_cover_pct']), 'cloud_low': None, 'cloud_mid': None,
            'cloud_high': None, 'precipitation_prob': round(cl['precipitation_prob']),
            'precipitation_mm': None, 'visibility_m': None,
            'condition': _condition_label(cl['cloud_cover_pct'], cl['precipitation_prob']),
            'window': [],
        }
    return unavailable('Layanan cuaca tidak dapat dihubungi dan tidak ada data cadangan.')
