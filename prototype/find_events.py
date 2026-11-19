"""
Pencari event astronomi (prototipe).  Jalankan:  python -m prototype.find_events 2026 11
Semua waktu keluaran dalam WIB (UTC+7). Lokasi untuk okultasi: Jakarta (bisa diubah).
"""
import sys
from datetime import datetime, timedelta

from app.services import astro_core as ac
from prototype.engine import E

WIB = 7.0
BODY_ID = {'moon': 'Bulan', 'sun': 'Matahari', 'mercury': 'Merkurius', 'venus': 'Venus', 'mars': 'Mars',
           'jupiter': 'Jupiter', 'saturn': 'Saturnus', 'uranus': 'Uranus', 'neptune': 'Neptunus', 'm45': 'M45 (Pleiades)', 'm44': 'M44 (Praesepe)',
           'regulus': 'Regulus', 'antares': 'Antares', 'spica': 'Spica', 'aldebaran': 'Aldebaran',
           'sigma_sagittarii': 'Sigma Sagittarii', 'beta_tauri': 'Beta Tauri'}
STARS = ['regulus', 'antares', 'spica', 'aldebaran', 'sigma_sagittarii', 'beta_tauri']
CLUSTERS = ['m45', 'm44']


def jd_to_wib(jd_ut: float) -> datetime:
    return datetime(2000, 1, 1, 12) + timedelta(days=jd_ut - 2451545.0, hours=WIB)


def wib_to_jd(y, m, d, h=0, mi=0) -> float:
    return ac.jd_from_jdn(ac.to_jdn(y, m, d), h - WIB + mi / 60.0)


# ---------------------------------------------------------------------------
# Alat pencarian akar / minimum
# ---------------------------------------------------------------------------
def find_roots(f, t0, t1, step, max_abs=60.0):
    out, a, fa = [], t0, f(t0)
    t = t0
    while t < t1:
        t2 = min(t + step, t1)
        fb = f(t2)
        if fa == 0 or fa * fb < 0:
            if abs(fa) < max_abs and abs(fb) < max_abs:          # buang lompatan pembungkusan sudut
                lo, hi, flo = t, t2, fa
                for _ in range(40):
                    mid = (lo + hi) / 2
                    fm = f(mid)
                    if flo * fm <= 0:
                        hi = mid
                    else:
                        lo, flo = mid, fm
                out.append((lo + hi) / 2)
        t, fa = t2, fb
    return out


def find_minima(f, t0, t1, step):
    ts = [t0 + i * step for i in range(int((t1 - t0) / step) + 2)]
    vs = [f(t) for t in ts]
    out = []
    for i in range(1, len(ts) - 1):
        if vs[i] < vs[i - 1] and vs[i] <= vs[i + 1]:
            lo, hi = ts[i - 1], ts[i + 1]
            for _ in range(60):                                    # ternary search
                m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
                if f(m1) < f(m2):
                    hi = m2
                else:
                    lo = m1
            t = (lo + hi) / 2
            out.append((t, f(t)))
    return out


# ---------------------------------------------------------------------------
# Katalog event
# ---------------------------------------------------------------------------
def moon_phases(t0, t1):
    names = {0: 'new_moon', 90: 'first_quarter', 180: 'full_moon', 270: 'last_quarter'}
    ev = []
    for target, kind in names.items():
        f = lambda t, tg=target: E.wrap180(E.ecl('moon', t)[0] - E.ecl('sun', t)[0] - tg)
        for t in find_roots(f, t0, t1, 0.25):
            ev.append({'kind': kind, 'bodies': ('moon',), 'jd': t})
    return ev


def pair_events(a, b, t0, t1, step, max_sep):
    ev = []
    sep = lambda t: E.sep(a, b, t)
    for t, s in find_minima(sep, t0, t1, step):
        if s <= max_sep:
            ev.append({'kind': 'close', 'bodies': (a, b), 'jd': t, 'sep': s})
    f_lon = lambda t: E.wrap180(E.ecl(a, t)[0] - E.ecl(b, t)[0])
    f_ra = lambda t: E.wrap180(E.eq(a, t)[0] - E.eq(b, t)[0])
    for kind, f in (('conj_lon', f_lon), ('conj_ra', f_ra)):
        for t in find_roots(f, t0, t1, step, max_abs=30):
            s = sep(t)
            if s <= max_sep:
                ev.append({'kind': kind, 'bodies': (a, b), 'jd': t, 'sep': s})
    return ev


def opposition_events(body, t0, t1):
    f = lambda t: E.wrap180(E.ecl(body, t)[0] - E.ecl('sun', t)[0] - 180.0)
    return [{'kind': 'opposition', 'bodies': (body,), 'jd': t} for t in find_roots(f, t0, t1, 1.0, max_abs=60)]


def inner_planet_events(body, t0, t1):
    ev = []
    # Elongasi = selisih BUJUR EKLIPTIKA terhadap Matahari (definisi yang cocok dengan in-the-sky.org;
    # jarak sudut geosentris memberi waktu berbeda ~1 jam karena puncaknya sangat datar).
    signed = lambda t: E.wrap180(E.ecl(body, t)[0] - E.ecl('sun', t)[0])
    for t, v in find_minima(lambda t: -abs(signed(t)), t0, t1, 0.5):
        ev.append({'kind': 'greatest_elongation_' + ('east' if signed(t) > 0 else 'west'), 'bodies': (body,),
                   'jd': t, 'sep': -v})
    for t in find_roots(lambda t: E.phase_angle_and_mag(body, t)[0] - 90.0, t0, t1, 0.5):
        ev.append({'kind': 'dichotomy', 'bodies': (body,), 'jd': t})
    for t, v in find_minima(lambda t: E.phase_angle_and_mag(body, t)[1], t0, t1, 0.5):
        if t0 + 1 < t < t1 - 1:                                      # abaikan 'minimum' di tepi jendela
            ev.append({'kind': 'greatest_brightness', 'bodies': (body,), 'jd': t, 'mag': v})
    return ev


def occultations(close_events, lat, lon):
    """Dari tiap close approach Bulan-planet: apakah pengamat di (lat, lon) melihat okultasi?"""
    out = []
    for c in close_events:
        if c['kind'] != 'close' or 'moon' not in c['bodies']:
            continue
        other = [b for b in c['bodies'] if b != 'moon'][0]
        if other in E.FIXED and other in CLUSTERS:
            continue
        tsep = lambda t: E.separation(*E.topo_moon(t, lat, lon), *E.eq(other, t))
        (tm, smin), = find_minima(tsep, c['jd'] - 0.15, c['jd'] + 0.15, 1 / 144)[:1] or [(None, None)]
        if tm is None:
            continue
        sd = E.moon_semidiameter_deg(tm)
        if smin < sd:
            g = lambda t: tsep(t) - sd
            ing = find_roots(g, tm - 0.1, tm, 1 / 288, 5)
            egr = find_roots(g, tm, tm + 0.1, 1 / 288, 5)
            out.append({'kind': 'occultation', 'bodies': ('moon', other), 'jd': tm, 'sep': smin,
                        'ingress': ing[0] if ing else None, 'egress': egr[0] if egr else None,
                        'moon_alt': ac.moon_altitude(tm, lat, lon)})
    return out


def occultation_windows(close_events):
    """
    Okultasi yang terjadi di SUATU TEMPAT di Bumi: jarak sudut geosentris < semidiameter Bulan + paralaks horizontal.
    Jendela waktunya = saat kondisi itu terpenuhi (diperkirakan sama dengan 'FROM ... TO' di in-the-sky.org).
    """
    out = []
    for c in close_events:
        if c['kind'] != 'close' or 'moon' not in c['bodies']:
            continue
        other = [b for b in c['bodies'] if b != 'moon'][0]
        if other in CLUSTERS:
            continue
        g = lambda t: E.sep('moon', other, t) - (E.moon_semidiameter_deg(t) + E.moon_horizontal_parallax_deg(t))
        if g(c['jd']) >= 0:
            continue
        a = find_roots(g, c['jd'] - 0.25, c['jd'], 1 / 288, 5)
        b = find_roots(g, c['jd'], c['jd'] + 0.25, 1 / 288, 5)
        if a and b:
            out.append({'kind': 'occ_window', 'bodies': ('moon', other), 'jd': c['jd'], 'start': a[0], 'end': b[0],
                        'sep': c['sep']})
    return out


def find_window(t0, t1, lat=-6.2088, lon=106.8456, include_local=True):
    """Semua event dalam jendela JD [t0, t1). include_local=False melewatkan okultasi lokal (khusus satu lokasi)."""
    events = moon_phases(t0, t1)
    for b in E.PLANETS + CLUSTERS:
        events += pair_events('moon', b, t0, t1, 1 / 24, 8.0)
    for b in STARS:                       # bintang: hanya yang cukup dekat untuk berpotensi okultasi
        events += [e for e in pair_events('moon', b, t0, t1, 1 / 24, 1.6) if e['kind'] == 'close']
    for b in ('mars', 'jupiter', 'saturn', 'uranus', 'neptune'):
        events += opposition_events(b, t0, t1)
    visible = ['mercury', 'venus', 'mars', 'jupiter', 'saturn']
    for i, a in enumerate(visible):
        for b in visible[i + 1:]:
            events += pair_events(a, b, t0, t1, 0.5, 5.0)
    for p in ('mercury', 'venus'):
        events += inner_planet_events(p, t0 - 20, t1 + 20)
    events = [e for e in events if t0 <= e['jd'] < t1]
    if include_local:
        events += [o for o in occultations(events, lat, lon) if t0 <= o['jd'] < t1]
    events += [o for o in occultation_windows(events) if t0 <= o['jd'] < t1]
    events.sort(key=lambda e: e['jd'])
    return events


def find_all(year, month, lat=-6.2088, lon=106.8456, include_local=True):
    nxt = (year + (month == 12), 1 if month == 12 else month + 1)
    return find_window(wib_to_jd(year, month, 1), wib_to_jd(nxt[0], nxt[1], 1), lat, lon, include_local)


def describe(e):
    b = [BODY_ID[x] for x in e['bodies']] + ['', '']
    k = e['kind']
    return {'new_moon': 'Bulan Baru', 'first_quarter': 'Bulan Kuartal Awal', 'full_moon': 'Bulan Purnama',
            'last_quarter': 'Bulan Kuartal Akhir', 'close': f'Close approach {" - ".join(b)}',
            'conj_lon': f'Konjungsi (bujur ekliptika) {" - ".join(b)}', 'conj_ra': f'Konjungsi (asensio rekta) {" - ".join(b)}',
            'dichotomy': f'{b[0]} dikotomi (fase 50%)', 'greatest_brightness': f'{b[0]} paling terang',
            'greatest_elongation_east': f'{b[0]} elongasi maks. timur', 'greatest_elongation_west': f'{b[0]} elongasi maks. barat',
            'occultation': f'Okultasi {b[1]} oleh Bulan (Jakarta)', 'opposition': f'{b[0]} oposisi', 'occ_window': f'Okultasi {b[1]} oleh Bulan (terlihat di suatu tempat di Bumi)'}.get(k, k)


if __name__ == '__main__':
    y, m = int(sys.argv[1]), int(sys.argv[2])
    for e in find_all(y, m):
        extra = f"  sep={e['sep']:.2f}°" if 'sep' in e else ''
        print(jd_to_wib(e['jd']).strftime('%Y-%m-%d %H:%M WIB'), describe(e), extra)
