"""
Islamic Astronomy & Timekeeping Service
=======================================
- Waktu salat (metode Kemenag RI dan MWL) dari posisi Matahari
- Arah kiblat (azimuth great-circle ke Ka'bah)
- Rasydulqiblat tahunan (Matahari di zenit Ka'bah) dan harian (azimuth Matahari = azimuth kiblat)
- Kalender Hijriah aritmetis: tanggal penting dan rekomendasi puasa sunah

Semua waktu keluaran memakai zona waktu lokal yang diberikan (default WIB = UTC+7).
"""
import math
from datetime import date, timedelta

from app.services import astro_core as ac
from app.services import calendar_service as cs

KAABA_LAT = 21.42255    # 21 derajat 25' 21.17" LU (acuan Kemenag)
KAABA_LON = 39.82620    # 39 derajat 49' 34.33" BT

METHODS = {
    'kemenag': {'nama': 'Kemenag RI', 'fajr': 20.0, 'isha': 18.0, 'ihtiyat_min': 2, 'imsak_min': 10},
    'mwl': {'nama': 'Muslim World League', 'fajr': 18.0, 'isha': 17.0, 'ihtiyat_min': 0, 'imsak_min': 10},
}

ZONA = {7: 'WIB', 8: 'WITA', 9: 'WIT'}


def suggest_timezone(lon: float) -> float:
    """Zona waktu standar Indonesia berdasarkan bujur; di luar Indonesia: bulatkan lon/15."""
    if 95 <= lon < 115:
        return 7.0
    if 115 <= lon < 130:
        return 8.0
    if 130 <= lon <= 141.5:
        return 9.0
    return float(round(lon / 15.0))


def _fmt(hours: float, with_seconds: bool = False) -> str:
    """Jam desimal -> HH:MM (dibulatkan ke menit terdekat) atau HH:MM:SS."""
    if hours is None or math.isnan(hours):
        return '--:--'
    total = hours % 24
    if with_seconds:
        s = int(round(total * 3600))
        s %= 86400
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    mins = int(round(total * 60)) % 1440
    return f"{mins // 60:02d}:{mins % 60:02d}"


# ---------------------------------------------------------------------------
# Kiblat
# ---------------------------------------------------------------------------
def qibla_azimuth(lat: float, lon: float) -> float:
    """Azimuth kiblat dari utara sejati searah jarum jam (derajat)."""
    p1, p2 = math.radians(lat), math.radians(KAABA_LAT)
    dl = math.radians(KAABA_LON - lon)
    y = math.sin(dl)
    x = math.cos(p1) * math.tan(p2) - math.sin(p1) * math.cos(dl)
    return ac.norm360(math.degrees(math.atan2(y, x)))


def qibla_distance_km(lat: float, lon: float) -> float:
    p1, p2 = math.radians(lat), math.radians(KAABA_LAT)
    dl = math.radians(KAABA_LON - lon)
    c = math.acos(max(-1.0, min(1.0, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl))))
    return 6371.0088 * c


def _compass(az: float) -> str:
    names = ['U', 'UTL', 'TL', 'TTL', 'T', 'TTG', 'TG', 'STG', 'S', 'SBD', 'BD', 'BBD', 'B', 'BBL', 'BL', 'UBL']
    return names[int((az + 11.25) % 360 // 22.5)]


# ---------------------------------------------------------------------------
# Posisi Matahari lokal
# ---------------------------------------------------------------------------
def _sun_at(jdn: int, ut_hours: float) -> dict:
    return ac.sun_position(ac.jd_from_jdn(jdn, ut_hours))


def _transit_local(jdn: int, lon: float, tz: float) -> float:
    """Waktu lokal (jam desimal) transit Matahari, iterasi 2x agar EoT akurat."""
    t_ut = 12.0 - lon / 15.0
    for _ in range(3):
        eot = _sun_at(jdn, t_ut)['eot_min']
        t_ut = 12.0 - lon / 15.0 - eot / 60.0
    return t_ut + tz


def _hour_angle(alt_deg: float, lat: float, dec: float):
    """Sudut jam (derajat) saat Matahari mencapai ketinggian alt_deg; None jika tidak tercapai."""
    cos_h = ((math.sin(math.radians(alt_deg)) - math.sin(math.radians(lat)) * math.sin(math.radians(dec)))
             / (math.cos(math.radians(lat)) * math.cos(math.radians(dec))))
    if cos_h < -1 or cos_h > 1:
        return None
    return math.degrees(math.acos(cos_h))


def _event_time(jdn, lat, lon, tz, alt, rising: bool, noon_local):
    """Waktu lokal saat Matahari melewati ketinggian alt; iterasi dengan deklinasi pada waktu kejadian."""
    t = noon_local - (6.0 if rising else -6.0)
    for _ in range(4):
        dec = _sun_at(jdn, t - tz)['declination']
        h = _hour_angle(alt, lat, dec)
        if h is None:
            return None
        t = noon_local - h / 15.0 if rising else noon_local + h / 15.0
    return t


def sun_altitude_azimuth(lat: float, lon: float, jdn: int, ut_hours: float) -> tuple:
    """(ketinggian, azimuth dari utara searah jarum jam) Matahari geometris."""
    sp = _sun_at(jdn, ut_hours)
    gha = ac.norm360(15.0 * (ut_hours - 12.0) + sp['eot_min'] / 4.0)   # GHA Matahari
    lha = math.radians(ac.norm360(gha + lon))                          # sudut jam lokal (barat positif)
    phi, dec = math.radians(lat), math.radians(sp['declination'])
    sin_alt = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(lha)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))
    y = -math.sin(lha) * math.cos(dec)
    x = math.cos(phi) * math.sin(dec) - math.sin(phi) * math.cos(dec) * math.cos(lha)
    az = ac.norm360(math.degrees(math.atan2(y, x)))
    return alt, az


# ---------------------------------------------------------------------------
# Waktu salat
# ---------------------------------------------------------------------------
def prayer_times(lat: float, lon: float, d: date, tz: float = None, elevation: float = 0.0,
                 method: str = 'kemenag') -> dict:
    if not -66 <= lat <= 66:
        raise ValueError('Lintang di luar jangkauan perhitungan (|lat| harus <= 66).')
    if method not in METHODS:
        raise ValueError('Metode tidak dikenal.')
    tz = suggest_timezone(lon) if tz is None else tz
    m = METHODS[method]
    ih = m['ihtiyat_min'] / 60.0
    jdn = ac.to_jdn(d.year, d.month, d.day)

    noon = _transit_local(jdn, lon, tz)
    dec_noon = _sun_at(jdn, noon - tz)['declination']
    dip = 0.0347 * math.sqrt(max(elevation, 0.0))
    horizon = -(0.8333 + dip)

    sunrise = _event_time(jdn, lat, lon, tz, horizon, True, noon)
    sunset = _event_time(jdn, lat, lon, tz, horizon, False, noon)
    fajr = _event_time(jdn, lat, lon, tz, -m['fajr'], True, noon)
    isha = _event_time(jdn, lat, lon, tz, -m['isha'], False, noon)
    dhuha = _event_time(jdn, lat, lon, tz, 4.5, True, noon)

    # Ashar: bayangan = tinggi benda + bayangan saat kulminasi (mazhab Syafii/Jumhur)
    asr_alt = math.degrees(math.atan(1.0 / (1.0 + math.tan(math.radians(abs(lat - dec_noon))))))
    asr = _event_time(jdn, lat, lon, tz, asr_alt, False, noon)

    def plus(t, minutes=None):
        if t is None:
            return None
        return t + (ih if minutes is None else minutes / 60.0)

    times = {
        'imsak': plus(fajr, -m['imsak_min'] + m['ihtiyat_min']),
        'subuh': plus(fajr),
        'terbit': plus(sunrise, -m['ihtiyat_min']),
        'dhuha': plus(dhuha),
        'dzuhur': plus(noon),
        'ashar': plus(asr),
        'maghrib': plus(sunset),
        'isya': plus(isha),
    }
    labels = {
        'imsak': 'Imsak', 'subuh': 'Subuh', 'terbit': 'Terbit (Syuruq)', 'dhuha': 'Dhuha',
        'dzuhur': 'Dzuhur', 'ashar': 'Ashar', 'maghrib': 'Maghrib', 'isya': 'Isya',
    }
    zona = ZONA.get(int(tz), f"UTC{tz:+g}") if tz == int(tz) else f"UTC{tz:+g}"
    return {
        'tanggal': d.isoformat(),
        'lokasi': {'lat': lat, 'lon': lon, 'elevasi_m': elevation},
        'zona': zona,
        'tz_offset': tz,
        'metode': m['nama'],
        'jadwal': [{'kunci': k, 'nama': labels[k], 'waktu': _fmt(v), 'jam_desimal': v} for k, v in times.items()],
        'kiblat': {
            'azimuth': round(qibla_azimuth(lat, lon), 2),
            'arah': _compass(qibla_azimuth(lat, lon)),
            'jarak_km': round(qibla_distance_km(lat, lon)),
        },
        'matahari': {'deklinasi': round(dec_noon, 3), 'eot_menit': round(_sun_at(jdn, noon - tz)['eot_min'], 2)},
        'catatan': ('Ihtiyat +2 menit (kecuali Terbit -2 menit). ' if method == 'kemenag' else '')
                   + 'Ashar: bayangan = tinggi benda + bayangan kulminasi. Maghrib/Terbit: tinggi Matahari -0,8333 derajat.',
    }


# ---------------------------------------------------------------------------
# Rasydulqiblat
# ---------------------------------------------------------------------------
def _angular_distance_to_kaaba(ut_hours: float, jdn: int) -> float:
    sp = _sun_at(jdn, ut_hours)
    sub_lon = -(15.0 * (ut_hours - 12.0) + sp['eot_min'] / 4.0)           # bujur titik subsolar (BT positif)
    sub_lon = (sub_lon + 180.0) % 360.0 - 180.0
    p1, p2 = math.radians(sp['declination']), math.radians(KAABA_LAT)
    dl = math.radians(sub_lon - KAABA_LON)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def annual_rasydulqiblat(year: int, tz: float = 7.0) -> list:
    """
    Dua kali setahun Matahari berada (hampir) tepat di zenit Ka'bah.
    Dicari dengan memindai tiap menit di sekitar waktu transit Makkah pada jendela tanggal
    yang memuat deklinasi Matahari = lintang Ka'bah.
    """
    events = []
    for label, (m0, d0, m1, d1) in {'I': (5, 24, 6, 3), 'II': (7, 11, 7, 21)}.items():
        best = None
        d = date(year, m0, d0)
        end = date(year, m1, d1)
        while d <= end:
            jdn = ac.to_jdn(d.year, d.month, d.day)
            center = 12.0 - KAABA_LON / 15.0
            # pindai +- 20 menit di sekitar transit kasar, resolusi 1 detik pada 2 tahap
            t = center - 0.4
            while t <= center + 0.4:
                dist = _angular_distance_to_kaaba(t, jdn)
                if best is None or dist < best[0]:
                    best = (dist, jdn, t)
                t += 1 / 60.0
            d += timedelta(days=1)
        dist, jdn, t = best
        lo, hi = t - 1 / 60.0, t + 1 / 60.0
        for _ in range(40):                                  # ternary search halus
            a, b = lo + (hi - lo) / 3, hi - (hi - lo) / 3
            if _angular_distance_to_kaaba(a, jdn) < _angular_distance_to_kaaba(b, jdn):
                hi = b
            else:
                lo = a
        t = (lo + hi) / 2
        dist = _angular_distance_to_kaaba(t, jdn)
        y, mo, dd, _ = ac.from_jdn(jdn)
        local_t = t + tz
        events.append({
            'peristiwa': f"Rasydulqiblat Tahunan {label}",
            'tanggal': date(y, mo, dd).isoformat(),
            'tanggal_teks': f"{dd} {cs.BULAN_MASEHI[mo - 1]} {y}",
            'waktu_utc': _fmt(t, with_seconds=True),
            'waktu_lokal': _fmt(local_t, with_seconds=True),
            'zona': ZONA.get(int(tz), f"UTC{tz:+g}"),
            'jarak_ke_zenit_deg': round(dist, 3),
            'catatan': 'Pada saat ini bayangan benda tegak di seluruh belahan Bumi yang sedang siang '
                       'menunjuk berlawanan dengan arah kiblat (bayangan = arah Matahari + 180 derajat).',
        })
    return events


def daily_rasydulqiblat(lat: float, lon: float, d: date, tz: float = None) -> dict:
    """
    Waktu harian ketika azimuth Matahari = azimuth kiblat (atau kebalikannya),
    sehingga bayangan tongkat segaris dengan arah kiblat.
    """
    tz = suggest_timezone(lon) if tz is None else tz
    jdn = ac.to_jdn(d.year, d.month, d.day)
    q = qibla_azimuth(lat, lon)
    q_opp = ac.norm360(q + 180.0)
    targets = {
        'menuju': (q_opp, 'Bayangan tongkat MENUJU arah kiblat (Matahari di arah berlawanan kiblat).'),
        'membelakangi': (q, 'Bayangan tongkat BERLAWANAN arah kiblat: arahkan ke arah ujung tongkat ke Matahari.'),
    }

    def diff(ut, target):
        alt, az = sun_altitude_azimuth(lat, lon, jdn, ut)
        return ((az - target + 180.0) % 360.0) - 180.0, alt

    events = []
    step = 1.0 / 60.0
    base_ut = -tz   # tengah malam lokal dalam UT
    for kind, (target, note) in targets.items():
        t = base_ut
        prev_d, prev_alt = diff(t, target)
        while t < base_ut + 24.0:
            t2 = t + step
            cur_d, cur_alt = diff(t2, target)
            if prev_d * cur_d < 0 and abs(prev_d) < 30 and abs(cur_d) < 30 and (prev_alt > 0 or cur_alt > 0):
                lo, hi = t, t2
                for _ in range(30):
                    mid = (lo + hi) / 2
                    if diff(mid, target)[0] * prev_d > 0:
                        lo = mid
                    else:
                        hi = mid
                tm = (lo + hi) / 2
                alt, az = sun_altitude_azimuth(lat, lon, jdn, tm)
                if alt > 2.0:   # abaikan saat Matahari terlalu rendah (bayangan tak terukur)
                    events.append({
                        'jenis': kind,
                        'waktu': _fmt(tm + tz, with_seconds=True),
                        'jam_desimal': tm + tz,
                        'tinggi_matahari': round(alt, 2),
                        'azimuth_matahari': round(az, 2),
                        'arah_bayangan': round(ac.norm360(az + 180.0), 2),
                        'keterangan': note,
                    })
            t, prev_d, prev_alt = t2, cur_d, cur_alt
    events.sort(key=lambda e: e['jam_desimal'])
    return {
        'tanggal': d.isoformat(),
        'lokasi': {'lat': lat, 'lon': lon},
        'zona': ZONA.get(int(tz), f"UTC{tz:+g}") if tz == int(tz) else f"UTC{tz:+g}",
        'azimuth_kiblat': round(q, 2),
        'arah_kiblat': _compass(q),
        'peristiwa': events,
        'catatan': None if events else
        'Pada tanggal ini Matahari tidak melintasi azimuth kiblat (atau kebalikannya) saat cukup tinggi di atas ufuk.',
    }


# ---------------------------------------------------------------------------
# Kalender Islam: tanggal penting dan puasa sunah
# ---------------------------------------------------------------------------
IMPORTANT_DATES = {
    (1, 1): 'Tahun Baru Islam 1 Muharram',
    (1, 10): "Hari Asyura (10 Muharram)",
    (3, 12): 'Maulid Nabi Muhammad SAW',
    (7, 27): "Isra Mi'raj",
    (8, 15): 'Nisfu Syaban',
    (9, 1): 'Awal Ramadan',
    (9, 17): 'Nuzulul Quran',
    (10, 1): 'Idulfitri 1 Syawal',
    (12, 9): 'Hari Arafah',
    (12, 10): 'Iduladha 10 Zulhijah',
}


def fasting_info(jdn: int) -> dict:
    """Status puasa untuk satu hari: wajib, haram, atau daftar puasa sunah yang berlaku."""
    y, m, d = cs.jdn_to_hijri(jdn)
    wd = ac.weekday_index(jdn)
    out = {'wajib': False, 'haram': None, 'sunah': []}
    if m == 9:
        out['wajib'] = True
        return out
    if (m, d) == (10, 1):
        out['haram'] = 'Hari Raya Idulfitri'
        return out
    if m == 12 and d in (10, 11, 12, 13):
        out['haram'] = 'Iduladha' if d == 10 else 'Hari Tasyrik'
        return out
    if wd == 1:
        out['sunah'].append('Senin')
    if wd == 4:
        out['sunah'].append('Kamis')
    if d in (13, 14, 15):
        out['sunah'].append('Ayyamul Bidh')
    if m == 12 and d == 9:
        out['sunah'].append('Arafah')
    if m == 1 and d in (9, 10):
        out['sunah'].append('Tasua' if d == 9 else 'Asyura')
    if m == 10 and 2 <= d <= 30:
        out['sunah'].append('Syawal (6 hari)')
    if m == 8 and d == 15:
        out['sunah'].append('Nisfu Syaban')
    return out


FASTING_NOTES = {
    'Senin': 'Puasa Senin: hari kelahiran dan awal wahyu Nabi SAW.',
    'Kamis': 'Puasa Kamis: hari diangkatnya amal.',
    'Ayyamul Bidh': 'Puasa 13, 14, 15 setiap bulan Hijriah (hari-hari Bulan purnama).',
    'Arafah': 'Puasa Arafah (9 Zulhijah) bagi yang tidak sedang berhaji.',
    'Tasua': 'Puasa Tasua (9 Muharram).',
    'Asyura': 'Puasa Asyura (10 Muharram).',
    'Syawal (6 hari)': 'Puasa enam hari di bulan Syawal setelah 1 Syawal (boleh berurutan/tidak).',
    'Nisfu Syaban': 'Sebagian ulama menganjurkan; termasuk Ayyamul Bidh bulan Syaban.',
}


def fasting_schedule(start: date, days: int = 30) -> list:
    rows = []
    for i in range(days):
        d = start + timedelta(days=i)
        jdn = ac.to_jdn(d.year, d.month, d.day)
        f = fasting_info(jdn)
        h = cs.hijri_info(jdn)
        evt = IMPORTANT_DATES.get((h['bulan'], h['tanggal']))
        if f['sunah'] or f['wajib'] or f['haram'] or evt:
            rows.append({
                'tanggal': d.isoformat(),
                'hari': cs.HARI[ac.weekday_index(jdn)],
                'hijriah': h['teks'],
                'status': 'wajib' if f['wajib'] else ('haram' if f['haram'] else 'sunah'),
                'jenis': f['sunah'],
                'keterangan': 'Puasa Ramadan (wajib)' if f['wajib'] else (f['haram'] and f"Dilarang berpuasa: {f['haram']}")
                              or '; '.join(FASTING_NOTES[x] for x in f['sunah']),
                'peristiwa': evt,
            })
    return rows


def hijri_calendar_month(year: int, month: int) -> dict:
    """Satu bulan Hijriah penuh (untuk tampilan kalender) dengan padanan Masehi."""
    if not 1 <= month <= 12:
        raise ValueError('Bulan Hijriah tidak valid.')
    n = cs.hijri_month_length(year, month)
    first = cs.hijri_to_jdn(year, month, 1)
    days = []
    for i in range(n):
        jdn = first + i
        gy, gm, gd, _ = ac.from_jdn(jdn)
        days.append({
            'hijri': i + 1,
            'masehi': date(gy, gm, gd).isoformat() if 1 <= gy <= 9999 else None,
            'hari': cs.HARI[ac.weekday_index(jdn)],
            'peristiwa': IMPORTANT_DATES.get((month, i + 1)),
            'puasa': fasting_info(jdn)['sunah'],
        })
    return {'tahun': year, 'bulan': month, 'nama_bulan': cs.BULAN_HIJRIAH[month - 1], 'panjang': n, 'hari': days}
