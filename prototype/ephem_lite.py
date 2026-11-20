"""
ephem_lite: mesin posisi SEMENTARA untuk prototipe pencarian event.

Akurasi (perkiraan, lihat prototype/compare.py untuk pengukuran nyata):
  - Bulan/Matahari: Meeus (suku utama)            ~ 1-2 menit busur
  - Planet: elemen Keplerian JPL (Standish, 1800-2050) ~ menit busur (Jupiter/Saturnus terburuk)
PENGGANTI PRODUKSI: Skyfield + JPL DE440s (detik busur). Antarmuka `eq()`, `ecl()` sengaja dibuat sama
untuk semua benda agar mesin ini bisa diganti tanpa mengubah kode pencari event.
"""
import math

import numpy as np

from app.services import astro_core as ac
from prototype import magnitudes as MG

NAME = 'ephem_lite (sementara: Meeus + elemen JPL Standish)'
DELTA_T_DAYS = 69.2 / 86400.0      # TT - UT, kira-kira tahun 2026
KM_PER_AU = 149597870.7
EARTH_RADIUS_KM = 6378.14
LIGHT_DAY_PER_AU = 0.0057755183

# a, da, e, de, I, dI, L, dL, varpi, dvarpi, Omega, dOmega  (satuan: AU, derajat, per abad Julian dari J2000)
ELEMENTS = {
    'mercury': (0.38709927, 0.00000037, 0.20563593, 0.00001906, 7.00497902, -0.00594749, 252.25032350, 149472.67411175, 77.45779628, 0.16047689, 48.33076593, -0.12534081),
    'venus':   (0.72333566, 0.00000390, 0.00677672, -0.00004107, 3.39467605, -0.00078890, 181.97909950, 58517.81538729, 131.60246718, 0.00268329, 76.67984255, -0.27769418),
    'earth':   (1.00000261, 0.00000562, 0.01671123, -0.00004392, -0.00001531, -0.01294668, 100.46457166, 35999.37244981, 102.93768193, 0.32327364, 0.0, 0.0),
    'mars':    (1.52371034, 0.00001847, 0.09339410, 0.00007882, 1.84969142, -0.00813131, -4.55343205, 19140.30268499, -23.94362959, 0.44441088, 49.55953891, -0.29257343),
    'jupiter': (5.20288700, -0.00011607, 0.04838624, -0.00013253, 1.30439695, -0.00183714, 34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106),
    'saturn':  (9.53667594, -0.00125060, 0.05386179, -0.00050991, 2.48599187, 0.00193609, 49.95424423, 1222.49362201, 92.59887831, -0.41897216, 113.66242448, -0.28867794),
    'uranus':  (19.18916464, -0.00196176, 0.04725744, -0.00004397, 0.77263783, -0.00242939, 313.23810451, 428.48202785, 170.95427630, 0.40805281, 74.01692503, 0.04240589),
    'neptune': (30.06992276, 0.00026291, 0.00859048, 0.00005105, 1.77004347, 0.00035372, -55.12002969, 218.45945325, 44.96476227, -0.32241464, 131.78422574, -0.00508664),
}
PLANETS = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune']

# Bintang/gugus tetap (RA, Dec J2000 dalam derajat)
FIXED = {
    'm45': (56.75, 24.117),        # Pleiades
    'm44': (130.10, 19.667),       # Praesepe
    'sigma_sagittarii': (283.8164, -26.2967),   # Nunki
    'beta_tauri': (81.5730, 28.6074),           # Elnath
    'aldebaran': (68.980, 16.509),
    'regulus': (152.093, 11.967),
    'spica': (201.298, -11.161),
    'antares': (247.352, -26.432),
}

# Suku jarak Bulan (D, M, M', F, koefisien cos dalam 1e-3 km), Meeus tabel 47.A
_MOON_R = [
    (0, 0, 1, 0, -20905355), (2, 0, -1, 0, -3699111), (2, 0, 0, 0, -2955968), (0, 0, 2, 0, -569925),
    (0, 1, 0, 0, 48888), (0, 0, 0, 2, -3149), (2, 0, -2, 0, 246158), (2, -1, -1, 0, -152138),
    (2, 0, 1, 0, -170733), (2, -1, 0, 0, -204586), (0, 1, -1, 0, -129620), (1, 0, 0, 0, 108743),
    (0, 1, 1, 0, 104755), (2, 0, 0, -2, 10321), (0, 0, 1, -2, 79661), (0, 0, 1, 2, -34782),
    (4, 0, -1, 0, -23210), (0, 0, 3, 0, -21636), (4, 0, -2, 0, 24208), (2, 1, -1, 0, 30824),
    (2, 1, 0, 0, -8379), (1, 0, -1, 0, -16675), (1, 1, 0, 0, -12831), (2, -1, 1, 0, -10445),
    (2, 0, 2, 0, -11650), (4, 0, 0, 0, 14403), (2, 0, -3, 0, -7003), (0, 1, -2, 0, 10056),
    (2, -1, -2, 0, -9884), (1, 0, 1, 0, 5751), (2, -2, -1, 0, -4950), (2, 0, 1, -2, -4130),
]

rad, deg = math.radians, math.degrees


def tt(jd_ut: float) -> float:
    return jd_ut + DELTA_T_DAYS


def wrap180(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def _kepler(M_deg: float, e: float) -> float:
    M = rad(wrap180(M_deg))
    E = M + e * math.sin(M)
    for _ in range(12):
        E -= (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    return E


def helio(body: str, jd_tt: float):
    """Posisi heliosentris (AU), ekliptika J2000."""
    a0, da, e0, de, i0, di, l0, dl, w0, dw, o0, do = ELEMENTS[body]
    T = (jd_tt - 2451545.0) / 36525.0
    a, e, I = a0 + da * T, e0 + de * T, rad(i0 + di * T)
    L, wbar, Om = l0 + dl * T, w0 + dw * T, rad(o0 + do * T)
    w = rad(wbar) - Om
    E = _kepler(L - wbar, e)
    xp, yp = a * (math.cos(E) - e), a * math.sqrt(1 - e * e) * math.sin(E)
    cw, sw, cO, sO, cI, sI = math.cos(w), math.sin(w), math.cos(Om), math.sin(Om), math.cos(I), math.sin(I)
    x = (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp
    y = (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp
    z = (sw * sI) * xp + (cw * sI) * yp
    return x, y, z


def _eps(jd_tt: float) -> float:
    return 23.439291 - 0.0130042 * (jd_tt - 2451545.0) / 36525.0


def _precession_lon(jd_tt: float) -> float:
    T = (jd_tt - 2451545.0) / 36525.0
    return (5028.796195 * T + 1.1054348 * T * T) / 3600.0


def _planet_geo(body: str, jd_ut: float):
    """(lon, lat) ekliptika tanggal [derajat], jarak geosentris (AU), jarak heliosentris (AU)."""
    t = tt(jd_ut)
    earth = helio('earth', t)
    tau = 0.0
    for _ in range(3):                                   # koreksi waktu-cahaya
        p = helio(body, t - tau)
        v = (p[0] - earth[0], p[1] - earth[1], p[2] - earth[2])
        dist = math.sqrt(sum(c * c for c in v))
        tau = dist * LIGHT_DAY_PER_AU
    lon = deg(math.atan2(v[1], v[0])) + _precession_lon(t)
    lat = deg(math.asin(v[2] / dist))
    return ac.norm360(lon), lat, dist, math.sqrt(sum(c * c for c in p))


def moon_distance_km(jd_tt: float) -> float:
    T = ac.julian_centuries(jd_tt)
    D = rad(ac.norm360(297.8501921 + 445267.1114034 * T))
    M = rad(ac.norm360(357.5291092 + 35999.0502909 * T))
    Mp = rad(ac.norm360(134.9633964 + 477198.8675055 * T))
    F = rad(ac.norm360(93.2720950 + 483202.0175233 * T))
    E = 1 - 0.002516 * T - 0.0000074 * T * T
    s = sum(c * (E ** abs(m)) * math.cos(d * D + m * M + mp * Mp + f * F) for d, m, mp, f, c in _MOON_R)
    return 385000.56 + s / 1000.0


def ecl(body: str, jd_ut: float):
    """(lon, lat) ekliptika tanggal, derajat, geosentris."""
    if body == 'moon':
        t = tt(jd_ut)
        return ac.moon_longitude(t), ac.moon_latitude(t)
    if body == 'sun':
        return ac.sun_position(tt(jd_ut))['longitude'], 0.0
    if body in ELEMENTS:
        lon, lat, _, _ = _planet_geo(body, jd_ut)
        return lon, lat
    if body in FIXED:
        ra0, dec0 = FIXED[body]
        e0 = rad(23.4392911)
        lon = deg(math.atan2(math.sin(rad(ra0)) * math.cos(e0) + math.tan(rad(dec0)) * math.sin(e0), math.cos(rad(ra0))))
        lat = deg(math.asin(math.sin(rad(dec0)) * math.cos(e0) - math.cos(rad(dec0)) * math.sin(e0) * math.sin(rad(ra0))))
        return ac.norm360(lon + _precession_lon(tt(jd_ut))), lat
    raise KeyError(body)


def eq(body: str, jd_ut: float):
    """(RA, Dec) geosentris tanggal, derajat."""
    lon, lat = ecl(body, jd_ut)
    e = rad(_eps(tt(jd_ut)))
    l, b = rad(lon), rad(lat)
    ra = deg(math.atan2(math.sin(l) * math.cos(e) - math.tan(b) * math.sin(e), math.cos(l)))
    dec = deg(math.asin(math.sin(b) * math.cos(e) + math.cos(b) * math.sin(e) * math.sin(l)))
    return ac.norm360(ra), dec


def separation(a_ra, a_dec, b_ra, b_dec) -> float:
    a1, d1, a2, d2 = rad(a_ra), rad(a_dec), rad(b_ra), rad(b_dec)
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(a1 - a2)
    return deg(math.acos(max(-1.0, min(1.0, c))))


def sep(a: str, b: str, jd_ut: float) -> float:
    return separation(*eq(a, jd_ut), *eq(b, jd_ut))


def topo_moon(jd_ut: float, lat: float, lon: float):
    """(RA, Dec) topocentris Bulan untuk pengamat di permukaan laut (Meeus bab 40)."""
    ra, dec = eq('moon', jd_ut)
    dist = moon_distance_km(tt(jd_ut))
    sinpi = EARTH_RADIUS_KM / dist
    u = math.atan(0.99664719 * math.tan(rad(lat)))
    rho_s, rho_c = 0.99664719 * math.sin(u), math.cos(u)
    gmst = ac.norm360(280.46061837 + 360.98564736629 * (jd_ut - 2451545.0))
    H = rad(ac.norm360(gmst + lon) - ra)
    d_r = rad(dec)
    dra = math.atan2(-rho_c * sinpi * math.sin(H), math.cos(d_r) - rho_c * sinpi * math.cos(H))
    dec_t = math.atan2((math.sin(d_r) - rho_s * sinpi) * math.cos(dra), math.cos(d_r) - rho_c * sinpi * math.cos(H))
    return ac.norm360(ra + deg(dra)), deg(dec_t)


def moon_semidiameter_deg(jd_ut: float) -> float:
    return deg(math.asin(0.2725076 * EARTH_RADIUS_KM / moon_distance_km(tt(jd_ut))))


def phase_angle_and_mag(body: str, jd_ut: float):
    """Sudut fase i (derajat) dan magnitudo visual (Venus/Merkurius, rumus Astronomical Almanac)."""
    _, _, delta, r = _planet_geo(body, jd_ut)
    R = math.sqrt(sum(c * c for c in helio('earth', tt(jd_ut))))
    cos_i = (r * r + delta * delta - R * R) / (2 * r * delta)
    i = deg(math.acos(max(-1.0, min(1.0, cos_i))))
    if body == 'venus':
        m = -4.40 + 5 * math.log10(r * delta) + 0.0009 * i + 0.000239 * i ** 2 - 0.00000065 * i ** 3
    elif body == 'mercury':
        m = -0.42 + 5 * math.log10(r * delta) + 0.0380 * i - 0.000273 * i ** 2 + 0.000002 * i ** 3
    else:
        m = None
    return i, m


def moon_horizontal_parallax_deg(jd_ut: float) -> float:
    return deg(math.asin(EARTH_RADIUS_KM / moon_distance_km(tt(jd_ut))))


SUN_SD_1AU_DEG = 959.63 / 3600.0      # semidiameter Matahari pada 1 AU
SUN_PARALLAX_1AU_DEG = 8.794 / 3600.0


def _sun_distance_au(jd_ut: float) -> float:
    return math.sqrt(sum(c * c for c in helio('earth', tt(jd_ut))))


def sun_semidiameter_deg(jd_ut: float) -> float:
    return SUN_SD_1AU_DEG / _sun_distance_au(jd_ut)


def sun_parallax_deg(jd_ut: float) -> float:
    return SUN_PARALLAX_1AU_DEG / _sun_distance_au(jd_ut)


def apparent_mag(body: str, jd_ut: float):
    """Magnitudo tampak benda (planet, Bulan, bintang/gugus tetap). None untuk Matahari."""
    if body in MG.FIXED_MAG:
        return MG.FIXED_MAG[body]
    if body == 'moon':
        return MG.moon_mag(wrap180(ecl('moon', jd_ut)[0] - ecl('sun', jd_ut)[0]) % 360.0)
    if body in ELEMENTS and body != 'earth':
        _, _, delta, r = _planet_geo(body, jd_ut)
        R = _sun_distance_au(jd_ut)
        i, _ = phase_angle_and_mag(body, jd_ut) if body in ('mercury', 'venus') else (None, None)
        if i is None:
            cos_i = (r * r + delta * delta - R * R) / (2 * r * delta)
            i = deg(math.acos(max(-1.0, min(1.0, cos_i))))
        ra, dec = eq(body, jd_ut)
        return MG.planet_mag(body, r, delta, i, ra, dec)
    return None


# ---------------------------------------------------------------------------
# API BATCH (vektor). Pada ephem_lite hanya melingkar skalar; pada Skyfield benar-benar vektor (jauh lebih cepat).
# ---------------------------------------------------------------------------
HAS_BATCH = True


def eq_many(body: str, jds):
    out = np.array([eq(body, float(j)) for j in np.asarray(jds, float)]).reshape(-1, 2)
    return out[:, 0], out[:, 1]


def ecl_many(body: str, jds):
    out = np.array([ecl(body, float(j)) for j in np.asarray(jds, float)]).reshape(-1, 2)
    return out[:, 0], out[:, 1]


def moon_radii_many(jds):
    """(semidiameter, paralaks horizontal) Bulan dalam derajat untuk larik JD."""
    jds = np.asarray(jds, float)
    return (np.array([moon_semidiameter_deg(float(j)) for j in jds]),
            np.array([moon_horizontal_parallax_deg(float(j)) for j in jds]))


def separation_many(a_ra, a_dec, b_ra, b_dec):
    a1, d1, a2, d2 = (np.radians(np.asarray(x, float)) for x in (a_ra, a_dec, b_ra, b_dec))
    c = np.sin(d1) * np.sin(d2) + np.cos(d1) * np.cos(d2) * np.cos(a1 - a2)
    return np.degrees(np.arccos(np.clip(c, -1.0, 1.0)))
