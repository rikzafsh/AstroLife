"""Kalender: Hijriah aritmetis (julian_day.js: jdkh/khcjdn/cjdnkh) dan Jawa Mataraman/Sultan Agungan (kalender_jawa.js)."""
from __future__ import annotations

import math

from .core import jdkm, kmjd, mod

HARI_H = ('Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Ahad')
PASARAN = ('Legi', 'Pahing', 'Pon', 'Wage', 'Kliwon')
BULAN_H = ('Muharam', 'Safar', 'Rabiulawal', 'Rabiulakhir', 'Jumadilawal', 'Jumadilakhir', 'Rajab',
           'Syakban', 'Ramadan', 'Syawal', 'Zulkaidah', 'Zulhijah')   # ejaan KBBI

# epoch: 1 = Kamis 15 Juli 622 M; 2 = Jumat 16 Juli 622 M.  kabisat (hCalL): 1 = 2,5,7,10,13,15,18,21,24,26,29;
# 2 = 2,5,7,10,13,16,18,21,24,26,29 (bawaan); 3 = 2,5,8,10,13,16,19,21,24,27,29; 4 = 2,5,8,11,13,16,19,21,24,27,30
_EPOCH = {1: 1948439.0}
_KABISAT = {1: 15.0, 2: 14.0, 3: 11.0, 4: 9.0}


def _epoch(e): return _EPOCH.get(e, 1948440.0)
def _kab(l): return _KABISAT.get(l, 14.0)


def cjdn_ke_hijri(cjdn: int, epoch: int = 2, kabisat: int = 2) -> dict:
    """Nomor hari kronologis (CJDN) → tanggal Hijriah aritmetis + nama hari & pasaran."""
    hari = cjdn - _epoch(epoch)
    x2 = math.floor((30.0 * hari + 29.0 - _kab(kabisat)) / 10631)
    r2 = mod(30 * hari + 29 - _kab(kabisat), 10631)
    x1 = math.floor((11 * math.floor(r2 / 30) + 5) / 325)
    r1 = mod(11 * math.floor(r2 / 30) + 5, 325)
    tgl, bln, thn = math.floor(r1 / 11) + 1, int(x1) + 1, int(x2) + 1
    no_hr = int(cjdn - 7 * math.floor(cjdn / 7))
    no_ps = int(cjdn - 5 * math.floor(cjdn / 5))
    return {'tgl': tgl, 'bln': bln, 'thn': thn, 'nama_bulan': BULAN_H[bln - 1], 'hari': HARI_H[no_hr], 'pasaran': PASARAN[no_ps]}


def hijri_dari_jd(jd: float, tz: float = 7.0, epoch: int = 2, kabisat: int = 2) -> dict:
    """JD (UT) → tanggal Hijriah aritmetis pada zona tz."""
    return cjdn_ke_hijri(math.floor(jd + 0.5 + tz / 24), epoch, kabisat)


def hijri_ke_cjdn(tgl: int, bln: int, thn: int, epoch: int = 2, kabisat: int = 2) -> int:
    hari = (math.floor((10631 * thn - 10631 + _kab(kabisat)) / 30) + math.floor((325 * bln - 320) / 11) + (tgl - 1))
    return int(hari + _epoch(epoch))


def hijri_ke_masehi(tgl: int, bln: int, thn: int, epoch: int = 2, kabisat: int = 2) -> dict:
    """Tanggal Hijriah aritmetis → tanggal Masehi (hari yang sama dengan CJDN)."""
    cjdn = hijri_ke_cjdn(tgl, bln, thn, epoch, kabisat)
    m = jdkm(cjdn - 0.5, 0.0)
    return {'tgl': m['tgl'], 'bln': m['bln'], 'thn': m['thn'], 'hari': m['hari'], 'bulan': m['bulan'], 'cjdn': cjdn}


# ── Kalender Jawa (Sultan Agungan, kurup/windu) ─────────────────────
_AMBAL_HARI, _AMBAL_KURUP, _AMBAL_TAHUN = 765433, 18, 2160
NAMA_BULAN_JAWA = ('Sura', 'Sapar', 'Mulud', 'Bakda Mulud', 'Jumadilawal', 'Jumadilakir', 'Rejeb', 'Ruwah', 'Pasa',
                   'Sawal', 'Sela', 'Besar')
NAMA_TAHUN_JAWA = ('Alip', 'Ehé', 'Jimawal', 'Jé', 'Dal', 'Bé', 'Wawu', 'Jimakir')


def _js_round(x: float) -> int:
    return math.floor(x + 0.5)           # Math.round JS: pembulatan ke atas pada .5


def jd_ke_jawa(jd: float) -> dict:
    """JD → {tahun, bulan, tanggal} Jawa (kalender hitung Sultan Agungan, tahun Jawa = Saka-Jawa)."""
    a = math.floor(jd) + 0.5 - 1917963.5
    b = math.floor(a / _AMBAL_HARI)
    c = a - b * _AMBAL_HARI
    d = math.floor(c / 42524) - math.floor(c / 42524 / _AMBAL_KURUP)
    e = c - d * 42524
    f = math.floor(e / 2835)
    g = e - 2835 * f
    h = math.floor(((g - math.floor(g / 2834)) / 354.36667) + 0.0013)
    i = g - _js_round(h * 354.36667)
    j = math.floor((i - math.floor(i / 354)) / 29.5)
    tgl = i - _js_round(j * 29.5) + 1
    thn = b * _AMBAL_TAHUN + d * 120 + f * 8 + h + 427
    return {'tahun': int(thn), 'bulan': int(j + 1), 'tanggal': int(tgl)}


def no_tahun_jawa(tahun: int) -> int:
    """Urutan tahun dalam windu 1..8 (1 = Alip)."""
    return ((tahun - 3) % 8) + 1


def jawa_ke_jd(tgl: int, bln: int, thn: int) -> float:
    a = math.floor((thn - 427) / _AMBAL_TAHUN)
    b = math.floor(((thn - 427) - a * _AMBAL_TAHUN) / 120)
    c = math.floor(((thn - 427) - (a * _AMBAL_TAHUN + b * 120)) / 8)
    d = (thn - 427) - a * _AMBAL_TAHUN - b * 120 - c * 8
    e = bln - 1
    return 1917962.5 + a * _AMBAL_HARI + b * 42524 + c * 2835 + _js_round(d * 354.35) + _js_round(e * 29.5) + tgl


def jawa_info(jd: float) -> dict:
    j = jd_ke_jawa(jd)
    n = no_tahun_jawa(j['tahun'])
    return {**j, 'nama_bulan': NAMA_BULAN_JAWA[j['bulan'] - 1], 'nama_tahun': NAMA_TAHUN_JAWA[n - 1], 'no_tahun_windu': n}
