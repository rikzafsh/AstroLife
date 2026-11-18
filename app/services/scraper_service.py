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
# Toleran terhadap: huruf besar/kecil, ada/tidaknya spasi, "at" / "from", nama bulan penuh.
_TZ = r'((?-i:[A-Z]{2,5}))?'          # label zona apa pun (WIB, IST, ...), huruf kapital
_TIME_RE = re.compile(r'(\d{1,2})\s*([A-Za-z]{3})[A-Za-z]*\.?\s*(\d{4})\s*(?:at|from|@)?\s*(\d{1,2}):(\d{2})\s*' + _TZ, re.I)
_NOT_TZ = {'TO', 'AT', 'AGO', 'AWAY', 'DAYS', 'DAY', 'HOUR', 'HOURS', 'FROM'}
_END_RE = re.compile(r'\bto\s*(\d{1,2}):(\d{2})\s*' + _TZ, re.I)


_DATE_RE = re.compile(r'(\d{1,2})\s*([A-Za-z]{3})[A-Za-z]*\.?\s*(\d{4})')


def parse_event_date(text: str):
    """Tanggal saja (tanpa jam) dari teks halaman, mis. 'Sun, 08 Nov 2026'; None bila tidak terbaca."""
    m = _DATE_RE.search(text or '')
    if not m or m.group(2).title() not in _MONTHS:
        return None
    try:
        return datetime(int(m.group(3)), _MONTHS[m.group(2).title()], int(m.group(1)))
    except ValueError:
        return None


_UTC_RE = re.compile(r'\(\s*(\d{1,2}):(\d{2})\s*UTC\s*\)', re.I)
WIB_OFFSET_H = 7


def _utc_candidate(local_dt: datetime, hh: int, mm: int):
    """Tanggal UTC dari jam UTC (hh:mm) dan waktu lokal; offset zona lokal wajar: -12 s.d. +14 jam."""
    best = None
    for dd in (-1, 0, 1):
        u = datetime(local_dt.year, local_dt.month, local_dt.day, hh, mm) + timedelta(days=dd)
        diff = (local_dt - u).total_seconds() / 3600.0
        if -12 <= diff <= 14 and (best is None or abs(diff) < abs(best[1])):
            best = (u, diff)
    return best[0] if best else None


def parse_event_time(text: str):
    """
    Membaca tanggal/jam dari teks halaman in-the-sky, mis.
      'Mon, 02 Nov 2026 at 20:39 WIB'
      'Mon, 02 Nov 2026 at 01:58 IST (20:28 UTC)'          <- lokasi situs bukan Jakarta
      'TUE, 03 NOV 2026 FROM 03:45 WIB (20:45 UTC) TO 07:45 WIB (00:45 UTC)'
    Hasil: {'tz': label zona lokal situs, 'start','end','mid': WIB (naive datetime), 'utc_start': ...} atau None.
    Acuan utama = jam UTC dalam kurung (tidak bergantung pada lokasi yang dipilih situs); bila tidak ada,
    jam lokal hanya dipakai jika zonanya WIB atau UTC. Selain itu waktu tidak dapat ditentukan (None).
    """
    m = _TIME_RE.search(text or '')
    if not m or m.group(2).title() not in _MONTHS:
        return None
    local = datetime(int(m.group(3)), _MONTHS[m.group(2).title()], int(m.group(1)), int(m.group(4)), int(m.group(5)))
    tz = (m.group(6) or '').upper()
    tz = '' if tz in _NOT_TZ else tz

    u = _UTC_RE.match(text, m.end()) or _UTC_RE.search(text, m.end(), m.end() + 20)
    if u:
        utc_start = _utc_candidate(local, int(u.group(1)), int(u.group(2)))
    elif tz == 'WIB':
        utc_start = local - timedelta(hours=WIB_OFFSET_H)
    elif tz in ('UTC', 'GMT'):
        utc_start = local
    else:
        return None
    if utc_start is None:
        return None

    utc_end = None
    e = _END_RE.search(text, u.end() if u else m.end())
    if e:
        u2 = _UTC_RE.search(text, e.end(), e.end() + 25)
        if u2:
            utc_end = utc_start.replace(hour=int(u2.group(1)), minute=int(u2.group(2)))
        elif (e.group(3) or tz).upper() == tz and tz in ('WIB', 'UTC', 'GMT'):
            utc_end = utc_start.replace(hour=int(e.group(1)), minute=int(e.group(2)))
            if tz == 'WIB':
                utc_end -= timedelta(hours=WIB_OFFSET_H)
        if utc_end is not None and utc_end < utc_start:
            utc_end += timedelta(days=1)

    to_wib = lambda d: d + timedelta(hours=WIB_OFFSET_H)
    start = to_wib(utc_start)
    end = to_wib(utc_end) if utc_end else None
    return {'tz': tz, 'start': start, 'end': end, 'mid': start + (end - start) / 2 if end else start,
            'utc_start': utc_start}


def _hhmm(text: str):
    m = _HHMM_RE.search(text or '')
    return (int(m.group(1)) + int(m.group(2)) / 60.0) if m else None


_TRANSIT_RE = re.compile(r'highest point in the sky at\s*(\d{1,2}):(\d{2})', re.I)
_PREDAWN_H, _EVENING_H = 4.25, 19.0
OBS_BASIS_LABEL = {
    'peak': 'Jam puncak dari in-the-sky.org (WIB).',
    'transit': 'Jam kulminasi (titik tertinggi) dari in-the-sky.org.',
    'predawn': 'Puncak terjadi saat langit terang; dinilai pada langit dini hari terdekat (04:15 WIB).',
    'evening': 'Puncak terjadi saat langit terang; dinilai pada malam terdekat (19:00 WIB).',
    'assumed_meteor': 'ASUMSI: jam puncak tidak dirilis; hujan meteor dinilai pukul 02:00 WIB.',
    'assumed_morning': 'ASUMSI: jam puncak tidak dirilis; penampakan pagi dinilai pukul 04:15 WIB.',
    'assumed_evening': 'ASUMSI: jam puncak tidak dirilis; dinilai pukul 20:00 WIB.',
}


def _nearest(base: datetime, hour: float, peak_dt: datetime) -> datetime:
    """Waktu pada jam `hour` (di hari base -1/0/+1) yang paling dekat dengan puncak."""
    cands = [base + timedelta(days=d, hours=hour) for d in (-1, 0, 1)]
    return min(cands, key=lambda c: abs((c - peak_dt).total_seconds()))


def compute_observation_time(raw: dict, title: str, category: str, loc_ok: bool = True) -> dict:
    """
    Menentukan KAPAN cuaca dinilai untuk sebuah fenomena (WIB, naive). Urutan prioritas:
      1. Puncak malam hari (17:30-05:30) dan berzona WIB      -> jam puncak.
      2. Puncak saat langit terang                            -> malam/dini hari terdekat, ditentukan
         dari teks sumber: penampakan pagi ("morning", "at sunrise", ada jam terbit) -> 04:15, selain itu 19:00.
      3. Tanpa jam puncak: kulminasi dari teks sumber ("highest point in the sky at HH:MM"),
         hujan meteor 02:00, penampakan pagi 04:15, selain itu 20:00. Tiga yang terakhir adalah ASUMSI.
    Hasil memuat 'obs_basis' dan 'obs_assumed' agar UI dapat menandainya.
    """
    date_str = raw.get('date', '')
    text = ' '.join([title, raw.get('description', ''), raw.get('visibility_summary', '')]).lower()
    morning = ('morning' in text or 'at sunrise' in text or 'before sunrise' in text) and 'evening' not in text
    morning = morning or bool(raw.get('rising_time') and raw.get('fading_time'))

    parsed = parse_event_time(raw.get('peak_event_time', '') or '')
    peak_dt = parsed['mid'] if parsed else None   # sudah dalam WIB (dikonversi dari UTC)
    try:
        if peak_dt:
            base = datetime(peak_dt.year, peak_dt.month, peak_dt.day)
        else:
            try:
                base = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:                      # mis. '2026-11' (hari tidak terbaca dari ID): coba teks halaman
                base = parse_event_date(raw.get('peak_event_time', '') or '')
                if base is None:
                    raise ValueError('tanggal tidak terbaca')
    except ValueError:
        return {'obs_time': None, 'peak_time': None, 'obs_basis': None, 'obs_assumed': False,
                'obs_note': 'Tanggal fenomena tidak dapat dibaca.', 'date_wib': None}

    if peak_dt:
        h = peak_dt.hour + peak_dt.minute / 60.0
        if h >= 17.5 or h < 5.5:
            obs, basis = peak_dt, 'peak'
        elif morning:
            obs, basis = _nearest(base, _PREDAWN_H, peak_dt), 'predawn'
        else:
            obs, basis = _nearest(base, _EVENING_H, peak_dt), 'evening'
    else:
        # Jam kulminasi dari teks situs adalah jam LOKAL situs: hanya dipakai bila lokasinya Jakarta (WIB).
        t = _TRANSIT_RE.search(raw.get('visibility_summary', '') or '') if loc_ok else None
        if t:
            obs, basis = base + timedelta(hours=int(t.group(1)), minutes=int(t.group(2))), 'transit'
        elif category == 'Hujan Meteor':
            obs, basis = base + timedelta(hours=2), 'assumed_meteor'
        elif morning:
            obs, basis = base + timedelta(hours=_PREDAWN_H), 'assumed_morning'
        else:
            obs, basis = base + timedelta(hours=20), 'assumed_evening'

    return {
        'obs_time': obs.strftime('%Y-%m-%dT%H:%M'),
        'peak_time': peak_dt.strftime('%Y-%m-%dT%H:%M') if peak_dt else None,
        'date_wib': (peak_dt or base).strftime('%Y-%m-%d'),
        'obs_basis': basis,
        'obs_assumed': basis.startswith('assumed'),
        'obs_note': OBS_BASIS_LABEL[basis],
    }


def _site_location_ok(raw: dict) -> bool:
    """Data lokasi-spesifik (jam terbit, ketinggian, arah, jam hilang/muncul) valid untuk Jakarta hanya bila
    situs saat itu memakai zona WIB. Rekaman lama tanpa label zona dianggap sah."""
    tz = (raw.get('source_tz') or '').upper()
    if not tz:
        p = _TIME_RE.search(raw.get('peak_event_time', '') or '')
        tz = (p.group(6) or '').upper() if p else ''
        tz = '' if tz in _NOT_TZ else tz
    return tz in ('', 'WIB')


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
    diff_source = 'in-the-sky.org' if (diff_key and diff_label) else 'perkiraan dari judul'
    if not diff_key or not diff_label:
        diff_key, diff_label = determine_event_difficulty(title)

    # Waktu & Posisi Ilmiah Riil (jika ada hasil deep scraping)
    rising_time = raw_item.get('rising_time')
    fading_time = raw_item.get('fading_time')
    altitude = raw_item.get('altitude', '')
    azimuth = raw_item.get('azimuth_direction', '')
    constellation = raw_item.get('constellation', '')
    loc_ok = _site_location_ok(raw_item)
    if not loc_ok:       # data situs untuk lokasi LAIN (bukan Jakarta): jangan ditampilkan sebagai data Jakarta
        rising_time = fading_time = None
        altitude = azimuth = ''
    if constellation and not constellation.startswith('Rasi '):
        constellation = 'Rasi ' + constellation
    
    if rising_time:
        time_display = f"Terbit {rising_time}" + (f" • Fajar {fading_time}" if fading_time else "")
    else:
        time_display = raw_item.get('time') or 'Jam terbit tidak dirilis sumber'

    if azimuth or altitude:
        sky_pos = {
            'direction': azimuth or 'Tidak dirilis',
            'altitude': altitude or 'Tidak dirilis',
            'constellation': constellation or 'Tidak dirilis'
        }
    else:
        sky_pos = {'direction': 'Tidak dirilis', 'altitude': 'Tidak dirilis',
                   'constellation': constellation or 'Tidak dirilis'}

    description = (raw_item.get('visibility_summary') if loc_ok else '') or raw_item.get('description') or 'Deskripsi tidak tersedia dari sumber.'

    # Adanya jam terbit & fajar (objek terlihat dini hari) bersifat kualitatif dan tetap sah walau lokasi situs
    # bukan Jakarta; yang dibatasi hanya jam kulminasi yang bergantung zona (lihat compute_observation_time).
    timing = compute_observation_time(raw_item, title, cat, loc_ok)

    return {
        'id': raw_item.get('id', ''),
        'date': raw_item.get('date', ''),
        'title': title,
        'type': cat,
        'difficulty': 'telescope' if 'telescope' in str(diff_key) else diff_key,   # keluarga alat (filter & ikon UI)
        'difficulty_detail': diff_key,                                       # kunci rinci dari sumber

        'difficulty_label': diff_label,
        'difficulty_alt': raw_item.get('difficulty_alt', ''),
        'difficulty_source': diff_source,
        'detail_failed': bool(raw_item.get('detail_failed')),
        'location_ok': loc_ok,
        'location_note': '' if loc_ok else 'Jam terbit, ketinggian, dan arah dari sumber berasal dari lokasi selain Jakarta, sehingga tidak ditampilkan.',
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
