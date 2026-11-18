"""
Mesin posisi berbasis Skyfield + JPL DE440s (pengganti ephem_lite).

STATUS: ditulis tanpa dapat dijalankan di lingkungan pengembangan (tanpa internet/Skyfield). Jalankan dulu
    python -m prototype.verify_engine
untuk membandingkan dengan ephem_lite sebelum mempercayai hasilnya.

Instalasi:  pip install -r requirements-prototype.txt
Saat pertama kali diimpor, de440s.bsp (~32 MB) diunduh otomatis ke data/ephemeris/.
Semua posisi: geosentris, tampak (aberrasi + defleksi), ekuinoks/ekliptika TANGGAL, derajat.
Waktu masukan: JD dalam UT (UT1 ~ UT untuk keperluan ini); Skyfield mengurus Delta-T.
"""
import math
from functools import lru_cache
from pathlib import Path

from skyfield.api import Loader, Star, wgs84

try:                                    # opsional: model magnitudo Mallama & Hilton
    from skyfield.magnitudelib import planetary_magnitude
except Exception:                       # pragma: no cover
    planetary_magnitude = None

# Fungsi MURNI (bukan mesin posisi) dipakai bersama dengan ephem_lite
from prototype.ephem_lite import FIXED, PLANETS, wrap180, separation, EARTH_RADIUS_KM  # noqa: F401

NAME = 'skyfield + JPL DE440s'
# False: rumus Astronomical Almanac (sepadan dengan in-the-sky.org; puncak 'paling terang' Venus jatuh pada tanggal yang sama).
# True : model Mallama & Hilton bawaan Skyfield (lebih akurat secara fisik, tetapi puncak Venus bergeser ~3 hari).
USE_MALLAMA = False
_DIR = Path(__file__).resolve().parent.parent / 'data' / 'ephemeris'
_DIR.mkdir(parents=True, exist_ok=True)
_load = Loader(str(_DIR))
_ts = _load.timescale()
_eph = _load('de440s.bsp')

_earth, _sun, _moon = _eph['earth'], _eph['sun'], _eph['moon']
_BODY = {p: _eph[f'{p} barycenter'] for p in PLANETS}      # barisentrum planet (selisih ke pusat planet diabaikan)
_BODY['moon'], _BODY['sun'] = _moon, _sun
for _k, (_ra, _dec) in FIXED.items():                       # bintang/gugus: RA/Dec J2000
    _BODY[_k] = Star(ra_hours=_ra / 15.0, dec_degrees=_dec)


@lru_cache(maxsize=400_000)
def _geo(body: str, jd_ut: float):
    """(RA, Dec, lon_ekliptika, lat_ekliptika, jarak_km) geosentris tampak, ekuinoks tanggal."""
    t = _ts.ut1_jd(jd_ut)
    app = _earth.at(t).observe(_BODY[body]).apparent()
    ra, dec, dist = app.radec(epoch='date')
    lat, lon, _ = app.ecliptic_latlon(epoch='date')
    return (ra.hours * 15.0) % 360.0, dec.degrees, lon.degrees % 360.0, lat.degrees, dist.km


def eq(body: str, jd_ut: float):
    g = _geo(body, jd_ut)
    return g[0], g[1]


def ecl(body: str, jd_ut: float):
    g = _geo(body, jd_ut)
    return g[2], g[3]


def sep(a: str, b: str, jd_ut: float) -> float:
    return separation(*eq(a, jd_ut), *eq(b, jd_ut))


@lru_cache(maxsize=200_000)
def topo_moon(jd_ut: float, lat: float, lon: float):
    """(RA, Dec) topocentris Bulan untuk pengamat di permukaan laut (WGS84)."""
    t = _ts.ut1_jd(jd_ut)
    observer = _earth + wgs84.latlon(lat, lon)
    ra, dec, _ = observer.at(t).observe(_moon).apparent().radec(epoch='date')
    return (ra.hours * 15.0) % 360.0, dec.degrees


def moon_semidiameter_deg(jd_ut: float) -> float:
    return math.degrees(math.asin(0.2725076 * EARTH_RADIUS_KM / _geo('moon', jd_ut)[4]))


def moon_horizontal_parallax_deg(jd_ut: float) -> float:
    return math.degrees(math.asin(EARTH_RADIUS_KM / _geo('moon', jd_ut)[4]))


def phase_angle_and_mag(body: str, jd_ut: float):
    """Sudut fase (derajat) dan magnitudo visual Merkurius/Venus."""
    t = _ts.ut1_jd(jd_ut)
    p = _BODY[body].at(t).position.au
    e = _earth.at(t).position.au
    s = _sun.at(t).position.au
    r = float(math.dist(p, s))          # planet - Matahari
    delta = float(math.dist(p, e))      # planet - Bumi
    R = float(math.dist(e, s))          # Bumi - Matahari
    i = math.degrees(math.acos(max(-1.0, min(1.0, (r * r + delta * delta - R * R) / (2 * r * delta)))))
    mag = None
    if USE_MALLAMA and planetary_magnitude is not None:
        try:
            mag = float(planetary_magnitude(_earth.at(t).observe(_eph[body])))
        except Exception:
            mag = None
    if mag is None:                      # cadangan: rumus Astronomical Almanac (sama dengan ephem_lite)
        if body == 'venus':
            mag = -4.40 + 5 * math.log10(r * delta) + 0.0009 * i + 0.000239 * i ** 2 - 0.00000065 * i ** 3
        else:
            mag = -0.42 + 5 * math.log10(r * delta) + 0.0380 * i - 0.000273 * i ** 2 + 0.000002 * i ** 3
    return i, mag
