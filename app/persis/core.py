"""Inti astronomi (port dari persis-times-js, asalnya pustaka Dart `persis_times`, abusabda, MIT).

Isi: matematika dasar, Julian Day, ΔT (Espenak-Meeus), nutasi & kemiringan ekliptika, posisi Matahari (VSOP87D).
Semua sudut dalam derajat, jam dalam jam desimal, kecuali disebut lain. Perilaku (termasuk keanehan kecil
pada pustaka asli) dipertahankan agar hasilnya sama dengan versi JavaScript; lihat tests/test_persis.py.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from .nutation_tables import EPS_TERMS, PSI_TERMS

_DATA = Path(__file__).resolve().parent / '_data'


# ── matematika dasar ───────────────────────────────────────────────
def rad(x: float) -> float:
    return x * math.pi / 180.0


def deg(x: float) -> float:
    return x * 180.0 / math.pi


def _valid(v) -> bool:
    return v is not None and not math.isnan(v) and not math.isinf(v)


def mod(a: float, m: float) -> float:
    """a - m·floor(a/m); 0 bila masukan tidak sahir (seperti MathFunction.mod)."""
    if not _valid(a) or not _valid(m) or m == 0:
        return 0.0
    return a - m * math.floor(a / m)


# ── Julian Day ──────────────────────────────────────────────────────
def kmjd(tgl, bln, thn, jam_des: float = 0.0, tz: float = 0.0) -> float:
    """Kalender Masehi (Gregorian/Julian sebelum 15 Okt 1582) → JD (UT). jam_des = jam lokal pada zona tz."""
    dd = tgl + (jam_des - tz) / 24.0
    if bln > 2:
        mm, yy = bln, thn
    else:
        mm, yy = bln + 12, thn - 1
    if thn + bln / 100 + tgl / 10000 >= 1582.1015:
        aa = math.floor(yy / 100)
        bb = 2 - aa + math.floor(aa / 4)
    else:
        bb = 0.0
    return math.floor(365.25 * (yy + 4716)) + math.floor(30.6001 * (mm + 1)) + dd + bb - 1524.5


HARI = ('Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Ahad')
BULAN = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober',
         'November', 'Desember')


def jdkm(jd: float, tz: float = 0.0) -> dict:
    """JD → kalender Masehi pada zona tz: {tgl, bln, thn, jam_des, hari_no, hari, bulan}."""
    cjd = jd + 0.5 + tz / 24.0
    cjdn = math.floor(cjd)
    frac = cjd - cjdn
    alpha = math.floor((cjdn - 1867216.25) / 36524.25)
    beta = 1 + alpha - math.floor(alpha / 4)
    gc = beta if cjdn >= 2299161 else 0.0
    b = cjdn + gc + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    tgl = b - d - math.floor(30.6001 * e)
    bln = e - 1 if e < 14 else e - 13
    thn = c - 4716 if bln > 2 else c - 4715
    no_hr = cjdn - 7 * math.floor(cjdn / 7)
    return {'tgl': int(tgl), 'bln': int(bln), 'thn': int(thn), 'jam_des': frac * 24, 'cjdn': int(cjdn),
            'hari_no': int(no_hr), 'hari': HARI[int(no_hr)], 'bulan': BULAN[int(bln) - 1]}


def jc(jd: float) -> float:
    return (jd - 2451545) / 36525


def jm(t: float) -> float:
    return t / 10.0


# ── ΔT ──────────────────────────────────────────────────────────────
def delta_t(jd: float) -> float:
    """ΔT = TT − UT (detik), polinomial Espenak–Meeus seperti DynamicalTime.deltaT."""
    k = jdkm(jd, 0.0)
    dy = k['thn'] + (k['bln'] - 0.5) / 12
    if dy <= -500:
        ku = (dy - 1820) / 100
        dt = -20 + 32 * ku * ku
    elif dy <= 500:
        u = dy / 100
        dt = (10583.6 - 1014.41 * u + 33.78311 * u ** 2 - 5.952053 * u ** 3 - 0.1798452 * u ** 4
              + 0.022174192 * u ** 5 + 0.0090316521 * u ** 6)
    elif dy <= 1600:
        u = (dy - 1000) / 100
        dt = (1574.2 - 556.01 * u + 71.23472 * u ** 2 + 0.319781 * u ** 3 - 0.8503463 * u ** 4
              - 0.005050998 * u ** 5 + 0.0083572073 * u ** 6)
    elif dy <= 1700:
        u = (dy - 1600) / 100
        dt = 120 - 98.08 * u - 153.2 * u ** 2 + u ** 3 / 0.007129
    elif dy <= 1800:
        u = (dy - 1700) / 100
        dt = 8.83 + 16.03 * u - 59.285 * u ** 2 + 133.36 * u ** 3 - u ** 4 / 0.01174
    elif dy <= 1860:
        u = (dy - 1800) / 100
        dt = (13.72 - 33.2447 * u + 68.612 * u ** 2 + 4111.6 * u ** 3 - 37436 * u ** 4 + 121272 * u ** 5
              - 1699000 * u ** 6 + 87500 * u ** 7)
    elif dy <= 1900:
        u = (dy - 1860) / 100
        dt = 7.62 + 57.37 * u - 2517.54 * u ** 2 + 16806.68 * u ** 3 - 44736.24 * u ** 4 + u ** 5 / 0.00000233174
    elif dy <= 1920:
        u = (dy - 1900) / 100
        dt = -2.79 + 149.4119 * u - 598.939 * u ** 2 + 6196.6 * u ** 3
    elif dy <= 1941:
        u = (dy - 1920) / 100
        dt = 21.20 + 84.493 * u - 761.00 * u ** 2 + 2093.6 * u ** 3
    elif dy <= 1961:
        u = (dy - 1950) / 100
        dt = 29.07 + 40.7 * u - u ** 2 / 0.0233 + u ** 3 / 0.002547
    elif dy <= 1986:
        u = (dy - 1975) / 100
        dt = 45.45 + 106.7 * u - u ** 2 / 0.026 - u ** 3 / 0.000718
    elif dy <= 2005:
        u = (dy - 2000) / 100
        dt = 63.86 + 33.45 * u - 603.74 * u ** 2 + 1727.5 * u ** 3 + 65181.4 * u ** 4 + 237359.9 * u ** 5
    elif dy <= 2015:
        u = dy - 2005
        dt = 64.69 + 0.293 * u
    elif dy <= 3000:
        u = dy - 2015
        dt = 67.62 + 0.3645 * u + 0.0039755 * u * u
    else:
        dt = 0.0
    if dy < 1955 or dy > 2005:
        dt += -0.000012932 * (dy - 1955) ** 2
    return dt


# ── nutasi & kemiringan ─────────────────────────────────────────────
def _delaunay(t: float):
    t2, t3, t4 = t * t, t ** 3, t ** 4
    l = (485868.249036 + 1717915923.2178 * t + 31.8792 * t2 + 0.051635 * t3 - 0.00024470 * t4) / 3600.0
    lp = (1287104.79305 + 129596581.0481 * t - 0.5532 * t2 + 0.000136 * t3 - 0.00001149 * t4) / 3600.0
    f = (335779.526232 + 1739527262.8478 * t - 12.7512 * t2 - 0.001037 * t3 + 0.00000417 * t4) / 3600.0
    d = (1072260.70369 + 1602961601.2090 * t - 6.3706 * t2 + 0.006593 * t3 - 0.00003169 * t4) / 3600.0
    om = (450160.398036 - 6962890.5431 * t + 7.4722 * t2 + 0.007702 * t3 - 0.00005939 * t4) / 3600.0
    return tuple(rad(mod(x, 360.0)) for x in (l, lp, f, d, om))


def nutation_longitude(jd: float, dt: float) -> float:
    """Δψ (derajat)."""
    t = (jd + dt / 86400.0 - 2451545.0) / 36525.0
    l, lp, f, d, om = _delaunay(t)
    s = 0.0
    for (a, b, c, e, g), A, B, C in PSI_TERMS:
        arg = a * l + b * lp + c * f + e * d + g * om
        s += (A + B * t) * math.sin(arg) + C * math.cos(arg)
    return s / 36000000000.0


def nutation_obliquity(jd: float, dt: float) -> float:
    """Δε (derajat)."""
    t = (jd + dt / 86400.0 - 2451545.0) / 36525.0
    l, lp, f, d, om = _delaunay(t)
    s = 0.0
    for (a, b, c, e, g), A, B, C in EPS_TERMS:
        arg = a * l + b * lp + c * f + e * d + g * om
        s += (A + B * t) * math.cos(arg) + C * math.sin(arg)
    return s / 36000000000.0


def mean_obliquity(jd: float, dt: float) -> float:
    t = (jd + dt / 86400.0 - 2451545.0) / 36525.0
    u = t / 100.0
    return (23.0 + 26.0 / 60.0 + 21.448 / 3600.0 +
            (-4680.93 * u - 1.55 * u ** 2 + 1999.25 * u ** 3 - 51.38 * u ** 4 - 249.67 * u ** 5
             - 39.05 * u ** 6 + 7.12 * u ** 7 + 27.87 * u ** 8 + 5.79 * u ** 9 + 2.45 * u ** 10) / 3600.0)


def true_obliquity(jd: float, dt: float) -> float:
    return mean_obliquity(jd, dt) + nutation_obliquity(jd, dt)


# ── Matahari (VSOP87D) ──────────────────────────────────────────────
@lru_cache(maxsize=1)
def _vsop():
    z = np.load(_DATA / 'sun_vsop87d.npz')
    return {k: z[k] for k in z.files}


def _series(prefix: str, n: int, tau: float):
    """Σ_k tau^k · Σ_i A·cos(B + C·tau) untuk deret prefix0..prefix(n-1)."""
    v = _vsop()
    total = 0.0
    for k in range(n):
        a = v['sun_%s0%d' % (prefix, k)]
        total += float(np.sum(a[:, 0] * np.cos(a[:, 1] + a[:, 2] * tau))) * tau ** k
    return total


class Sun:
    """Posisi Matahari geosentris (VSOP87D + FK5 + nutasi + aberasi). Argumen (jd, dt): JD UT dan ΔT detik
    (JDE = jd + dt/86400). Hasil dipakai ulang bila (jd, dt) sama dengan pemanggilan terakhir."""

    def __init__(self):
        self._key = None
        self._lbr = None

    def _lbr_for(self, jd, dt):
        jde = jd + dt / 86400.0
        if self._key != jde:
            tau = jm(jc(jde))
            l = mod(deg(_series('l', 6, tau)), 360.0)
            b = deg(_series('b', 5, tau))
            r = _series('r', 6, tau)
            self._key, self._lbr = jde, (l, b, r)
        return self._lbr

    def earth_longitude(self, jd, dt): return self._lbr_for(jd, dt)[0]
    def earth_latitude(self, jd, dt): return self._lbr_for(jd, dt)[1]
    def radius(self, jd, dt): return self._lbr_for(jd, dt)[2]

    def aberration(self, jd, dt):
        """Aberrasi (detik busur)."""
        tau = jm(jc(jd + dt / 86400.0))
        terms = [(3548.330, 0, 0, 0), (118.568, 87.5287, 359993.7286, 0), (2.476, 85.0561, 719987.4571, 0),
                 (1.376, 27.8502, 4452671.1152, 0), (0.119, 73.1375, 450368.8564, 0),
                 (0.114, 337.2264, 329644.6718, 0), (0.086, 222.5400, 659289.3436, 0),
                 (0.078, 162.8136, 9224659.7915, 0), (0.054, 82.5823, 1079981.1857, 0),
                 (0.052, 171.5189, 225184.4282, 0), (0.034, 30.3214, 4092677.3866, 0),
                 (0.033, 119.8105, 337181.4711, 0), (0.023, 247.5418, 299295.6151, 0),
                 (0.023, 325.1526, 315559.5560, 0), (0.021, 155.1241, 675553.2846, 0),
                 (7.311, 333.4515, 359993.7286, 1), (0.305, 330.9814, 719987.4571, 1),
                 (0.010, 328.5170, 1079981.1857, 1), (0.309, 241.4518, 359993.7286, 2),
                 (0.021, 205.0482, 719987.4571, 2), (0.004, 297.8610, 4452671.1152, 2),
                 (0.010, 154.7066, 359993.7286, 3)]
        dl = 3548.330
        for a, ph, fr, p in terms[1:]:
            dl += a * tau ** p * math.sin(rad(ph + fr * tau))
        return -0.005775518 * self.radius(jd, dt) * dl

    def longitude(self, jd, dt):
        """Bujur tampak (derajat)."""
        l, b = self.earth_longitude(jd, dt), self.earth_latitude(jd, dt)
        theta = mod(l + 180, 360)
        beta = -b
        t = jc(jd + dt / 86400)
        lp = mod(theta - 1.397 * t - 0.00031 * t * t, 360.0)
        dth = (-0.09033 + 0.03916 * (math.cos(rad(lp)) + math.sin(rad(lp))) * math.tan(rad(beta))) / 3600
        return mod(theta + dth + nutation_longitude(jd, dt) + self.aberration(jd, dt) / 3600.0, 360.0)

    def latitude(self, jd, dt):
        l, b = self.earth_longitude(jd, dt), self.earth_latitude(jd, dt)
        theta = mod(l + 180, 360)
        t = jc(jd + dt / 86400)          # (JS memakai jce(); nilainya identik)
        lp = theta - 1.397 * t - 0.00031 * t * t
        return -b + 0.03916 * (math.cos(rad(lp)) - math.sin(rad(lp))) / 3600

    def right_ascension(self, jd, dt):
        lam, beta, eps = self.longitude(jd, dt), self.latitude(jd, dt), true_obliquity(jd, dt)
        return mod(deg(math.atan2(math.sin(rad(lam)) * math.cos(rad(eps)) - math.tan(rad(beta)) * math.sin(rad(eps)),
                                  math.cos(rad(lam)))), 360)

    def declination(self, jd, dt):
        lam, beta, eps = self.longitude(jd, dt), self.latitude(jd, dt), true_obliquity(jd, dt)
        return deg(math.asin(math.sin(rad(beta)) * math.cos(rad(eps)) +
                             math.cos(rad(beta)) * math.sin(rad(eps)) * math.sin(rad(lam))))

    def semidiameter(self, jd, dt):
        return (15 + 59.63 / 60) / self.radius(jd, dt) / 60

    @staticmethod
    def gmst(jd):
        t = jc(jd)
        return mod(280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t ** 2 - t ** 3 / 38710000, 360)

    def gast(self, jd, dt):
        return mod(self.gmst(jd) + nutation_longitude(jd, dt) * math.cos(rad(true_obliquity(jd, dt))), 360.0)

    def last(self, jd, dt, glon):
        return mod(self.gast(jd, dt) + glon, 360.0)

    def equation_of_time(self, jd, dt):
        """Perata waktu e (jam); positif bila Matahari lebih cepat dari waktu pertengahan."""
        tau = jm(jc(jd + dt / 86400))
        alpha = self.right_ascension(jd, dt)
        lo = mod(280.4664567 + 360007.6982779 * tau + 0.03032028 * tau ** 2 + tau ** 3 / 49931
                 - tau ** 4 / 15300 - tau ** 5 / 2000000, 360)
        e = lo - 0.0057183 - alpha + nutation_longitude(jd, dt) * math.cos(rad(true_obliquity(jd, dt)))
        if abs(e) * 4 < 20:
            return e / 15
        return e / 15 - 24 if e > 0 else e / 15 + 24
