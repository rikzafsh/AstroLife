"""Arah & jarak kiblat, rasydulqiblat (tahunan, antipoda, harian), istiwa & sepertiga malam.
Port arah_kiblat.js dan pelengkap_service.js (Matahari saja; rasydul Bulan belum diport)."""
from __future__ import annotations

import math

from .core import Sun, delta_t, deg, jdkm, kmjd, mod, rad
from .salat import METODE, NORMAL, PrayerMethod, WaktuSalat

LAT_KABAH = 21.0 + 25.0 / 60.0 + 21.02 / 3600.0
LON_KABAH = 39.0 + 49.0 / 60.0 + 34.27 / 3600.0


def arah_bola(glon, glat) -> float:
    a, b, c = 90.0 - glat, 90.0 - LAT_KABAH, glon - LON_KABAH
    sb = math.sin(rad(b)) * math.sin(rad(c))
    cb = math.cos(rad(b)) * math.sin(rad(a)) - math.cos(rad(a)) * math.sin(rad(b)) * math.cos(rad(c))
    return mod(360.0 - deg(math.atan2(sb, cb)), 360.0)


def arah_elipsoid(glon, glat) -> float:
    e = 0.0066943800229
    kp = deg(math.atan((1 - e) * math.tan(rad(LAT_KABAH))))
    pp = deg(math.atan((1 - e) * math.tan(rad(glat))))
    a, b, c = 90.0 - pp, 90.0 - kp, glon - LON_KABAH
    sb = math.sin(rad(b)) * math.sin(rad(c))
    cb = math.cos(rad(b)) * math.sin(rad(a)) - math.cos(rad(a)) * math.sin(rad(b)) * math.cos(rad(c))
    return mod(360.0 - deg(math.atan2(sb, cb)), 360.0)


def vincenty(glon, glat, hasil: str = 'PtoQ') -> float:
    """hasil: 'PtoQ' (arah kiblat dari lokasi), 'QtoP' (azimut awal dari Ka'bah), 'Dist' (jarak, meter)."""
    f, ae, be = 1.0 / 298.257223563, 6378137.0, 6356752.314245180
    u1 = math.atan((1 - f) * math.tan(rad(LAT_KABAH)))
    u2 = math.atan((1 - f) * math.tan(rad(glat)))
    l0 = rad(glon - LON_KABAH)
    lam = l0
    it = 0
    while True:
        it += 1
        lam0 = lam
        c_sig = math.sin(u1) * math.sin(u2) + math.cos(u1) * math.cos(u2) * math.cos(lam)
        s_sig = math.sqrt((math.cos(u2) * math.sin(lam)) ** 2 +
                          (math.cos(u1) * math.sin(u2) - math.sin(u1) * math.cos(u2) * math.cos(lam)) ** 2)
        sigma = math.atan2(s_sig, c_sig)
        s_al = math.cos(u1) * math.cos(u2) * math.sin(lam) / s_sig
        c2_al = 1.0 - s_al ** 2
        c2sm = c_sig - 2.0 * math.sin(u1) * math.sin(u2) / c2_al
        c = f / 16.0 * c2_al * (4.0 + f * (4.0 - 3.0 * c2_al))
        lam = l0 + (1.0 - c) * f * s_al * (sigma + c * s_sig * (c2sm + c * c_sig * (-1.0 + 2.0 * c2sm ** 2)))
        if not (abs(lam - lam0) > 1e-12 and it < 100):
            break
    al1 = math.atan2(math.cos(u2) * math.sin(lam), math.cos(u1) * math.sin(u2) - math.sin(u1) * math.cos(u2) * math.cos(lam))
    al2 = math.atan2(math.cos(u1) * math.sin(lam), -math.sin(u1) * math.cos(u2) + math.cos(u1) * math.sin(u2) * math.cos(lam))
    up2 = c2_al * (ae ** 2 - be ** 2) / be ** 2
    a = 1 + up2 / 16384 * (4096 + up2 * (-768 + up2 * (320 - 175 * up2)))
    b = up2 / 1024 * (256 + up2 * (-128 + up2 * (74 - 47 * up2)))
    d_sig = b * s_sig * (c2sm + 0.25 * b * (c_sig * (-1 + 2 * c2sm ** 2) -
                                           1 / 6 * b * c2sm * (-3 + 4 * s_sig ** 2) * (-3 + 4 * c2sm ** 2)))
    if hasil == 'QtoP':
        return mod(deg(al1), 360.0)
    if hasil == 'Dist':
        return be * a * (sigma - d_sig)
    return mod(180 + deg(al2), 360.0)


def jarak_bola_km(glon, glat) -> float:
    d = deg(math.acos(math.sin(rad(glat)) * math.sin(rad(LAT_KABAH)) +
                      math.cos(rad(glat)) * math.cos(rad(LAT_KABAH)) * math.cos(rad(LON_KABAH - glon))))
    return 6378.137 * d / 57.2957795


def arah_kiblat(glon, glat, metode: str = 'vincenty') -> float:
    return {'bola': arah_bola, 'elipsoid': arah_elipsoid}.get(metode, lambda lo, la: vincenty(lo, la, 'PtoQ'))(glon, glat)


# ── rasydulqiblat tahunan (Matahari di zenit/nadir Ka'bah) ───────────
def _peristiwa_tahunan(tahun, tz, opt, lintang, jam0):
    """Port rashdulQiblat/antipodaKabah: cari hari dengan |lintang − deklinasi| minimum, transit di meridian Ka'bah."""
    sn = Sun()
    tz_k = 3.0
    trs = [jam0, jam0, jam0]
    jd_hasil = 0.0
    for n in range(1, 13):
        for i in range(1, 32):
            for _ in range(3):
                for k in range(3):
                    jd0 = kmjd(i + k, n, tahun, trs[k], tz_k)
                    jde = jd0 + delta_t(jd0) / 86400.0
                    trs[k] = jam0 - sn.equation_of_time(jde, 0.0) - (LON_KABAH - tz_k * 15) / 15
            jds = [kmjd(i + k, n, tahun, trs[k], tz_k) for k in range(3)]
            dl = [abs(lintang - sn.declination(j + delta_t(j) / 86400.0, 0.0)) for j in jds]
            if dl[0] > dl[1] and dl[1] < dl[2]:
                jd_hasil = jds[1]
                if opt == 1:
                    return _hasil(sn, jd_hasil, tz, lintang)
                break                       # opt 2: lanjut ke bulan berikutnya (hasil terakhir dipakai)
    return _hasil(sn, jd_hasil, tz, lintang)


def _hasil(sn, jd, tz, lintang):
    dm = sn.declination(jd, 0.0)
    h = 90.0 - abs(lintang - dm)
    return {'jd': jd, 'jam_des': jdkm(jd, tz)['jam_des'], 'tinggi': h if lintang > 0 else -h, 'deklinasi': dm}


def rasydulqiblat(tahun, tz, opt: int = 1) -> dict:
    """opt 1: Rasydulqiblat 1 (±28 Mei); opt 2: Rasydulqiblat 2 (±15/16 Juli). jd = JD UT."""
    return _peristiwa_tahunan(tahun, tz, opt, LAT_KABAH, 12.0)


def antipoda_kabah(tahun, tz, opt: int = 1) -> dict:
    """Matahari di nadir Ka'bah (zenit antipoda)."""
    return _peristiwa_tahunan(tahun, tz, opt, -LAT_KABAH, 24.0)


def bayangan_kiblat_harian(glon, glat, tgl, bln, thn, tz, azimut_kiblat: str = 'bola', opt: int = 1):
    """Jam (desimal, zona tz) bayangan tegak menuju kiblat — rumus pustaka asli (bayanganQiblatHarian); None bila tak ada."""
    sn = Sun()
    az = {'elipsoid': arah_elipsoid, 'vincenty': lambda lo, la: vincenty(lo, la, 'PtoQ')}.get(azimut_kiblat.lower(), arah_bola)(glon, glat)
    bq = 12.0
    for _ in range(3):
        jd = kmjd(tgl, bln, thn, bq, tz)
        jde = jd + delta_t(jd) / 86400.0
        dm = sn.declination(jde, 0.0)
        e = sn.equation_of_time(jde, 0.0)
        b = 90 - glat
        p = deg(math.atan(1 / (math.cos(rad(b)) * math.tan(rad(az)))))
        cos_arg = math.tan(rad(dm)) * math.tan(rad(b)) * math.cos(rad(p))
        if cos_arg < -1.0 or cos_arg > 1.0:
            return None
        ca = deg(math.acos(cos_arg))
        if opt == 1:
            bq = mod(-(p - ca) / 15 + (12 - e) + (tz * 15 - glon) / 15, 24.0)
        elif opt == 2:
            bq = mod(-(p + ca) / 15 + (12 - e) + (tz * 15 - glon) / 15, 24.0)
        else:
            return None
    return mod(bq, 24.0)


# ── pelengkap: istiwa, tafawut, sepertiga malam, rasydulqiblat harian ──
def _mod24(x):
    return ((x % 24) + 24) % 24


def kwd(glon, tz) -> float:
    return (glon - tz * 15) / 15


def istiwa(tgl, bln, thn, glon, glat, tz) -> dict:
    """Istiwa (zuhur mentah = 12 − e − KWD), tafawut (perata waktu e, jam), KWD, deklinasi & tinggi Matahari saat kulminasi."""
    sn = Sun()
    t = WaktuSalat().zuhur(tgl, bln, thn, glon, tz).time
    jd = kmjd(tgl, bln, thn, t, tz)
    dt = delta_t(jd)
    dek = sn.declination(jd, dt)
    return {'jam': t, 'jd': jd, 'tafawut': sn.equation_of_time(jd + delta_t(jd) / 86400, 0), 'kwd': kwd(glon, tz),
            'deklinasi': dek, 'tinggi': 90 - abs(glat - dek)}


def sepertiga_malam(tgl, bln, thn, glon, glat, elev, tz, metode: PrayerMethod = METODE['persatuanIslam']):
    ws = WaktuSalat()
    mg = ws.magrib(tgl, bln, thn, glon, glat, elev, tz)
    sb = ws.subuh(tgl, bln, thn, glon, glat, tz, metode.hm_subuh)
    if not mg.is_normal or not sb.is_normal:
        return None
    lama = _mod24(sb.time - mg.time)
    return {'magrib': mg.time, 'subuh': sb.time, 'lama': lama, 'akhirSepertigaPertama': _mod24(mg.time + lama / 3),
            'tengahMalam': _mod24(mg.time + lama / 2), 'awalSepertigaTerakhir': _mod24(mg.time + 2 * lama / 3)}


def tinggi_azimut_matahari(jd, glat, glon) -> dict:
    """Tinggi & azimut (dari utara, searah jarum jam) Matahari geosentris pada JD UT."""
    sn = Sun()
    dt = delta_t(jd)
    dek = rad(sn.declination(jd, dt))
    ra = sn.right_ascension(jd, dt)
    H = rad(sn.last(jd, dt, glon) - ra)
    ph = rad(glat)
    alt = math.asin(math.sin(ph) * math.sin(dek) + math.cos(ph) * math.cos(dek) * math.cos(H))
    N = math.cos(ph) * math.sin(dek) - math.sin(ph) * math.cos(dek) * math.cos(H)
    E = -math.cos(dek) * math.sin(H)
    return {'tinggi': deg(alt), 'azimut': (deg(math.atan2(E, N)) + 360) % 360}


def rasydulqiblat_harian(tgl, bln, thn, glat, glon, tz, Q) -> list:
    """Jam saat azimut Matahari = Q (jenis 0) atau Q+180° (jenis 1: bayangan tegak menuju kiblat), Matahari di atas ufuk.
    Hasil: [{jenis, jam, tinggi, azimut}] urut jam (0–2 peristiwa)."""
    sn = Sun()
    out = []
    ph, q = rad(glat), rad(Q)
    for sg in (1, -1):
        t, last = 12.0, None
        for _ in range(12):
            jd = kmjd(tgl, bln, thn, t, tz)
            dt = delta_t(jd)
            de = rad(sn.declination(jd, dt))
            ist = 12 - sn.equation_of_time(jd + dt / 86400, 0) - (glon - tz * 15) / 15
            a = math.sin(ph) * math.sin(q) * math.cos(de)
            b = -math.cos(q) * math.cos(de)
            c = math.sin(q) * math.cos(ph) * math.sin(de)
            R = math.hypot(a, b)
            if R < 1e-12 or abs(c) > R:
                last = None
                break
            H = math.atan2(b, a) + sg * math.acos(c / R)
            hd = ((deg(H) + 540) % 360) - 180
            tn = ist + hd / 15
            last = (H, tn, de)
            if abs(tn - t) < 1e-7:
                break
            t = tn
        if last is None:
            continue
        H, tn, de = last
        N = math.cos(ph) * math.sin(de) - math.sin(ph) * math.cos(de) * math.cos(H)
        E = -math.cos(de) * math.sin(H)
        jenis = 0 if (E * math.sin(q) + N * math.cos(q)) > 0 else 1
        tinggi = deg(math.asin(max(-1, min(1, math.sin(ph) * math.sin(de) + math.cos(ph) * math.cos(de) * math.cos(H)))))
        if tinggi > -0.833:
            out.append({'jenis': jenis, 'jam': tn, 'tinggi': tinggi, 'azimut': (Q + (180 if jenis else 0)) % 360})
    return sorted(out, key=lambda e: e['jam'])
