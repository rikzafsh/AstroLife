"""
Layanan katalog untuk halaman web: memuat events.json, menghitung keterlihatan + kelangkaan per lokasi (dengan cache),
dan menyiapkan bidang tampilan (waktu lokal, bahan tautan cuaca). Dipakai oleh halaman Katalog, Observasi, dan Beranda.
"""
import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from catalog import rarity as R
from catalog import visibility as V
from prototype.find_events import BODY_ID

SKY_LIMITS = {'kota': 4.0, 'pinggiran': 5.0, 'gelap': 6.0}
CATEGORY_LABEL = {'fase_bulan': 'Fase Bulan', 'konjungsi': 'Konjungsi', 'okultasi': 'Okultasi', 'gerhana_bulan': 'Gerhana Bulan',
                  'gerhana_matahari': 'Gerhana Matahari', 'elongasi': 'Elongasi', 'oposisi': 'Oposisi',
                  'fase_planet': 'Fase/Kecerahan Planet', 'hujan_meteor': 'Hujan Meteor'}
TIME_LABELS = [('start_utc', 'Mulai'), ('end_utc', 'Selesai')]
DETAIL_TIME_LABELS = {
    'pendekatan_terdekat_utc': 'Pendekatan terdekat', 'konjungsi_asensio_rekta_utc': 'Konjungsi (asensio rekta)',
    'umbra_mulai_utc': 'Umbra mulai', 'umbra_selesai_utc': 'Umbra selesai',
    'total_mulai_utc': 'Totalitas mulai', 'total_selesai_utc': 'Totalitas selesai',
}


def catalog_file(catalog_dir) -> Path:
    return Path(catalog_dir) / 'events.json'


def load(catalog_dir):
    """Dokumen katalog (dict) atau None bila belum dibuat. Di-cache per waktu ubah berkas."""
    path = catalog_file(catalog_dir)
    if not path.exists():
        return None
    return _read(str(path), path.stat().st_mtime)


@lru_cache(maxsize=2)
def _read(path: str, mtime: float):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=20000)
def _evaluate(ev_json: str, lat: float, lon: float, limit: float, tz: float):
    ev = json.loads(ev_json)
    vis = V.evaluate(ev, lat, lon, limit, tz)
    return vis, R.rarity(ev, vis)


def local(utc_iso: str, tz: float) -> str:
    return (datetime.strptime(utc_iso[:19], '%Y-%m-%dT%H:%M:%S') + timedelta(hours=tz)).strftime('%Y-%m-%d %H:%M')


def times_local(ev: dict, vis: dict, tz: float) -> list:
    """Semua jam yang ditampilkan di UI, SUDAH dalam waktu lokal lokasi (UI tidak menampilkan UTC)."""
    out = []
    for key, label in TIME_LABELS:
        if ev.get(key):
            out.append({'label': label + (' (jendela global)' if ev['category'] == 'okultasi' else ''), 'value': local(ev[key], tz)})
    for key, label in DETAIL_TIME_LABELS.items():
        if ev.get('details', {}).get(key):
            out.append({'label': label, 'value': local(ev['details'][key], tz)})
    le = vis.get('local_eclipse')
    if le and le.get('terlihat'):
        out.append({'label': 'Puncak gerhana di lokasi', 'value': local(le['waktu_maks_utc'], tz)})
    return out


def wx(ev: dict, vis: dict, tz: float) -> dict:
    """Bahan tautan analisis cuaca: waktu puncak & waktu terbaik (bila dapat diamati), format ISO lokal."""
    peak = local(ev['time_utc'], tz).replace(' ', 'T')
    best = local(vis['best_time_utc'], tz).replace(' ', 'T') if vis.get('observable') and vis.get('best_time_utc') else None
    return {'peak': peak, 'best': best, 'default': best or peak}


def decorate(ev: dict, lat: float, lon: float, sky: str, tz: float) -> dict:
    vis, rar = _evaluate(json.dumps(ev, sort_keys=True), round(lat, 3), round(lon, 3), SKY_LIMITS[sky], tz)
    return {**ev, 'time_local': local(ev['time_utc'], tz), 'kategori_label': CATEGORY_LABEL.get(ev['category'], ev['category']),
            'visibility': vis, 'rarity': rar, 'times_local': times_local(ev, vis, tz), 'wx': wx(ev, vis, tz)}


def coverage(doc) -> dict:
    return {'dari_tahun': doc['meta']['dari_tahun'], 'sampai_tahun': doc['meta']['sampai_tahun']} if doc else None


def covers(doc, when_utc: datetime, margin_days: int = 0) -> bool:
    """Apakah katalog mencakup `when_utc` (dan `margin_days` hari sesudahnya)?"""
    if not doc:
        return False
    m = doc['meta']
    start = datetime(m['dari_tahun'], 1, 1)
    end = datetime(m['sampai_tahun'] + 1, 1, 1)
    return start <= when_utc and when_utc + timedelta(days=margin_days) < end


def upcoming(doc, lat: float, lon: float, sky: str, tz: float, now_utc: datetime, days: int = 14,
             observable_only: bool = True, max_rank: int = 4) -> list:
    """Event mulai sekarang sampai `days` hari ke depan (waktu UTC), terurut waktu, sudah dievaluasi untuk lokasi."""
    t0, t1 = now_utc - timedelta(hours=3), now_utc + timedelta(days=days)     # 3 jam ke belakang: event yang baru/sedang berlangsung
    rank = {k: i for i, k in enumerate(V.INSTRUMENTS)}
    items = []
    for ev in doc['events']:
        t = datetime.strptime(ev['time_utc'][:19], '%Y-%m-%dT%H:%M:%S')
        end = datetime.strptime(ev['end_utc'][:19], '%Y-%m-%dT%H:%M:%S') if ev.get('end_utc') else t
        if end < t0 or t > t1:
            continue
        it = decorate(ev, lat, lon, sky, tz)
        v = it['visibility']
        if observable_only and not v['observable']:
            continue
        if v.get('instrument') and rank[v['instrument']] > max_rank:
            continue
        items.append(it)
    items.sort(key=lambda e: e['time_utc'])
    return items
