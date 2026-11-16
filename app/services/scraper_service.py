"""
Astronomy Events Scraper & Data Provider Service
Responsible for:
1. Loading raw astronomical events data from in-the-sky.org
2. Application-layer processing (categorization, equipment difficulty evaluation, display formatting)
"""

import json
import time
from datetime import datetime
from pathlib import Path
from config import Config

CACHE_DIR = Config.CACHE_DIR
DATASETS_DIR = Config.DATASETS_DIR

def determine_event_category(title: str) -> str:
    """Categorizes the event at runtime based on raw English title."""
    t = title.lower()
    if 'meteor' in t:
        return 'Hujan Meteor'
    if 'moon' in t or 'full moon' in t or 'new moon' in t or 'quarter' in t:
        return 'Fase Bulan'
    if 'eclipse' in t:
        return 'Gerhana'
    if any(k in t for k in ['conjunction', 'close approach', 'occultation', 'appulse']):
        return 'Konjungsi Planet'
    if any(p in t for p in ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'perihelion', 'aphelion', 'elongation']):
        return 'Planet'
    return 'Astronomical Event'

def determine_event_difficulty(title: str) -> tuple:
    """Evaluates equipment requirement (maxdiff) at runtime."""
    t = title.lower()
    if any(k in t for k in ['uranus', 'neptune', 'm44', 'm45', 'cluster', 'comet', 'occultation', 'regulus', 'antares', 'sigma', 'tauri']):
        return 'telescope', 'Teleskop'
    if any(k in t for k in ['conjunction', 'close approach', 'pleiades', 'hyades', 'mercury']):
        return 'binoculars', 'Binokular'
    return 'naked_eye', 'Mata Telanjang'

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
        'source': raw_item.get('source', 'in-the-sky.org')
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
