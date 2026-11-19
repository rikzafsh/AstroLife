"""
Pencari event tambahan (gerhana, hujan meteor) dan penormal skema katalog.
Semua fungsi memakai antarmuka mesin posisi `prototype.engine.E` sehingga berlaku untuk ephem_lite maupun Skyfield.
"""
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from prototype import find_events as F
from prototype.engine import E

ROOT = Path(__file__).resolve().parent.parent
METEOR_FILE = ROOT / 'data' / 'catalog' / 'meteor_showers.json'


def jd_to_utc(jd: float) -> datetime:
    return datetime(2000, 1, 1, 12) + timedelta(days=jd - 2451545.0)


def iso(jd: float) -> str:
    return jd_to_utc(jd).strftime('%Y-%m-%dT%H:%M:%S')


# ---------------------------------------------------------------------------
# Gerhana Bulan: jarak Bulan ke sumbu bayangan Bumi (titik anti-Matahari)
# ---------------------------------------------------------------------------
def _shadow_distance(t: float) -> float:
    s_ra, s_dec = E.eq('sun', t)
    m_ra, m_dec = E.eq('moon', t)
    return E.separation(m_ra, m_dec, (s_ra + 180.0) % 360.0, -s_dec)


def _shadow_radii(t: float):
    """(umbra, penumbra) dalam derajat pada jarak Bulan; Bumi diperbesar 2% (aturan Danjon)."""
    pi_m, pi_s, s_s = E.moon_horizontal_parallax_deg(t), E.sun_parallax_deg(t), E.sun_semidiameter_deg(t)
    return 1.02 * (pi_m + pi_s - s_s), 1.02 * (pi_m + pi_s + s_s)


def lunar_eclipses(t0: float, t1: float) -> list:
    out = []
    fulls = [e for e in F.moon_phases(t0 - 2, t1 + 2) if e['kind'] == 'full_moon']
    for fm in fulls:
        found = F.find_minima(_shadow_distance, fm['jd'] - 0.2, fm['jd'] + 0.2, 1 / 144)
        if not found:
            continue
        tg, d = min(found, key=lambda x: x[1])
        if not t0 <= tg < t1:
            continue
        ru, rp = _shadow_radii(tg)
        sm = E.moon_semidiameter_deg(tg)
        if d >= rp + sm:
            continue                                            # tidak ada gerhana (bahkan penumbral)
        umbral = (ru + sm - d) / (2 * sm)
        penumbral = (rp + sm - d) / (2 * sm)
        kind = 'total' if umbral >= 1 else ('sebagian' if umbral > 0 else 'penumbra')
        contacts = {}
        for name, radius in (('p', rp + sm), ('u', ru + sm), ('t', ru - sm)):
            if name == 'u' and umbral <= 0 or name == 't' and umbral < 1:
                continue
            g = lambda t, r=radius: _shadow_distance(t) - r
            a = F.find_roots(g, tg - 0.25, tg, 1 / 288, 5)
            b = F.find_roots(g, tg, tg + 0.25, 1 / 288, 5)
            if a and b:
                contacts[name] = (a[0], b[0])
        ev = {'category': 'gerhana_bulan', 'kind': kind, 'bodies': ['moon'], 'jd': tg,
              'details': {'jenis': kind, 'magnitudo_umbra': round(umbral, 3), 'magnitudo_penumbra': round(penumbral, 3),
                          'jarak_ke_sumbu_deg': round(d, 3)}}
        if 'p' in contacts:
            ev['start_jd'], ev['end_jd'] = contacts['p']
        if 'u' in contacts:
            ev['details']['umbra_mulai_utc'], ev['details']['umbra_selesai_utc'] = iso(contacts['u'][0]), iso(contacts['u'][1])
        if 't' in contacts:
            ev['details']['total_mulai_utc'], ev['details']['total_selesai_utc'] = iso(contacts['t'][0]), iso(contacts['t'][1])
        out.append(ev)
    return out


# ---------------------------------------------------------------------------
# Gerhana Matahari (global): sumbu bayangan Bulan terhadap pusat Bumi
# ---------------------------------------------------------------------------
CENTRAL_LIMIT = 0.9972          # gamma < ini: gerhana sentral (total/cincin) -- Meeus bab 54
PARTIAL_LIMIT = 1.5433          # gamma < ini: gerhana sebagian terlihat di suatu tempat


def solar_eclipses(t0: float, t1: float) -> list:
    out = []
    news = [e for e in F.moon_phases(t0 - 2, t1 + 2) if e['kind'] == 'new_moon']
    for nm in news:
        found = F.find_minima(lambda t: E.sep('moon', 'sun', t), nm['jd'] - 0.2, nm['jd'] + 0.2, 1 / 144)
        if not found:
            continue
        tg, sep = min(found, key=lambda x: x[1])
        if not t0 <= tg < t1:
            continue
        gamma = math.sin(math.radians(sep)) / math.sin(math.radians(E.moon_horizontal_parallax_deg(tg)))
        if gamma >= PARTIAL_LIMIT:
            continue
        sm, ss = E.moon_semidiameter_deg(tg), E.sun_semidiameter_deg(tg)
        kind = ('total' if sm > ss else 'cincin') if gamma < CENTRAL_LIMIT else 'sebagian'
        out.append({'category': 'gerhana_matahari', 'kind': kind, 'bodies': ['sun', 'moon'], 'jd': tg,
                    'details': {'jenis': kind, 'gamma_perkiraan': round(gamma, 3), 'sep_pusat_deg': round(sep, 3),
                                'rasio_diameter_bulan_matahari': round(sm / ss, 4)}})
    return out


# ---------------------------------------------------------------------------
# Hujan meteor: puncak = Matahari mencapai bujur tertentu (IMO, J2000 -> tanggal)
# ---------------------------------------------------------------------------
def _precession_deg(jd: float) -> float:
    T = (jd - 2451545.0) / 36525.0
    return (5028.796195 * T + 1.1054348 * T * T) / 3600.0


def meteor_showers(year: int, path: Path = METEOR_FILE) -> list:
    data = json.loads(Path(path).read_text(encoding='utf-8'))['showers']
    out = []
    for sh in data:
        m, d = sh['approx_md']
        center = F.wib_to_jd(year, m, d)
        lam = sh['lambda_sun_j2000'] + _precession_deg(center)
        f = lambda t: E.wrap180(E.ecl('sun', t)[0] - lam)
        roots = F.find_roots(f, center - 6, center + 6, 0.25, 30)
        if not roots:
            continue
        out.append({'category': 'hujan_meteor', 'kind': sh['code'].lower(), 'bodies': [], 'jd': roots[0],
                    'details': {'nama': sh['name'], 'zhr': sh['zhr'], 'radian_ra': sh['radiant_ra'],
                                'radian_dec': sh['radiant_dec'], 'kecepatan_kms': sh['speed_kms'],
                                'catatan': 'Waktu puncak perkiraan (ketidakpastian beberapa jam hingga ~1 hari).'}})
    return out


# ---------------------------------------------------------------------------
# Penormal skema katalog
# ---------------------------------------------------------------------------
NAMES = F.BODY_ID
PHASE_TITLE = {'new_moon': 'Bulan Baru', 'first_quarter': 'Bulan Kuartal Awal', 'full_moon': 'Bulan Purnama', 'last_quarter': 'Bulan Kuartal Akhir'}


def _eid(cat: str, kind: str, jd: float, bodies) -> str:
    return f"{cat}-{kind}-{jd_to_utc(jd):%Y%m%d%H%M}" + ''.join('-' + b for b in bodies)


def _ev(cat, kind, title, jd, bodies, sep=None, start=None, end=None, details=None):
    e = {'id': _eid(cat, kind, jd, bodies), 'category': cat, 'kind': kind, 'title': title, 'bodies': list(bodies),
         'time_utc': iso(jd), 'details': details or {}}
    if start is not None:
        e['start_utc'], e['end_utc'] = iso(start), iso(end)
    if sep is not None:
        e['separation_deg'] = round(sep, 3)
    return e


def normalize(raw: list) -> list:
    """Mengubah keluaran find_events (+ gerhana/meteor) menjadi skema katalog; menggabungkan event sepasang benda."""
    out, pairs = [], {}
    for r in raw:
        k, b = r['kind'], tuple(r['bodies'])
        if k in ('conj_lon', 'occultation'):
            continue                                            # duplikat / khusus lokasi
        if r.get('category') in ('gerhana_bulan', 'gerhana_matahari', 'hujan_meteor'):
            title = {'gerhana_bulan': lambda: f"Gerhana Bulan {k} ({r['details']['magnitudo_umbra']:.2f} umbra)" if k != 'penumbra'
                     else 'Gerhana Bulan penumbra',
                     'gerhana_matahari': lambda: f"Gerhana Matahari {k}",
                     'hujan_meteor': lambda: f"Hujan Meteor {r['details']['nama']}"}[r['category']]()
            out.append(_ev(r['category'], k, title, r['jd'], b, start=r.get('start_jd'), end=r.get('end_jd'), details=r['details']))
        elif k in PHASE_TITLE:
            out.append(_ev('fase_bulan', k, PHASE_TITLE[k], r['jd'], b))
        elif k in ('close', 'conj_ra', 'occ_window'):
            pairs.setdefault(frozenset(b), []).append(r)
        elif k == 'opposition':
            out.append(_ev('oposisi', k, f"{NAMES[b[0]]} oposisi", r['jd'], b))
        elif k.startswith('greatest_elongation'):
            side = 'timur' if k.endswith('east') else 'barat'
            out.append(_ev('elongasi', k, f"{NAMES[b[0]]} elongasi maksimum {side}", r['jd'], b,
                           details={'elongasi_deg': round(r['sep'], 2), 'sisi': side}))
        elif k == 'dichotomy':
            out.append(_ev('fase_planet', k, f"{NAMES[b[0]]} dikotomi (fase 50%)", r['jd'], b))
        elif k == 'greatest_brightness':
            out.append(_ev('fase_planet', k, f"{NAMES[b[0]]} paling terang", r['jd'], b, details={'magnitudo': round(r['mag'], 2)}))

    for key, evs in pairs.items():
        evs.sort(key=lambda e: e['jd'])
        clusters, cur = [], [evs[0]]
        for e in evs[1:]:
            if e['jd'] - cur[-1]['jd'] <= 1.5:
                cur.append(e)
            else:
                clusters.append(cur)
                cur = [e]
        clusters.append(cur)
        for cl in clusters:
            occ = next((e for e in cl if e['kind'] == 'occ_window'), None)
            close = next((e for e in cl if e['kind'] == 'close'), None)
            conj = next((e for e in cl if e['kind'] == 'conj_ra'), None)
            bodies = sorted(key, key=lambda x: (x != 'moon', x))
            details = {}
            if close:
                details['pendekatan_terdekat_utc'] = iso(close['jd'])
            if conj:
                details['konjungsi_asensio_rekta_utc'] = iso(conj['jd'])
            if occ:
                other = [x for x in bodies if x != 'moon'][0]
                out.append(_ev('okultasi', 'occultation', f"Okultasi {NAMES[other]} oleh Bulan", occ['jd'], bodies,
                               sep=(close or occ)['sep'], start=occ['start'], end=occ['end'], details=details))
            else:
                main = close or conj
                title = 'Konjungsi ' + '–'.join(NAMES[x] for x in bodies)
                out.append(_ev('konjungsi', 'conjunction', title, main['jd'], bodies, sep=main['sep'], details=details))
    out.sort(key=lambda e: e['time_utc'])
    return out
