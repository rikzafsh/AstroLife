"""
Observation Planner Service
===========================
Menggabungkan event katalog (catalog.service) + prakiraan cuaca (weather_service)
menjadi skor kelayakan pengamatan 0-100 untuk lokasi, alat, dan waktu tertentu.

Faktor penalti (semuanya transparan dan dikembalikan sebagai 'breakdown'):
  awan     - tutupan awan efektif (lapisan rendah paling merusak, awan tinggi/cirrus paling ringan)
  hujan    - peluang & curah hujan
  lembap   - kelembapan tinggi (kabut tipis, lensa berembun)
  jarak    - jarak pandang rendah (haze/asap)
  bulan    - cahaya Bulan (hanya untuk target redup; diabaikan bila Bulan adalah objeknya)
  siang    - pengamatan jatuh pada siang hari
"""
import math
from datetime import datetime, timedelta

from app.services import astro_core as ac
from app.services.weather_service import fetch_hourly_forecast, get_weather_at

def moon_illumination(when_utc: datetime) -> float:
    """Fraksi cahaya Bulan 0..1 dari elongasi Bulan-Matahari (aproksimasi fase)."""
    jd = ac.jd_from_jdn(ac.to_jdn(when_utc.year, when_utc.month, when_utc.day),
                        when_utc.hour + when_utc.minute / 60.0)
    e = math.radians(ac.elongation(jd))
    return (1 - math.cos(e)) / 2.0


def moon_altitude_at(when_utc: datetime, lat: float, lon: float) -> float:
    jd = ac.jd_from_jdn(ac.to_jdn(when_utc.year, when_utc.month, when_utc.day),
                        when_utc.hour + when_utc.minute / 60.0)
    return ac.moon_altitude(jd, lat, lon)


def _status(score: float):
    if score >= 80:
        return 'Sangat Baik', 'emerald'
    if score >= 60:
        return 'Baik', 'blue'
    if score >= 40:
        return 'Cukup / Terbatas', 'amber'
    return 'Buruk / Tidak Layak', 'rose'


def _confidence(weather: dict) -> str:
    if weather['kind'] == 'climatology':
        return 'Indikatif (rata-rata historis)'
    d = weather.get('horizon_days', 0)
    return 'Tinggi' if d <= 3 else ('Sedang' if d <= 7 else 'Rendah')


def calculate_observation_feasibility(weather: dict, difficulty: str = 'naked_eye',
                                      event_type: str = 'General', moon_illum: float = None,
                                      involves_moon: bool = False, moon_alt: float = None) -> dict:
    """Skor 0-100. Bila cuaca tidak tersedia, skor = None (tidak dikarang)."""
    difficulty = 'telescope' if 'telescope' in str(difficulty) else difficulty
    if not weather.get('available'):
        return {
            'score': None, 'status': 'Data cuaca tidak tersedia', 'color': 'slate',
            'recommendation': weather.get('reason', 'Prakiraan tidak tersedia.'),
            'equipment_considered': difficulty, 'confidence': '-', 'breakdown': [], 'reasons': [],
        }

    meteor = 'meteor' in event_type.lower()
    if difficulty == 'telescope':
        cloud_w, hum_w = 0.90, 0.25
    elif meteor:
        cloud_w, hum_w = 0.85, 0.15
    elif difficulty == 'binoculars':
        cloud_w, hum_w = 0.75, 0.20
    else:
        cloud_w, hum_w = 0.65, 0.10

    total = weather.get('cloud_cover_pct')
    total = 50.0 if total is None else float(total)
    low, mid, high = weather.get('cloud_low'), weather.get('cloud_mid'), weather.get('cloud_high')
    if None not in (low, mid, high):
        layered = 0.55 * low + 0.30 * mid + 0.15 * high
        eff_cloud = 0.75 * total + 0.25 * layered
    else:
        eff_cloud = total
    p_rain = weather.get('precipitation_prob') or 0
    mm = weather.get('precipitation_mm') or 0
    hum = weather.get('humidity_pct') or 70
    vis = weather.get('visibility_m')

    pen = {
        'awan': eff_cloud / 100.0 * cloud_w * 100,
        'hujan': p_rain / 100.0 * 35 + (10 if mm >= 0.5 else 0),
        'lembap': max(0.0, (hum - 70) / 30.0) * hum_w * 100,
        'jarak': max(0.0, (15000 - vis) / 15000.0) * 20 if vis is not None else 0.0,
    }
    if moon_illum is not None and not involves_moon:
        moon_w = 0.35 if meteor else {'telescope': 0.22, 'binoculars': 0.12}.get(difficulty, 0.05)
        # Bulan di bawah ufuk tidak mengganggu; penuh bila tingginya >= 25 derajat
        up = 1.0 if moon_alt is None else max(0.0, min(1.0, moon_alt / 25.0))
        pen['bulan'] = moon_illum * moon_w * 100 * up
    h = weather.get('local_hour')
    if h is not None and 6 <= h < 17.5:
        pen['siang'] = 60.0

    score = round(max(0.0, min(100.0, 100 - sum(pen.values()))), 1)
    status, color = _status(score)

    labels = {'awan': 'Tutupan awan', 'hujan': 'Hujan', 'lembap': 'Kelembapan tinggi',
              'jarak': 'Jarak pandang rendah', 'bulan': 'Cahaya Bulan', 'siang': 'Siang hari'}
    detail = {
        'awan': f"awan efektif {eff_cloud:.0f}%", 'hujan': f"peluang hujan {p_rain:.0f}%",
        'lembap': f"kelembapan {hum:.0f}%",
        'jarak': f"jarak pandang {vis / 1000:.1f} km" if vis is not None else '',
        'bulan': f"Bulan {((moon_illum or 0) * 100):.0f}% terang"
                 + (f", tinggi {moon_alt:.0f} derajat" if moon_alt is not None else ''),
        'siang': 'langit masih terang',
    }
    breakdown = [{'faktor': k, 'label': labels[k], 'penalti': round(v, 1), 'detail': detail[k]}
                 for k, v in pen.items()]
    reasons = [f"{b['label']}: {b['detail']}" for b in sorted(breakdown, key=lambda x: -x['penalti'])
               if b['penalti'] >= 8]

    if score >= 80:
        rec = 'Langit diprakirakan sangat mendukung. Siapkan alat dan cari lokasi dengan ufuk terbuka.'
    elif score >= 60:
        rec = 'Cukup cerah. Pengamatan masih layak; pantau ulang prakiraan 1-2 jam sebelumnya.'
    elif score >= 40:
        rec = 'Kondisi terbatas. Objek redup sulit terlihat; objek terang masih berpeluang.'
    else:
        rec = 'Kurang disarankan: awan/hujan diperkirakan menghalangi pengamatan.'
    if reasons:
        rec += ' Penghambat utama: ' + '; '.join(reasons[:2]) + '.'
    if weather['kind'] == 'climatology':
        rec += ' (Di luar jangkauan prakiraan 16 hari: nilai ini rata-rata historis, bukan prakiraan.)'

    return {
        'score': score, 'status': status, 'color': color, 'recommendation': rec,
        'equipment_considered': difficulty, 'confidence': _confidence(weather),
        'breakdown': breakdown, 'reasons': reasons,
    }


# ---------------------------------------------------------------------------
# Perencana berbasis katalog
# ---------------------------------------------------------------------------
GEAR_RANK = {'naked_eye': 0, 'binoculars': 1, 'telescope': 3, 'all': 4}
FORECAST_MAX_DAYS = 15                       # prakiraan per jam Open-Meteo: 16 hari


def plan(doc: dict, lat: float, lon: float, sky: str, tz: float, instrument: str = 'all',
         now_utc: datetime = None, days: int = 14, limit: int = 12) -> dict:
    """
    Event katalog yang DAPAT DIAMATI dari lokasi dalam `days` hari ke depan, masing-masing diberi skor kelayakan cuaca
    pada WAKTU TERBAIKNYA, diurutkan dari skor tertinggi. Bila prakiraan tidak dapat diambil, skor tidak dikarang (None).
    """
    from catalog import service as S
    now_utc = now_utc or datetime.utcnow()
    days = max(1, min(int(days), FORECAST_MAX_DAYS))
    items = S.upcoming(doc, lat, lon, sky, tz, now_utc, days, observable_only=True, max_rank=GEAR_RANK.get(instrument, 4))
    forecast_ok = fetch_hourly_forecast(lat, lon) is not None if items else False
    rows = []
    for it in items:
        v = it['visibility']
        when = datetime.strptime(v['best_time_utc'][:19], '%Y-%m-%dT%H:%M:%S')
        weather = get_weather_at(lat, lon, when, now_utc) if forecast_ok else {'available': False, 'reason': 'Prakiraan cuaca tidak dapat dimuat.'}
        illum = moon_illumination(when)
        feas = calculate_observation_feasibility(weather, v['instrument'] or 'naked_eye', it['kategori_label'], illum,
                                                 'moon' in it['bodies'], v.get('moon_altitude'))
        rows.append({
            'id': it['id'], 'title': it['title'], 'category': it['category'], 'kategori_label': it['kategori_label'],
            'time_local': it['time_local'], 'best_local': it['wx']['best'], 'wx': it['wx'], 'headline': v['headline'],
            'rarity': {'tier': it['rarity']['tier'], 'label': it['rarity']['label']},
            'instrument': v['instrument'], 'instrument_label': v['instrument_label'], 'bodies': it['bodies'],
            'score': feas['score'], 'status': feas['status'], 'color': feas['color'], 'confidence': feas['confidence'],
            'reasons': feas['reasons'][:2], 'weather_kind': weather.get('kind'),
            'cloud_cover_pct': weather.get('cloud_cover_pct'), 'rain_prob': weather.get('precipitation_prob'),
        })
    tier_rank = {'common': 0, 'uncommon': 1, 'rare': 2, 'epic': 3, 'legendary': 4}
    rows.sort(key=lambda r: (r['score'] is None, -(r['score'] or 0), -tier_rank[r['rarity']['tier']], r['time_local']))
    return {'dihitung_utc': now_utc.strftime('%Y-%m-%dT%H:%M'), 'days': days, 'weather_available': forecast_ok,
            'total_observable': len(rows), 'items': rows[:limit]}
