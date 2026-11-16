"""
Observation Planner Service
===========================
Menggabungkan fenomena astronomi (scraper_service) + prakiraan cuaca (weather_service)
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
from app.services.scraper_service import scrape_in_the_sky_events
from app.services.weather_service import get_weather_at

WIB_OFFSET = timedelta(hours=7)
INSTRUMENT_RANK = {'naked_eye': 0, 'binoculars': 1, 'telescope': 2}
INSTRUMENT_LABEL = {'naked_eye': 'Mata Telanjang', 'binoculars': 'Binokular', 'telescope': 'Teleskop'}


def wib_to_utc(iso_wib: str) -> datetime:
    return datetime.strptime(iso_wib, '%Y-%m-%dT%H:%M') - WIB_OFFSET


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
    if not weather.get('available'):
        return {
            'score': None, 'status': 'Data cuaca tidak tersedia', 'color': 'slate',
            'recommendation': weather.get('reason', 'Prakiraan tidak tersedia.'),
            'equipment_considered': difficulty, 'confidence': '-', 'breakdown': [], 'reasons': [],
        }

    meteor = 'meteor' in event_type.lower()
    if difficulty == 'telescope':
        cloud_w, hum_w = 0.65, 0.25
    elif meteor:
        cloud_w, hum_w = 0.60, 0.15
    elif difficulty == 'binoculars':
        cloud_w, hum_w = 0.50, 0.20
    else:
        cloud_w, hum_w = 0.40, 0.10

    total = weather.get('cloud_cover_pct')
    total = 50.0 if total is None else float(total)
    low, mid, high = weather.get('cloud_low'), weather.get('cloud_mid'), weather.get('cloud_high')
    if None not in (low, mid, high):
        layered = 0.55 * low + 0.30 * mid + 0.15 * high
        eff_cloud = 0.5 * total + 0.5 * layered
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
# Perencana per fenomena
# ---------------------------------------------------------------------------
def evaluate_event(event: dict, lat: float, lon: float, instrument: str = None, now_utc: datetime = None) -> dict:
    """Skor untuk satu fenomena memakai alat pengguna (atau alat yang dibutuhkan fenomena)."""
    now_utc = now_utc or datetime.utcnow()
    needed = event.get('difficulty', 'naked_eye')
    use = instrument if instrument in INSTRUMENT_RANK else needed
    needs_more = INSTRUMENT_RANK[use] < INSTRUMENT_RANK.get(needed, 0)
    # Skor memakai kebutuhan fenomena: pengamat dengan alat lebih sederhana tetap dinilai sesuai target.
    scoring_diff = needed

    obs_iso = event.get('obs_time')
    if not obs_iso:
        return {'id': event['id'], 'feasibility': calculate_observation_feasibility(
            {'available': False, 'reason': 'Waktu pengamatan tidak diketahui.'}), 'weather': None}
    when = wib_to_utc(obs_iso)
    weather = get_weather_at(lat, lon, when, now_utc)
    illum = moon_illumination(when)
    malt = moon_altitude_at(when, lat, lon)
    feas = calculate_observation_feasibility(weather, scoring_diff, event.get('type', ''), illum,
                                             event.get('involves_moon', False), malt)
    return {
        'id': event['id'], 'obs_time_wib': obs_iso, 'moon_illumination_pct': round(illum * 100), 'moon_altitude_deg': round(malt),
        'needs_better_instrument': needs_more, 'required_instrument': INSTRUMENT_LABEL.get(needed, needed),
        'is_past': when < now_utc - timedelta(hours=1), 'weather': weather, 'feasibility': feas,
    }


def plan(lat: float, lon: float, instrument: str = None, year: int = None, month: int = None,
         now_utc: datetime = None, top_n: int = 3) -> dict:
    """Skor seluruh fenomena + daftar rekomendasi terbaik (hanya yang belum lewat & alatnya memadai)."""
    now_utc = now_utc or datetime.utcnow()
    events = scrape_in_the_sky_events(year=year, month=month)
    items = []
    for ev in events:
        r = evaluate_event(ev, lat, lon, instrument, now_utc)
        f = r['feasibility']
        items.append({
            'id': ev['id'], 'title': ev['title'], 'type': ev['type'], 'date': ev['date'],
            'obs_time_wib': r.get('obs_time_wib'), 'is_past': r.get('is_past', False),
            'needs_better_instrument': r.get('needs_better_instrument', False),
            'required_instrument': r.get('required_instrument'),
            'score': f['score'], 'status': f['status'], 'color': f['color'], 'confidence': f['confidence'],
            'reasons': f['reasons'][:2], 'cloud_cover_pct': (r.get('weather') or {}).get('cloud_cover_pct'),
            'weather_kind': (r.get('weather') or {}).get('kind'),
        })
    candidates = [i for i in items if i['score'] is not None and not i['is_past']
                  and not i['needs_better_instrument']]
    candidates.sort(key=lambda i: (-i['score'], i['obs_time_wib'] or ''))
    # satu rekomendasi per hari/objek serupa tidak diperlukan; ambil teratas apa adanya
    return {
        'lokasi': {'lat': lat, 'lon': lon}, 'instrument': instrument,
        'dihitung_utc': now_utc.strftime('%Y-%m-%dT%H:%M'),
        'items': items, 'top': [c['id'] for c in candidates[:top_n]],
        'weather_available': any(i['score'] is not None for i in items),
    }
