"""
Astronomy Events Scraper & Data Provider Service
Responsible for:
1. Loading raw astronomical events data from in-the-sky.org
2. Application-layer processing (categorization, equipment difficulty evaluation, display formatting)
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from config import Config

CACHE_DIR = Config.CACHE_DIR
DATASETS_DIR = Config.DATASETS_DIR

def determine_event_category(title: str) -> str:
    """Categorizes the event at runtime based on raw English title.
    Urutan penting: gerhana & konjungsi dicek SEBELUM kata 'moon', karena judul seperti
    'Close approach of the Moon and Mars' adalah konjungsi, bukan fase Bulan."""
    t = title.lower()
    if 'eclipse' in t:
        return 'Gerhana'
    if 'meteor' in t:
        return 'Hujan Meteor'
    if any(k in t for k in ['conjunction', 'close approach', 'occultation', 'appulse']):
        return 'Konjungsi Planet'
    if any(k in t for k in ['full moon', 'new moon', 'quarter', 'moon at']):
        return 'Fase Bulan'
    if any(p in t for p in ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'perihelion', 'aphelion', 'elongation', 'dichotomy']):
        return 'Planet'
    if any(k in t for k in ['pleiades', 'hyades', 'cluster', 'well placed']):
        return 'Gugus Bintang'
    return 'Astronomical Event'


def determine_event_difficulty(title: str) -> tuple:
    """Evaluates equipment requirement (maxdiff) at runtime."""
    t = title.lower()
    if any(k in t for k in ['uranus', 'neptune', 'm44', 'm45', 'cluster', 'comet', 'occultation', 'regulus', 'antares', 'sigma', 'tauri']):
        return 'telescope', 'Teleskop'
    if any(k in t for k in ['conjunction', 'close approach', 'pleiades', 'hyades', 'mercury']):
        return 'binoculars', 'Binokular'
    return 'naked_eye', 'Mata Telanjang'


_MONTHS = {m: i + 1 for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}
_PEAK_RE = re.compile(r'(\d{1,2}) ([A-Z][a-z]{2}) (\d{4}) at (\d{1,2}):(\d{2}) WIB')
_HHMM_RE = re.compile(r'(\d{1,2}):(\d{2})')


def _hhmm(text: str):
    m = _HHMM_RE.search(text or '')
    return (int(m.group(1)) + int(m.group(2)) / 60.0) if m else None


def compute_observation_time(raw: dict, title: str, category: str) -> dict:
    """
    Menentukan KAPAN fenomena paling layak dinilai cuacanya (waktu WIB, naive datetime).
    - Puncak bermalam hari (17:30-05:30)  -> pakai waktu puncak.
    - Puncak siang hari + objek terbit dini hari (ada rising/fading) -> 1 jam sebelum fajar.
    - Puncak siang hari lain -> 19:00 pada tanggal tersebut (malam terdekat).
    - Tanpa jam puncak: hujan meteor -> 02:00; lainnya -> 20:00.
    """
    date_str = raw.get('date', '')
    peak = _PEAK_RE.search(raw.get('peak_event_time', '') or '')
    base = None
    if peak:
        base = datetime(int(peak.group(3)), _MONTHS[peak.group(2)], int(peak.group(1)))
        h = int(peak.group(4)) + int(peak.group(5)) / 60.0
    else:
        try:
            base = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return {'obs_time': None, 'peak_time': None, 'obs_note': ''}
        h = None

    note = ''
    if h is not None:
        peak_dt = base + timedelta(hours=h)
        if h >= 17.5 or h < 5.5:
            obs = peak_dt
        else:
            fade = _hhmm(raw.get('fading_time', ''))
            if raw.get('rising_time') and fade:
                obs = base + timedelta(hours=max(fade - 1.0, 0))
                note = 'Puncak terjadi setelah fajar (langit sudah terang); dinilai pada langit dini hari sebelum fajar.'
            else:
                obs = base + timedelta(hours=19)
                note = 'Puncak terjadi pada siang hari; dinilai pada malam terdekat.'
        peak_iso = peak_dt.strftime('%Y-%m-%dT%H:%M')
    else:
        peak_iso = None
        if category == 'Hujan Meteor':
            obs = base + timedelta(hours=2)
            note = 'Hujan meteor paling aktif setelah tengah malam hingga fajar.'
        else:
            obs = base + timedelta(hours=20)
            note = 'Jam puncak tidak dirilis; dinilai pada pukul 20:00 WIB.'
    return {'obs_time': obs.strftime('%Y-%m-%dT%H:%M'), 'peak_time': peak_iso, 'obs_note': note}


def enrich_raw_event(raw_item: dict) -> dict:
    """
    Enriches a raw event item for application rendering.
    If the event already contains scraped detail attributes (rising_time, altitude, etc.),
    they are preserved directly!
    """
    title = raw_item.get('title', '')
    cat = determine_event_category(title)
    
    # Gunakan difficulty asli jika sudah diekstrak dari maxdiff / levelX_icon
    diff_key = raw_item.get('difficulty_key') or raw_item.get('difficulty')
    diff_label = raw_item.get('difficulty_label')
    if not diff_key or not diff_label:
        diff_key, diff_label = determine_event_difficulty(title)

    # Waktu & Posisi Ilmiah Riil (jika ada hasil deep scraping)
    rising_time = raw_item.get('rising_time')
    fading_time = raw_item.get('fading_time')
    altitude = raw_item.get('altitude', '')
    azimuth = raw_item.get('azimuth_direction', '')
    constellation = raw_item.get('constellation', '')
    
    if rising_time:
        time_display = f"Terbit {rising_time}" + (f" • Fajar {fading_time}" if fading_time else "")
    else:
        time_display = raw_item.get('time', 'Malam hari')

    if azimuth or altitude:
        sky_pos = {
            'direction': azimuth or 'Langit Malam',
            'altitude': altitude or 'Di atas ufuk',
            'constellation': constellation or 'Jalur Ekliptika'
        }
    else:
        sky_pos = raw_item.get('sky_position', {
            'direction': 'Langit Malam',
            'altitude': 'Di atas cakrawala',
            'constellation': constellation or 'Sesuai peta bintang'
        })

    description = raw_item.get('visibility_summary') or raw_item.get('description') or f"Astronomical event: {title}."

    timing = compute_observation_time(raw_item, title, cat)

    return {
        'id': raw_item.get('id', ''),
        'date': raw_item.get('date', ''),
        'title': title,
        'type': cat,
        'difficulty': diff_key,
        'difficulty_label': diff_label,
        'difficulty_alt': raw_item.get('difficulty_alt', ''),
        'time': time_display,
        'sky_position': sky_pos,
        'objects': raw_item.get('objects', []),
        'description': description,
        'link': raw_item.get('url') or raw_item.get('link', ''),
        'source': raw_item.get('source', 'in-the-sky.org'),
        'involves_moon': 'moon' in title.lower(),
        **timing,
    }

def scrape_in_the_sky_events(year: int = None, month: int = None, force_refresh: bool = False):
    """
    Reads pure raw data and returns dynamically enriched events for the UI.
    """
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    raw_file = DATASETS_DIR / "astronomy_events.json"
    if raw_file.exists():
        try:
            with open(raw_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                # Filter by year and month if needed
                filtered = [e for e in raw_data if e.get('date', '').startswith(f"{year}-{month:02d}")]
                target_list = filtered if filtered else raw_data
                return [enrich_raw_event(e) for e in target_list]
        except Exception as e:
            print(f"[Error] Failed reading raw dataset: {e}")

    return []
