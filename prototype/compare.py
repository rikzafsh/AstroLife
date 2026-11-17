"""
Bandingkan hasil hitungan (find_events) dengan event hasil scraping in-the-sky.org.
Jalankan:  python -m prototype.compare [path_json] [tahun] [bulan]
Semua waktu dalam WIB. Waktu sumber dibaca dengan parse_event_time (toleran terhadap format).
"""
import json
import re
import statistics as st
import sys
from datetime import datetime, timedelta
from pathlib import Path

from app.services.scraper_service import parse_event_time
from prototype import find_events as F
from prototype.engine import E

KNOWN = set(F.BODY_ID) - {'sun'}


def classify(title: str):
    """Judul sumber -> (kind, frozenset(bodies)) atau None bila belum dicakup."""
    t = title.strip().lower()
    simple = {'moon at first quarter': 'first_quarter', 'moon at last quarter': 'last_quarter',
              'full moon': 'full_moon', 'new moon': 'new_moon'}
    if t in simple:
        return simple[t], frozenset(['moon'])
    m = re.match(r'lunar occultation of (.+)$', t)
    if m:
        name = m.group(1).strip().replace(' ', '_')
        return ('occ_window', frozenset(['moon', name])) if name in KNOWN else None
    m = re.match(r'(conjunction|close approach) of (?:the )?(\w+) and (?:the )?(\w+)$', t)
    if m and m.group(2) in KNOWN and m.group(3) in KNOWN:
        return ('conj_ra' if m.group(1) == 'conjunction' else 'close'), frozenset([m.group(2), m.group(3)])
    m = re.match(r'(\w+) at opposition$', t)
    if m and m.group(1) in KNOWN:
        return 'opposition', frozenset([m.group(1)])
    m = re.match(r'(mercury|venus) at (dichotomy|greatest brightness|greatest elongation (east|west))$', t)
    if m:
        k = {'dichotomy': 'dichotomy', 'greatest brightness': 'greatest_brightness'}.get(m.group(2))
        return (k or 'greatest_elongation_' + m.group(3)), frozenset([m.group(1)])
    return None


def _clock(text, near: datetime):
    """'04:39 (WIB)' -> datetime pada hari terdekat dengan `near` (menangani lintas tengah malam)."""
    m = re.match(r'\s*(\d{1,2}):(\d{2})\s*(?:\((\w+)\))?', text or '')
    if not m or (m.group(3) and m.group(3).upper() != 'WIB'):
        return None
    base = datetime(near.year, near.month, near.day, int(m.group(1)), int(m.group(2)))
    return min((base + timedelta(days=d) for d in (-1, 0, 1)), key=lambda x: abs(x - near))


def load_reference(path):
    rows = []
    for e in json.loads(Path(path).read_text(encoding='utf-8')):
        raw = e.get('peak_event_time', '') or ''
        p = parse_event_time(raw)
        ok = bool(p and p['tz'] == 'WIB')
        r = {'title': e['title'], 'raw': raw, 'cls': classify(e['title']),
             'when': p['mid'] if ok else None, 'start': p['start'] if ok else None, 'end': p['end'] if ok else None}
        if ok:
            r['ingress'] = _clock(e.get('occultation_ingress'), p['mid'])
            r['egress'] = _clock(e.get('occultation_egress'), p['mid'])
        rows.append(r)
    return rows


def _nearest(comp, kind, bodies, when, limit_h=36):
    c = [(abs((F.jd_to_wib(x['jd']) - when).total_seconds()), i, x) for i, x in enumerate(comp)
         if x['kind'] == kind and frozenset(x['bodies']) == bodies]
    if not c:
        return None
    d, i, x = min(c, key=lambda z: z[0])
    return (i, x) if d <= limit_h * 3600 else None


def run(path, year, month, out_dir):
    ref = [r for r in load_reference(path) if r['when'] is None or (r['when'].year, r['when'].month) in
           {(year, month), (year + (month == 12), 1 if month == 12 else month + 1), (year - (month == 1), 12 if month == 1 else month - 1)}]
    comp = F.find_all(year, month)
    used, rows, deltas = set(), [], {}
    not_cov, unreadable = [], []

    def add(title, src, ours, kind):
        if ours is None:
            rows.append((title, src, None, None, kind)); return
        d = (ours - src).total_seconds() / 60.0
        rows.append((title, src, ours, d, kind)); deltas.setdefault(kind, []).append(d)

    for r in ref:
        if r['cls'] is None:
            not_cov.append(r['title']); continue
        if r['when'] is None:
            unreadable.append((r['title'], r['raw'])); continue
        kind, bodies = r['cls']
        hit = _nearest(comp, kind, bodies, r['when'])
        if hit is None:
            add(r['title'], r['when'], None, kind); continue
        i, c = hit
        used.add(i)
        if kind == 'occ_window':
            add(r['title'] + ' [mulai jendela]', r['start'], F.jd_to_wib(c['start']), 'occ_window_start')
            add(r['title'] + ' [akhir jendela]', r['end'] or r['start'], F.jd_to_wib(c['end']), 'occ_window_end')
            loc = _nearest(comp, 'occultation', bodies, r['when'], 12)
            if r.get('ingress'):                                   # sumber: terlihat dari Jakarta
                if loc:
                    used.add(loc[0])
                    add(r['title'] + ' [hilang, Jakarta]', r['ingress'], F.jd_to_wib(loc[1]['ingress']), 'occ_local_ingress')
                    if r.get('egress') and loc[1]['egress']:
                        add(r['title'] + ' [muncul, Jakarta]', r['egress'], F.jd_to_wib(loc[1]['egress']), 'occ_local_egress')
                else:
                    add(r['title'] + ' [hilang, Jakarta]', r['ingress'], None, 'occ_local_ingress')
            elif loc:
                rows.append((r['title'] + ' [Jakarta]', r['when'], None, None, 'HITUNGAN: terlihat di Jakarta, SUMBER: tidak ada jam lokal'))
        else:
            used.add(i)
            add(r['title'], r['when'], F.jd_to_wib(c['jd']), kind)

    md = [f'# Perbandingan hitungan vs in-the-sky.org, {year}-{month:02d}\n',
          f'Sumber pembanding: `{path}`. Waktu dalam WIB. Mesin: {E.NAME}.\n',
          '| Event sumber | Jam sumber | Jam hitungan | Selisih (menit) | Jenis |', '|---|---|---|---|---|']
    for title, w, c, d, k in rows:
        md.append(f"| {title} | {w:%d %b %H:%M} | {c:%d %b %H:%M} | {d:+.0f} | {k} |" if c else
                  f"| {title} | {w:%d %b %H:%M} | **tidak ditemukan** | - | {k} |")
    allv = [abs(x) for v in deltas.values() for x in v]
    md += ['', '## Ringkasan selisih per jenis (menit)', '', '| Jenis | n | rata-rata \\|selisih\\| | maks \\|selisih\\| |', '|---|---|---|---|']
    for k, v in sorted(deltas.items()):
        md.append(f"| {k} | {len(v)} | {st.mean(abs(x) for x in v):.1f} | {max(abs(x) for x in v):.0f} |")
    if allv:
        md += ['', f'Dibandingkan: **{len(allv)}** titik waktu. Median |selisih| = **{st.median(allv):.1f}** menit; '
                   f'{sum(1 for x in allv if x <= 15)} dari {len(allv)} berselisih <= 15 menit.']
    md += ['', f'## Event sumber yang BELUM dicakup pencari ({len(not_cov)})', ''] + [f'- {t}' for t in not_cov]
    if unreadable:
        md += ['', f'## Event sumber yang jam/zonanya TIDAK TERBACA ({len(unreadable)})',
               '(teks mentah dicetak agar format dapat diperbaiki)', ''] + [f'- {t}: `{raw[:110]!r}`' for t, raw in unreadable]
    extra = [c for i, c in enumerate(comp) if i not in used and c['kind'] not in ('conj_lon', 'occultation', 'occ_window')]
    md += ['', f'## Event hitungan yang TIDAK ada di data sumber ({len(extra)})', '',
           '(bisa berarti sumber memfilternya atau definisi kita terlalu longgar)', '']
    md += [f"- {F.jd_to_wib(c['jd']):%d %b %H:%M} {F.describe(c)}" + (f" (sep {c['sep']:.1f}°)" if 'sep' in c else '') for c in extra]
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    f = out / f'compare_{year}-{month:02d}.md'
    f.write_text('\n'.join(md), encoding='utf-8')
    return f, deltas, rows, not_cov, unreadable, extra


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/datasets/astronomy_events.json'
    y = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    m = int(sys.argv[3]) if len(sys.argv) > 3 else 11
    f, *_ = run(path, y, m, 'prototype/output')
    print(f.read_text(encoding='utf-8'))
