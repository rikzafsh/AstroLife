"""
Astro Core
==========
Fungsi dasar astronomi yang dipakai bersama oleh calendar_service dan islamic_service:

- Julian Day Number (kalender Gregorian + Julian untuk tanggal sebelum 15 Okt 1582)
- Posisi Matahari (Meeus, Astronomical Algorithms bab 25, akurasi ~0.01 derajat)
- Bujur ekliptika Bulan (Meeus bab 47, suku-suku utama, akurasi ~0.02 derajat)
- Ayanamsa Lahiri (konversi bujur tropis -> sidereal untuk Jyotisa)

Semua sudut dalam derajat, waktu dalam UT kecuali dinyatakan lain.
"""
import math

GREGORIAN_START_JDN = 2299161  # 15 Oktober 1582 (Gregorian) = 5 Oktober 1582 (Julian)

rad = math.radians
deg = math.degrees


def norm360(x: float) -> float:
    return x % 360.0


# ---------------------------------------------------------------------------
# Julian Day
# ---------------------------------------------------------------------------
def to_jdn(year: int, month: int, day: int, proleptic_gregorian: bool = False) -> int:
    """
    JDN integer (hari berawal tengah malam + 0.5 -> JDN adalah nilai pada tengah hari).
    Sebelum 15 Okt 1582 otomatis memakai kalender Julian (kecuali proleptic_gregorian=True).
    """
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn_greg = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    if proleptic_gregorian or jdn_greg >= GREGORIAN_START_JDN:
        return jdn_greg
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - 32083


def from_jdn(jdn: int, proleptic_gregorian: bool = False):
    """JDN -> (tahun, bulan, hari, nama_kalender). Tahun <= 0 mengikuti astronomical year numbering."""
    use_greg = proleptic_gregorian or jdn >= GREGORIAN_START_JDN
    if use_greg:
        a = jdn + 32044
        b = (4 * a + 3) // 146097
        c = a - 146097 * b // 4
    else:
        b = 0
        c = jdn + 32082
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day, ('Gregorian' if use_greg else 'Julian')


def jd_from_jdn(jdn: int, ut_hours: float = 0.0) -> float:
    """JD pada jam UT tertentu di hari kalender JDN (tengah malam = JDN - 0.5)."""
    return jdn - 0.5 + ut_hours / 24.0


def weekday_index(jdn: int) -> int:
    """0 = Minggu ... 6 = Sabtu."""
    return (jdn + 1) % 7


def julian_centuries(jd: float) -> float:
    return (jd - 2451545.0) / 36525.0


# ---------------------------------------------------------------------------
# Matahari
# ---------------------------------------------------------------------------
def sun_position(jd: float) -> dict:
    """Posisi tampak Matahari: bujur ekliptika, deklinasi, asensio rekta, equation of time."""
    T = julian_centuries(jd)
    L0 = norm360(280.46646 + 36000.76983 * T + 0.0003032 * T * T)
    M = norm360(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    Mr = rad(M)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(Mr)
         + (0.019993 - 0.000101 * T) * math.sin(2 * Mr)
         + 0.000289 * math.sin(3 * Mr))
    true_long = L0 + C
    omega = 125.04 - 1934.136 * T
    lam = true_long - 0.00569 - 0.00478 * math.sin(rad(omega))
    eps = 23.439291 - 0.0130042 * T + 0.00256 * math.cos(rad(omega))
    lam_r, eps_r = rad(lam), rad(eps)
    ra = norm360(deg(math.atan2(math.cos(eps_r) * math.sin(lam_r), math.cos(lam_r))))
    dec = deg(math.asin(math.sin(eps_r) * math.sin(lam_r)))
    # Equation of time (menit): E = L0 - 0.0057183 - RA, dinormalkan ke [-180,180]
    e_deg = L0 - 0.0057183 - ra
    e_deg = (e_deg + 180.0) % 360.0 - 180.0
    return {
        'longitude': norm360(lam),
        'declination': dec,
        'ra': ra,
        'eot_min': 4.0 * e_deg,
        'obliquity': eps,
    }


# ---------------------------------------------------------------------------
# Bulan
# ---------------------------------------------------------------------------
# (D, M, M', F, koefisien sin dalam 1e-6 derajat)
_MOON_LON_TERMS = [
    (0, 0, 1, 0, 6288774), (2, 0, -1, 0, 1274027), (2, 0, 0, 0, 658314), (0, 0, 2, 0, 213618),
    (0, 1, 0, 0, -185116), (0, 0, 0, 2, -114332), (2, 0, -2, 0, 58793), (2, -1, -1, 0, 57066),
    (2, 0, 1, 0, 53322), (2, -1, 0, 0, 45758), (0, 1, -1, 0, -40923), (1, 0, 0, 0, -34720),
    (0, 1, 1, 0, -30383), (2, 0, 0, -2, 15327), (0, 0, 1, 2, -12528), (0, 0, 1, -2, 10980),
    (4, 0, -1, 0, 10675), (0, 0, 3, 0, 10034), (4, 0, -2, 0, 8548), (2, 1, -1, 0, -7888),
    (2, 1, 0, 0, -6766), (1, 0, -1, 0, -5163), (1, 1, 0, 0, 4987), (2, -1, 1, 0, 4036),
    (2, 0, 2, 0, 3994), (4, 0, 0, 0, 3861), (2, 0, -3, 0, 3665), (0, 1, -2, 0, -2689),
    (2, 0, -1, 2, -2602), (2, -1, -2, 0, 2390), (1, 0, 1, 0, -2348), (2, -2, 0, 0, 2236),
]


def moon_longitude(jd: float) -> float:
    """Bujur ekliptika geosentris Bulan (derajat, tropis)."""
    T = julian_centuries(jd)
    Lp = norm360(218.3164477 + 481267.88123421 * T - 0.0015786 * T * T)
    D = rad(norm360(297.8501921 + 445267.1114034 * T - 0.0018819 * T * T))
    M = rad(norm360(357.5291092 + 35999.0502909 * T - 0.0001536 * T * T))
    Mp = rad(norm360(134.9633964 + 477198.8675055 * T + 0.0087414 * T * T))
    F = rad(norm360(93.2720950 + 483202.0175233 * T - 0.0036539 * T * T))
    E = 1 - 0.002516 * T - 0.0000074 * T * T
    total = 0.0
    for d, m, mp, f, coef in _MOON_LON_TERMS:
        ecc = E ** abs(m)
        total += coef * ecc * math.sin(d * D + m * M + mp * Mp + f * F)
    A1 = rad(119.75 + 131.849 * T)
    A2 = rad(53.09 + 479264.290 * T)
    total += 3958 * math.sin(A1) + 1962 * math.sin(rad(Lp) - F) + 318 * math.sin(A2)
    return norm360(Lp + total / 1e6)


def lahiri_ayanamsa(jd: float) -> float:
    """Ayanamsa Lahiri (aproksimasi linear: 23.8533 derajat pada J2000, presesi 50.29 detik busur/tahun)."""
    years = (jd - 2451545.0) / 365.25
    return 23.8533 + years * (50.29 / 3600.0)


def elongation(jd: float) -> float:
    """Elongasi Bulan - Matahari (0-360). 0 = bulan baru, 180 = purnama."""
    return norm360(moon_longitude(jd) - sun_position(jd)['longitude'])


def moon_phase_name(elong: float) -> str:
    names = ['Bulan Baru', 'Sabit Awal', 'Kuartal Pertama', 'Cembung Awal',
             'Purnama', 'Cembung Akhir', 'Kuartal Akhir', 'Sabit Akhir']
    return names[int(((elong + 22.5) % 360) // 45)]


def prev_new_moon(jd: float) -> float:
    """JD bulan baru (elongasi=0) terakhir sebelum jd (bisection, presisi ~1 menit)."""
    e = elongation(jd)
    lo = jd - (e / 12.190749) - 1.0   # laju elongasi rata-rata ~12.19 derajat/hari
    # pastikan elongasi di 'lo' berada tepat di akhir siklus sebelumnya
    hi = jd - (e / 12.190749) + 1.0
    # elong(lo) ~ 350-360, elong(hi) ~ 0-10 (wrap). Gunakan nilai bertanda dekat 0.
    def signed(t):
        v = elongation(t)
        return v - 360.0 if v > 180.0 else v
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if signed(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# Ketinggian Bulan (untuk menilai gangguan cahaya Bulan saat pengamatan)
# ---------------------------------------------------------------------------
def moon_latitude(jd: float) -> float:
    """Lintang ekliptika Bulan (derajat), suku utama Meeus bab 47 (akurasi ~0.1 derajat)."""
    T = julian_centuries(jd)
    D = rad(norm360(297.8501921 + 445267.1114034 * T))
    Mp = rad(norm360(134.9633964 + 477198.8675055 * T))
    F = rad(norm360(93.2720950 + 483202.0175233 * T))
    s = (5128122 * math.sin(F) + 280602 * math.sin(Mp + F) + 277693 * math.sin(Mp - F)
         + 173237 * math.sin(2 * D - F) + 55413 * math.sin(2 * D - Mp + F)
         + 46271 * math.sin(2 * D - Mp - F) + 32573 * math.sin(2 * D + F)
         + 17198 * math.sin(2 * Mp + F))
    return s / 1e6


def moon_altitude(jd: float, lat: float, lon: float) -> float:
    """Ketinggian topocentris Bulan (derajat) di lokasi; negatif = di bawah ufuk."""
    lam, beta = rad(moon_longitude(jd)), rad(moon_latitude(jd))
    eps = rad(sun_position(jd)['obliquity'])
    ra = math.atan2(math.sin(lam) * math.cos(eps) - math.tan(beta) * math.sin(eps), math.cos(lam))
    dec = math.asin(math.sin(beta) * math.cos(eps) + math.cos(beta) * math.sin(eps) * math.sin(lam))
    gmst = norm360(280.46061837 + 360.98564736629 * (jd - 2451545.0))
    lha = rad(norm360(gmst + lon) - norm360(deg(ra)))
    phi = rad(lat)
    alt = deg(math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(lha)))
    return alt - 0.95 * math.cos(rad(alt))        # paralaks horizontal ~0.95 derajat
