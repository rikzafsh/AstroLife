"""
Generator katalog event astronomi.

    python -m catalog.generate 2026 2027                 # menulis data/catalog/events.json
    python -m catalog.generate 2026 2026 --force         # abaikan cache bulanan
    $env:ASTROLIFE_ENGINE = "skyfield"                   # PowerShell: pakai Skyfield + DE440s (disarankan untuk rilis)

Cache per bulan disimpan di data/catalog/cache/ agar proses panjang dapat dilanjutkan. Katalog bersifat GLOBAL
(geosentris); keterlihatan dihitung per lokasi saat halaman dibuka (catalog/visibility.py).
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from catalog import events as C
from prototype import find_events as F
from prototype.engine import E, NAME as ENGINE_KEY

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / 'data' / 'catalog'


def _month_events(year: int, month: int, cache_dir: Path, force: bool, log) -> list:
    cache = cache_dir / f'{ENGINE_KEY}_{year}-{month:02d}.json'
    if cache.exists() and not force:
        return json.loads(cache.read_text(encoding='utf-8'))
    t0 = time.time()
    nxt = (year + (month == 12), 1 if month == 12 else month + 1)
    raw = F.find_window(F.wib_to_jd(year, month, 1), F.wib_to_jd(nxt[0], nxt[1], 1), include_local=False)
    for r in raw:                                           # tuple -> list agar bisa disimpan sebagai JSON
        r['bodies'] = list(r['bodies'])
    cache.write_text(json.dumps(raw), encoding='utf-8')
    log(f'  {year}-{month:02d}: {len(raw)} event mentah ({time.time() - t0:.0f} dtk)')
    return raw


def generate(y0: int, y1: int, out: Path = None, force: bool = False, log=print) -> dict:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    cache_dir = CATALOG_DIR / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = Path(out) if out else CATALOG_DIR / 'events.json'
    if ENGINE_KEY != 'skyfield':
        log('[PERINGATAN] Mesin sementara (ephem_lite): galat planet ~2 menit busur. Untuk rilis jalankan dengan ASTROLIFE_ENGINE=skyfield.')
    raw = []
    for y in range(y0, y1 + 1):
        log(f'Tahun {y}')
        for m in range(1, 13):
            raw += _month_events(y, m, cache_dir, force, log)
        t0, t1 = F.wib_to_jd(y, 1, 1), F.wib_to_jd(y + 1, 1, 1)
        raw += C.lunar_eclipses(t0, t1) + C.solar_eclipses(t0, t1) + C.meteor_showers(y)
    events = C.normalize(raw)
    by_cat = {}
    for e in events:
        by_cat[e['category']] = by_cat.get(e['category'], 0) + 1
    doc = {'meta': {'engine': E.NAME, 'engine_key': ENGINE_KEY, 'dari_tahun': y0, 'sampai_tahun': y1,
                    'dibuat': datetime.now().isoformat(timespec='seconds'), 'jumlah': len(events), 'per_kategori': by_cat,
                    'catatan': 'Katalog global (geosentris). Waktu dalam UTC. Keterlihatan dihitung per lokasi saat dibuka.'},
           'events': events}
    tmp = out.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(out)
    log(f'[SUKSES] {len(events)} event -> {out}  {by_cat}')
    return doc


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dari', type=int)
    ap.add_argument('sampai', type=int)
    ap.add_argument('--out', default=None)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    if a.sampai < a.dari:
        sys.exit('Tahun akhir harus >= tahun awal.')
    generate(a.dari, a.sampai, a.out, a.force)
