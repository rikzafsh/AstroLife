"""Awal bulan Hijriah menurut kriteria MABIMS, Ummul Qura, Wujudul Hilal, dan KHGT/Turki (port calendar_service.js),
tanggal Hijriah tiap kriteria, dan tabel perbandingan kalender Hijriah & Jawa (tab_hilal.js)."""
from __future__ import annotations

import math
from functools import lru_cache

from .bulan import Moon
from .core import Sun, delta_t, jdkm, kmjd, mod
from .kalender import BULAN_H, cjdn_ke_hijri, jd_ke_jawa

_sn = Sun()
_mo = Moon(_sn)

# (lintang, bujur, zona)  — titik-titik MABIMS: 4 titik barat + poros tengah
_MABIMS = (
    (5 + 54 / 60 + 26.32 / 3600, 95 + 13 / 60 + 1.01 / 3600, 7), (-(5 + 22 / 60 + 28.80 / 3600), 102 + 13 / 60 + 54.86 / 3600, 7),
    (4 + 47 / 60 + 45.14 / 3600, 108 + 1 / 60 + 16.46 / 3600, 7), (-(7 + 4 / 60 + 26.1 / 3600), 106 + 31 / 60 + 53.71 / 3600, 7),
    (-(8 + 50 / 60 + 59.7 / 3600), 115 + 9 / 60 + 41.73 / 3600, 8), (4 + 9 / 60 + 9.62 / 3600, 117 + 42 / 60 + 3.47 / 3600, 8),
)
_TURKI = ((65, -166.7, -9), (54.47, -164.91, -9), (60, -139.6304, -9), (55.9182, -133.8442, -8), (50, -127.45, -8), (47, -124.21, -8),
          (34, -118.92, -8), (33, -117.33, -8), (20, -105.5555, -6), (14, -91.557, -6), (13, -87.62, -6), (9, -83.65, -6),
          (7.25, -80.9333, -5), (7, -77.692, -5), (3, -77.674, -5), (0, -80.1, -5), (-3, -79.83, -5), (-8, -79.235, -5),
          (-16, -74.0254, -4), (-24, -70.5235, -4), (-32, -71.5397, -4), (-40, -73.726, -4), (-44, -73.2683, -3),
          (-49, -75.6755, -3), (-55.9385, -67.2877, -3))
_KABAH = (21 + 25 / 60 + 21.02 / 3600, 39 + 49 / 60 + 34.27 / 3600)

NAMA_KRITERIA = ('MABIMS', 'Ummul Qura', 'Wujudul Hilal', 'KHGT (Turki)')


def _ijtimak(bln, thn):
    nm = _mo.ijtimak(bln, thn, 0.0)
    dt = delta_t(nm)
    return _mo.ijtimak(bln, thn, dt), dt


@lru_cache(maxsize=4096)
def awal_mabims(bln: int, thn: int) -> int:
    """CJDN hari pertama bulan (1 Muharram dst.) menurut MABIMS: tinggi >= 3° dan elongasi >= 6,4° di salah satu titik acuan."""
    nm, dt = _ijtimak(bln, thn)
    ir, jd_base, tz_base = 2, _sn.jd_ghurub(nm, _MABIMS[0][0], _MABIMS[0][1], 10.0, _MABIMS[0][2]), _MABIMS[0][2]
    for lat, lon, tz in _MABIMS:
        gs = _sn.jd_ghurub(nm, lat, lon, 10.0, tz)
        tinggi = _mo.altitude_topo(gs, dt, lon, lat, 10.0, 1010.0, 10.0, 'htoc')
        if _mo.elongasi(gs, dt) >= 6.4 and tinggi >= 3:
            ir, jd_base, tz_base = 1, gs, tz
            break
    return math.ceil(math.floor(jd_base + 0.5 + tz_base / 24.0) - 0.5 + tz_base / 24.0 + ir)


@lru_cache(maxsize=4096)
def awal_wujudul_hilal(bln: int, thn: int) -> int:
    """Wujudul Hilal (Yogyakarta): ijtimak sebelum Magrib dan Bulan di atas ufuk saat Magrib."""
    lon, lat, tz, elev = 110 + 21 / 60, -(7 + 48 / 60), 7, 30
    nm, dt = _ijtimak(bln, thn)
    gs = _sn.jd_ghurub(nm, lat, lon, elev, tz)
    tinggi = _mo.altitude_topo(gs, dt, lon, lat, 10.0, 1010.0, 10.0, 'htou')
    wh = 1 if (tinggi > 0 and nm < gs) else 2
    return math.ceil(math.floor(gs + 0.5 + tz / 24.0) - 0.5 + tz / 24.0 + wh)


@lru_cache(maxsize=4096)
def awal_ummul_qura(bln: int, thn: int) -> int:
    """Ummul Qura (Makkah): ijtimak sebelum Magrib dan Bulan terbenam sesudah Matahari terbenam."""
    lat, lon = _KABAH
    tz, elev = 3, 304
    nm, dt = _ijtimak(bln, thn)
    gs = _sn.jd_ghurub(nm, lat, lon, elev, tz)
    k = jdkm(gs, tz)
    bulan_set = _mo.terbit_terbenam(k['tgl'], k['bln'], k['thn'], lon, lat, elev, tz, 'SET', 2)
    matahari_set = k['jam_des']
    uq = 1 if (bulan_set > matahari_set and nm < gs) else 2
    return math.ceil(math.floor(gs + 0.5 + tz / 24.0) - 0.5 + tz / 24.0 + uq)


@lru_cache(maxsize=4096)
def awal_turki(bln: int, thn: int) -> int:
    """KHGT/Turki: elongasi >= 8° dan tinggi geosentris >= 5° di salah satu titik global sebelum 00 UT hari berikutnya
    (atau, bila sesudah itu, fajar Selandia Baru menentukan)."""
    nm0 = _mo.ijtimak(bln, thn, 0.0)
    dt = delta_t(nm0)
    nm = _mo.ijtimak(bln, thn, dt)
    jd0_next = math.floor(nm + 0.5) - 0.5 + 1.0
    ir, sebelum, sesudah = 2, False, False
    for lat, lon, tz in _TURKI:
        gs = _sn.jd_ghurub(nm0, lat, lon, 0, tz, ikut_zona=False)
        tinggi = _mo.altitude_geosentris(gs, dt, lon, lat)
        if _mo.elongasi(gs, dt) >= 8 and tinggi >= 5:
            if gs < jd0_next:
                sebelum, ir = True, 1
                break
            sesudah = True
    if not sebelum and sesudah:
        jd_fp = math.floor(nm + 0.5) - 0.5 + 17.0 / 24.0
        lon_nz, lat_nz, tz_nz = 174 + 48 / 60.0, -(41 + 19 / 60.0), 12.0
        kwd = (lon_nz - tz_nz * 15) / 15.0
        dek, eqt = _sn.declination(jd_fp, 0), _sn.equation_of_time(jd_fp, 0)
        r = math.radians
        ham = math.degrees(math.acos((math.sin(r(-18.0)) - math.sin(r(lat_nz)) * math.sin(r(dek))) / (math.cos(r(lat_nz)) * math.cos(r(dek)))))
        awf = 12.0 - eqt - ham / 15.0 - kwd
        jd_f_utc = math.floor(nm + 0.5) - 0.5 + mod(awf - 12.0, 24.0) / 24.0
        ir = 1 if nm < jd_f_utc else 2
    return math.floor(nm + 0.5) + ir


KRITERIA = {'mabims': awal_mabims, 'ummulqura': awal_ummul_qura, 'wujudulhilal': awal_wujudul_hilal, 'turki': awal_turki}


def hijri_kriteria(cjdn: int, kriteria: str, thn_h: int | None = None) -> dict:
    """Tanggal Hijriah untuk CJDN menurut kriteria (serviceKalenderHijriah*): {tgl, bln, thn, nama_bulan}; None bila di luar cakupan."""
    f = KRITERIA[kriteria]
    if thn_h is None:
        thn_h = cjdn_ke_hijri(cjdn)['thn']
    daftar = [(12, thn_h - 1)] + [(b, thn_h) for b in range(1, 13)] + [(1, thn_h + 1), (2, thn_h + 1)]
    awal = [f(b, y) for b, y in daftar]
    for i in range(len(awal) - 1):
        if awal[i] <= cjdn < awal[i + 1]:
            b, y = daftar[i]
            return {'tgl': cjdn - awal[i] + 1, 'bln': b, 'thn': y, 'nama_bulan': BULAN_H[b - 1], 'awal_cjdn': awal[i]}
    return None


def ramadan_malam_uq(tgl: int, bln: int, thn: int) -> bool:
    """Apakah hari berikutnya jatuh di Ramadan menurut kriteria Ummul Qura (pengganti Intl umalqura pada JS)."""
    cjdn = math.floor(kmjd(tgl + 1, bln, thn, 12, 0) + 0.5)
    h = hijri_kriteria(cjdn, 'ummulqura')
    return bool(h and h['bln'] == 9)


# ── tabel perbandingan (tab_hilal.js: hitungBanding) ────────────────
NAMA_BARIS = ('MABIMS', 'Ummul Qura', 'Wujudul Hilal', 'KHGT (Turki)', 'Aritmetis I', 'Aritmetis II', 'Aritmetis III', 'Aritmetis IV', 'Mataraman')
BULAN_JAWA = ('Sura', 'Sapar', 'Mulud', 'Bakda Mulud', 'Jumadilawal', 'Jumadilakir', 'Rejeb', 'Ruwah', 'Pasa', 'Sawal', 'Dulkangidah', 'Besar')


def _tabel_awal(f, k0, k1):
    t = []
    for k in range(k0 - 1, k1 + 2):
        t.append((f(k % 12 + 1, k // 12), k % 12 + 1, k // 12))
    return sorted(t)


def _dari_tabel(tb, c):
    k = -1
    for i, (ci, _, _) in enumerate(tb):
        if ci <= c:
            k = i
        else:
            break
    if k < 0 or k == len(tb) - 1:
        return None
    return {'d': c - tb[k][0] + 1, 'm': tb[k][1], 'y': tb[k][2]}


def banding(c0: int) -> dict:
    """Satu bulan Hijriah penuh (dari tanggal 1 paling awal hingga akhir bulan paling akhir di antara variasi) di sekitar CJDN c0.
    Baris: 4 kriteria hisab, 4 pola aritmetis, Mataraman. Hasil: {baris:[{nama, sel:[{d,m,y}|None]}], cjdn:[...], bulan}."""
    w0, w1 = c0 - 75, c0 + 75
    ar = lambda c, l: cjdn_ke_hijri(c, 2, l)
    ks = [ar(c, 2)['thn'] * 12 + ar(c, 2)['bln'] - 1 for c in range(w0 - 35, w1 + 36, 10)]
    k0, k1 = min(ks), max(ks)
    cs = list(range(w0, w1 + 1))
    peta = []
    for f in (awal_mabims, awal_ummul_qura, awal_wujudul_hilal, awal_turki):
        tb = _tabel_awal(f, k0, k1)
        peta.append([_dari_tabel(tb, c) for c in cs])
    for l in (1, 2, 3, 4):
        peta.append([{'d': ar(c, l)['tgl'], 'm': ar(c, l)['bln'], 'y': ar(c, l)['thn']} for c in cs])
    peta.append([{'d': j['tanggal'], 'm': j['bulan'], 'y': j['tahun']} for j in (jd_ke_jawa(c - 0.5) for c in cs)])
    ci = c0 - w0
    cnt = {}
    for r in peta:
        x = r[ci]
        if x:
            cnt[x['m']] = cnt.get(x['m'], 0) + 1
    m_t = max(cnt, key=lambda k: cnt[k])
    ca, cb = 10 ** 9, -10 ** 9
    for r in peta:
        best, i = None, 0
        while i < len(r):
            if r[i] and r[i]['m'] == m_t:
                j = i
                while j + 1 < len(r) and r[j + 1] and r[j + 1]['m'] == m_t and r[j + 1]['y'] == r[i]['y']:
                    j += 1
                dist = i - ci if ci < i else ci - j if ci > j else 0
                if best is None or dist < best[2]:
                    best = (i, j, dist)
                i = j + 1
            else:
                i += 1
        if best:
            ca, cb = min(ca, cs[best[0]]), max(cb, cs[best[1]])
    panjang = []
    for r in peta:
        o = {}
        for x in r:
            if x:
                k = x['y'] * 12 + x['m']
                o[k] = max(o.get(k, 0), x['d'])
        panjang.append(o)
    baris = []
    for v, r in enumerate(peta):
        sel = []
        for c in range(ca, cb + 1):
            x = r[c - w0]
            sel.append(None if not x else {**x, 'panjang_bulan': panjang[v].get(x['y'] * 12 + x['m'])})
        baris.append({'nama': NAMA_BARIS[v], 'jawa': v == 8, 'sel': sel})
    return {'bulan_acuan': m_t, 'cjdn_awal': ca, 'cjdn_akhir': cb, 'baris': baris}
