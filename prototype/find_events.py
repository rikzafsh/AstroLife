"""
Pencari event astronomi (prototipe).  Jalankan:  python -m prototype.find_events 2026 11
Semua waktu keluaran dalam WIB (UTC+7). Lokasi untuk okultasi: Jakarta (bisa diubah).
"""
import os
import sys
from datetime import datetime, timedelta

import numpy as np

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
    out, fa = [], f(t0)
    t = t0
    while t < t1:
        t2 = min(t + step, t1)
        fb = f(t2)
        if fa == 0 or fa * fb < 0:
            if abs(fa) < max_abs and abs(fb) < max_abs:          # buang lompatan pembungkusan sudut
                lo, hi, flo = t, t2, fa
                for _ in range(22):                                  # 22 iterasi: selang 1 jam -> ~1 detik
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
            gr = 0.6180339887498949                                # golden-section: 1 evaluasi per iterasi
            x1, x2 = hi - gr * (hi - lo), lo + gr * (hi - lo)
            f1, f2 = f(x1), f(x2)
            for _ in range(28):
                if f1 < f2:
                    hi, x2, f2 = x2, x1, f1
                    x1 = hi - gr * (hi - lo)
                    f1 = f(x1)
                else:
                    lo, x1, f1 = x1, x2, f2
                    x2 = lo + gr * (hi - lo)
                    f2 = f(x2)
            t = (lo + hi) / 2
            out.append((t, f(t)))
    return out


# ---------------------------------------------------------------------------
# Alat VEKTOR: pemindaian kasar + penghalusan pada grid halus lokal, semua lewat larik (engine.eq_many, dst.)
# ---------------------------------------------------------------------------
USE_BATCH = bool(getattr(E, 'HAS_BATCH', False)) and os.environ.get('ASTROLIFE_BATCH', '1') != '0'
_wrap = lambda x: (np.asarray(x) + 180.0) % 360.0 - 180.0


class _Grid:
    """Memo posisi pada grid waktu yang sama (Bulan dipakai ulang oleh 15 pasangan)."""
    def __init__(self):
        self.c = {}

    def _get(self, kind, body, ts):
        key = (kind, body, ts.tobytes())
        if key not in self.c:
            self.c[key] = getattr(E, kind + '_many')(body, ts)
        return self.c[key]

    def eq(self, body, ts):
        return self._get('eq', body, ts)

    def ecl(self, body, ts):
        return self._get('ecl', body, ts)


def _grid(t0, t1, step, extra=0):
    """Grid waktu t0..>=t1; extra=1 menambah satu langkah di luar t1 agar minimum tepat sebelum batas tetap terdeteksi."""
    return t0 + step * np.arange(int(np.ceil((t1 - t0) / step)) + 1 + extra)


def roots_vec(fvec, t0, t1, step, max_abs=60.0, passes=2, fine=21):
    """Akar f(t)=0 (pergantian tanda) pada [t0, t1]; f menerima larik. Penghalusan = grid halus lokal + interpolasi linear."""
    ts = _grid(t0, t1, step)
    v = np.asarray(fvec(ts), float)
    idx = np.nonzero((v[:-1] * v[1:] < 0) & (np.abs(v[:-1]) < max_abs) & (np.abs(v[1:]) < max_abs))[0]
    out = []
    for i in idx:
        lo, hi = ts[i], ts[i + 1]
        t = None
        for _ in range(passes):
            sub = np.linspace(lo, hi, fine)
            w = np.asarray(fvec(sub), float)
            k = np.nonzero(w[:-1] * w[1:] <= 0)[0]
            if not len(k):
                break
            j = k[0]
            lo, hi = sub[j], sub[j + 1]
            t = lo + (hi - lo) * (w[j] / (w[j] - w[j + 1]) if w[j] != w[j + 1] else 0.0)
        if t is not None:
            out.append(float(t))
    return out


def minima_vec(fvec, t0, t1, step, squared=False, passes=2, fine=41):
    """Minimum lokal f(t) pada [t0, t1] (hanya titik dalam); squared=True meminimalkan f^2 (eksak parabolik bagi jarak sudut)."""
    ts = _grid(t0, t1, step, extra=1)
    v = np.asarray(fvec(ts), float)
    idx = np.nonzero((v[1:-1] < v[:-2]) & (v[1:-1] <= v[2:]))[0] + 1
    out = []
    for i in idx:
        lo, hi = ts[i - 1], ts[i + 1]
        t = ts[i]
        for _ in range(passes):
            sub = np.linspace(lo, hi, fine)
            w = np.asarray(fvec(sub), float)
            w = w * w if squared else w
            j = int(np.argmin(w))
            if 0 < j < len(sub) - 1:
                h = sub[1] - sub[0]
                den = w[j - 1] - 2 * w[j] + w[j + 1]
                t = sub[j] + (h * (w[j - 1] - w[j + 1]) / (2 * den) if den > 0 else 0.0)
            else:
                t = sub[j]
            lo, hi = sub[max(j - 1, 0)], sub[min(j + 1, len(sub) - 1)]
        out.append((float(t), float(np.asarray(fvec(np.array([t])))[0])))
    return out


# ---------------------------------------------------------------------------
# Katalog event
# ---------------------------------------------------------------------------
def moon_phases(t0, t1):
    names = {0: 'new_moon', 90: 'first_quarter', 180: 'full_moon', 270: 'last_quarter'}
    ev = []
    G = _Grid()
    for target, kind in names.items():
        if USE_BATCH:
            fv = lambda ts, tg=target: _wrap(G.ecl('moon', ts)[0] - G.ecl('sun', ts)[0] - tg)
            roots = roots_vec(fv, t0, t1, 0.25)
        else:
            f = lambda t, tg=target: E.wrap180(E.ecl('moon', t)[0] - E.ecl('sun', t)[0] - tg)
            roots = find_roots(f, t0, t1, 0.25)
        for t in roots:
            ev.append({'kind': kind, 'bodies': ('moon',), 'jd': t})
    return ev


def pair_events(a, b, t0, t1, step, max_sep, with_lon=True, G=None):
    ev = []
    if USE_BATCH:
        G = G or _Grid()
        sepv = lambda ts: E.separation_many(*G.eq(a, ts), *G.eq(b, ts))
        for t, s_ in minima_vec(sepv, t0, t1, step, squared=True):
            if s_ <= max_sep:
                ev.append({'kind': 'close', 'bodies': (a, b), 'jd': t, 'sep': s_})
        specs = [('conj_ra', lambda ts: _wrap(G.eq(a, ts)[0] - G.eq(b, ts)[0]))]
        if with_lon:
            specs.append(('conj_lon', lambda ts: _wrap(G.ecl(a, ts)[0] - G.ecl(b, ts)[0])))
        for kind, fv in specs:
            for t in roots_vec(fv, t0, t1, step, max_abs=30):
                s_ = float(sepv(np.array([t]))[0])
                if s_ <= max_sep:
                    ev.append({'kind': kind, 'bodies': (a, b), 'jd': t, 'sep': s_})
        return ev
    sep = lambda t: E.sep(a, b, t)
    for t, s_ in find_minima(sep, t0, t1, step):
        if s_ <= max_sep:
            ev.append({'kind': 'close', 'bodies': (a, b), 'jd': t, 'sep': s_})
    f_lon = lambda t: E.wrap180(E.ecl(a, t)[0] - E.ecl(b, t)[0])
    f_ra = lambda t: E.wrap180(E.eq(a, t)[0] - E.eq(b, t)[0])
    for kind, f in (('conj_lon', f_lon), ('conj_ra', f_ra)):
        if kind == 'conj_lon' and not with_lon:
            continue
        for t in find_roots(f, t0, t1, step, max_abs=30):
            s_ = sep(t)
            if s_ <= max_sep:
                ev.append({'kind': kind, 'bodies': (a, b), 'jd': t, 'sep': s_})
    return ev


def opposition_events(body, t0, t1, G=None):
    if USE_BATCH:
        G = G or _Grid()
        fv = lambda ts: _wrap(G.ecl(body, ts)[0] - G.ecl('sun', ts)[0] - 180.0)
        return [{'kind': 'opposition', 'bodies': (body,), 'jd': t} for t in roots_vec(fv, t0, t1, 1.0)]
    f = lambda t: E.wrap180(E.ecl(body, t)[0] - E.ecl('sun', t)[0] - 180.0)
    return [{'kind': 'opposition', 'bodies': (body,), 'jd': t} for t in find_roots(f, t0, t1, 1.0, max_abs=60)]


def inner_planet_events(body, t0, t1):
    ev = []
    # Elongasi = selisih BUJUR EKLIPTIKA terhadap Matahari (definisi konvensional pada almanak astronomi;
    # jarak sudut geosentris memberi waktu berbeda ~1 jam karena puncaknya sangat datar).
    signed = lambda t: E.wrap180(E.ecl(body, t)[0] - E.ecl('sun', t)[0])
    if USE_BATCH:
        G = _Grid()
        sv = lambda ts: _wrap(G.ecl(body, ts)[0] - G.ecl('sun', ts)[0])
        for t, v in minima_vec(lambda ts: -np.abs(sv(ts)), t0, t1, 0.5):
            ev.append({'kind': 'greatest_elongation_' + ('east' if sv(np.array([t]))[0] > 0 else 'west'),
                       'bodies': (body,), 'jd': t, 'sep': -v})
    else:
        for t, v in find_minima(lambda t: -abs(signed(t)), t0, t1, 0.5):
            ev.append({'kind': 'greatest_elongation_' + ('east' if signed(t) > 0 else 'west'), 'bodies': (body,),
                       'jd': t, 'sep': -v})
    # Dikotomi & kecerahan maksimum berubah lambat (hari): langkah 1 hari cukup
    for t in find_roots(lambda t: E.phase_angle_and_mag(body, t)[0] - 90.0, t0, t1, 1.0):
        ev.append({'kind': 'dichotomy', 'bodies': (body,), 'jd': t})
    for t, v in find_minima(lambda t: E.phase_angle_and_mag(body, t)[1], t0, t1, 1.0):
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
    Jendela waktunya = saat kondisi itu terpenuhi (jendela keterlihatan global okultasi).
    """
    out = []
    for c in close_events:
        if c['kind'] != 'close' or 'moon' not in c['bodies']:
            continue
        other = [b for b in c['bodies'] if b != 'moon'][0]
        if other in CLUSTERS:
            continue
        if USE_BATCH:
            def gv(ts, other=other):
                sd, hp = E.moon_radii_many(ts)
                return E.separation_many(*E.eq_many('moon', ts), *E.eq_many(other, ts)) - (sd + hp)
            if gv(np.array([c['jd']]))[0] >= 0:
                continue
            a = roots_vec(gv, c['jd'] - 0.25, c['jd'], 1 / 288, 5)
            b = roots_vec(gv, c['jd'], c['jd'] + 0.25, 1 / 288, 5)
        else:
            g = lambda t, other=other: E.sep('moon', other, t) - (E.moon_semidiameter_deg(t) + E.moon_horizontal_parallax_deg(t))
            if g(c['jd']) >= 0:
                continue
            a = find_roots(g, c['jd'] - 0.25, c['jd'], 1 / 288, 5)
            b = find_roots(g, c['jd'], c['jd'] + 0.25, 1 / 288, 5)
        if a and b:
            out.append({'kind': 'occ_window', 'bodies': ('moon', other), 'jd': c['jd'], 'start': a[0], 'end': b[0],
                        'sep': c['sep']})
    return out


def find_window(t0, t1, lat=-6.2088, lon=106.8456, include_local=True, with_lon=True):
    """
    Semua event dalam jendela JD [t0, t1).
    include_local=False melewatkan okultasi lokal (khusus satu lokasi); with_lon=False melewatkan konjungsi
    bujur ekliptika (katalog tidak memakainya).
    """
    G = _Grid() if USE_BATCH else None
    events = moon_phases(t0, t1)
    for b in E.PLANETS + CLUSTERS:
        events += pair_events('moon', b, t0, t1, 1 / 24, 8.0, with_lon, G)
    for b in STARS:                       # bintang: hanya yang cukup dekat untuk berpotensi okultasi
        events += [e for e in pair_events('moon', b, t0, t1, 1 / 24, 1.6, False, G) if e['kind'] == 'close']
    for b in ('mars', 'jupiter', 'saturn', 'uranus', 'neptune'):
        events += opposition_events(b, t0, t1, G)
    visible = ['mercury', 'venus', 'mars', 'jupiter', 'saturn']
    for i, a in enumerate(visible):
        for b in visible[i + 1:]:
            events += pair_events(a, b, t0, t1, 0.5, 5.0, with_lon, G)
    for p in ('mercury', 'venus'):
        events += inner_planet_events(p, t0 - 20, t1 + 20)
    events = [e for e in events if t0 <= e['jd'] < t1]
    if include_local:
        events += [o for o in occultations(events, lat, lon) if t0 <= o['jd'] < t1]
    events += [o for o in occultation_windows(events) if t0 <= o['jd'] < t1]
    events.sort(key=lambda e: e['jd'])
    return events


def find_all(year, month, lat=-6.2088, lon=106.8456, include_local=True, with_lon=True):
    nxt = (year + (month == 12), 1 if month == 12 else month + 1)
    return find_window(wib_to_jd(year, month, 1), wib_to_jd(nxt[0], nxt[1], 1), lat, lon, include_local, with_lon)


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
