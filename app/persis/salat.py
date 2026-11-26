"""Waktu salat (port waktu_salat.js, prayer_method.js, salat_service.js, jadwal_service.js tanpa bagian Bulan)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .core import Sun, delta_t, deg, kmjd, mod, rad

NORMAL, UP, DOWN, BRIGHT, DARK, INVALID = 'normal', 'up', 'down', 'bright', 'dark', 'invalid'

KETERANGAN_STATUS = {
    UP: 'Matahari selalu di atas ufuk', DOWN: 'Matahari selalu di bawah ufuk',
    BRIGHT: 'Langit tidak cukup gelap (senja tak berakhir)', DARK: 'Matahari tidak mencapai sudut ini',
    INVALID: 'Tidak dapat dihitung',
}


@dataclass(frozen=True)
class SalatValue:
    time: Optional[float] = None      # jam desimal pada zona waktu masukan
    status: str = NORMAL

    @property
    def is_normal(self) -> bool:
        return self.status == NORMAL


@dataclass(frozen=True)
class PrayerMethod:
    key: str
    name: str
    hm_subuh: float
    hm_isya: float
    isya_menit: Optional[int] = None            # Isya berbasis interval (Ummul Qura)
    isya_menit_ramadan: Optional[int] = None

    @property
    def isya_interval(self) -> bool:
        return self.isya_menit is not None


METODE = {m.key: m for m in (
    PrayerMethod('persatuanIslam', 'Persatuan Islam', -20, -18),
    PrayerMethod('kemenagRI', 'Kemenag RI', -20, -18),
    PrayerMethod('nahdlatulUlama', 'Nahdlatul Ulama', -20, -18),
    PrayerMethod('muhammadiyah', 'Muhammadiyah', -18, -18),
    PrayerMethod('egyptianGeneralAuthority', 'Egyptian General Authority of Survey', -19.5, -17.5),
    PrayerMethod('islamicSocietyNorthAmerica', 'Islamic Society of North America', -18, -18),
    PrayerMethod('muslimWorldLeague', 'Muslim World League', -18, -17),
    PrayerMethod('universityIslamicScienceKarachi', 'University of Islamic Science, Karachi', -18, -18),
    PrayerMethod('ummulQura', 'Ummul Qura', -18.5, -18, 90, 120),
)}


def ihtiyat(jam_des: float, menit: float) -> float:
    """Menit hisab dibulatkan ke bawah + ihtiyat (ihtiyathShalat)."""
    h = math.floor(jam_des)
    m = math.floor((jam_des - h) * 60.0) + menit
    if m == 60.0:
        m, h = 0.0, h + 1.0
    return h + m / 60


class WaktuSalat:
    def __init__(self):
        self.sn = Sun()

    def _siap(self, tgl, bln, thn, jam, tz):
        jd = kmjd(tgl, bln, thn, jam, tz)
        return jd + delta_t(jd) / 86400.0

    def zuhur(self, tgl, bln, thn, glon, tz) -> SalatValue:
        z = 12.0
        for _ in range(3):
            jde = self._siap(tgl, bln, thn, z, tz)
            z = 12 - self.sn.equation_of_time(jde, 0.0) - (glon - tz * 15.0) / 15.0
        return SalatValue(z)

    def asar(self, tgl, bln, thn, glon, glat, tz) -> SalatValue:
        a = 15.0
        for _ in range(3):
            jde = self._siap(tgl, bln, thn, a, tz)
            e = self.sn.equation_of_time(jde, 0.0)
            dec = self.sn.declination(jde, 0.0)
            kwd = (glon - tz * 15.0) / 15.0
            zm = abs(glat - dec)
            hm = deg(math.atan(1 / (math.tan(rad(zm)) + 1)))
            cost = -math.tan(rad(glat)) * math.tan(rad(dec))
            costm = cost + math.sin(rad(hm)) / math.cos(rad(glat)) / math.cos(rad(dec))
            if cost < -1:
                return SalatValue(None, UP)
            if cost > 1:
                return SalatValue(None, DOWN)
            a = (12 - e) + deg(math.acos(max(-1.0, min(1.0, costm)))) / 15.0 - kwd
        return SalatValue(a)

    def _sudut(self, tgl, bln, thn, glon, glat, tz, awal, tanda, h_fn, lewat_atas, lewat_bawah):
        """Iterasi umum: waktu saat tinggi Matahari = h (tanda -1: sebelum zuhur, +1: sesudah)."""
        t = awal
        for _ in range(3):
            jde = self._siap(tgl, bln, thn, t, tz)
            e = self.sn.equation_of_time(jde, 0.0)
            dec = self.sn.declination(jde, 0.0)
            h = h_fn(jde)
            costm = (-math.tan(rad(glat)) * math.tan(rad(dec)) +
                     math.sin(rad(h)) / math.cos(rad(glat)) / math.cos(rad(dec)))
            if costm < -1:
                return SalatValue(None, lewat_atas)
            if costm > 1:
                return SalatValue(None, lewat_bawah)
            tm = deg(math.acos(costm))
            t = 12 - e + tanda * tm / 15.0 - (glon - tz * 15.0) / 15.0
        return SalatValue(t)

    def _h_terbit(self, elev):
        dip = 1.76 / 60.0 * math.sqrt(elev)
        return lambda jde: -(self.sn.semidiameter(jde, 0.0) + 34.5 / 60.0 + dip)

    def magrib(self, tgl, bln, thn, glon, glat, elev, tz):
        return self._sudut(tgl, bln, thn, glon, glat, tz, 18.0, +1, self._h_terbit(elev), UP, DOWN)

    def syuruk(self, tgl, bln, thn, glon, glat, elev, tz):
        return self._sudut(tgl, bln, thn, glon, glat, tz, 6.0, -1, self._h_terbit(elev), UP, DOWN)

    def isya(self, tgl, bln, thn, glon, glat, tz, hm=None):
        h = -18.0 if hm is None else hm
        return self._sudut(tgl, bln, thn, glon, glat, tz, 19.0, +1, lambda _: h, BRIGHT, DARK)

    def subuh(self, tgl, bln, thn, glon, glat, tz, hm=None):
        h = -20.0 if hm is None else hm
        return self._sudut(tgl, bln, thn, glon, glat, tz, 4.0, -1, lambda _: h, BRIGHT, DARK)

    def duha(self, tgl, bln, thn, glon, glat, elev, tz):
        s = self.syuruk(tgl, bln, thn, glon, glat, elev, tz)
        return SalatValue(s.time + 15 / 60.0) if s.is_normal else SalatValue(None, INVALID)

    def nisfu_lail(self, tgl, bln, thn, glon, glat, elev, tz, metode: PrayerMethod):
        mg = self.magrib(tgl, bln, thn, glon, glat, elev, tz)
        sb = self.subuh(tgl, bln, thn, glon, glat, tz, metode.hm_subuh)
        if not mg.is_normal or not sb.is_normal:
            return SalatValue(None, INVALID)
        return SalatValue(mg.time + mod(sb.time - mg.time, 24.0) / 2.0)


def ramadan_malam(tgl: int, bln: int, thn: int) -> bool:
    """Malam ini termasuk Ramadan? (hari berikutnya bulan Hijriah 9, kalender aritmetis; Ummul Qura resmi bisa 1 hari berbeda)."""
    from .kalender import hijri_dari_jd
    return hijri_dari_jd(kmjd(tgl + 1, bln, thn, 12, 0))['bln'] == 9


class SalatService:
    def __init__(self):
        self.ws = WaktuSalat()

    def harian(self, tgl, bln, thn, glon, glat, elev, tz, metode: PrayerMethod = METODE['persatuanIslam'], *,
               ihty_subuh=0, ihty_syuruk=0, ihty_duha=None, ihty_zuhur=0, ihty_asar=0, ihty_magrib=0, ihty_isya=0,
               ihty_nisfu=None, is_ramadan=None) -> dict:
        """Jadwal satu hari dengan ihtiyat (menit). Kunci: subuh, syuruk, duha, zuhur, asar, magrib, isya, nisfuLail.
        Seperti pustaka asli, Duha memakai ihtiyat Syuruk dan Nisfu lail memakai ihtiyat Magrib."""
        ws = self.ws

        def pakai(v: SalatValue, iht):
            return v if not v.is_normal else SalatValue(ihtiyat(v.time, iht), NORMAL)

        r = {
            'subuh': pakai(ws.subuh(tgl, bln, thn, glon, glat, tz, metode.hm_subuh), ihty_subuh),
            'syuruk': pakai(ws.syuruk(tgl, bln, thn, glon, glat, elev, tz), ihty_syuruk),
            'duha': pakai(ws.duha(tgl, bln, thn, glon, glat, elev, tz), ihty_syuruk if ihty_duha is None else ihty_duha),
            'zuhur': pakai(ws.zuhur(tgl, bln, thn, glon, tz), ihty_zuhur),
            'asar': pakai(ws.asar(tgl, bln, thn, glon, glat, tz), ihty_asar),
            'magrib': pakai(ws.magrib(tgl, bln, thn, glon, glat, elev, tz), ihty_magrib),
        }
        if metode.isya_interval:
            mg = ws.magrib(tgl, bln, thn, glon, glat, elev, tz)
            if not mg.is_normal:
                r['isya'] = mg
            else:
                ram = ramadan_malam(tgl, bln, thn) if is_ramadan is None else is_ramadan
                menit = (metode.isya_menit_ramadan or metode.isya_menit) if ram else metode.isya_menit
                r['isya'] = pakai(SalatValue(mg.time + menit / 60), ihty_isya)
        else:
            r['isya'] = pakai(ws.isya(tgl, bln, thn, glon, glat, tz, metode.hm_isya), ihty_isya)
        r['nisfuLail'] = pakai(ws.nisfu_lail(tgl, bln, thn, glon, glat, elev, tz, metode),
                               ihty_magrib if ihty_nisfu is None else ihty_nisfu)
        return r


def lama_siang(ws: WaktuSalat, tgl, bln, thn, glon, glat, elev, tz):
    a = ws.syuruk(tgl, bln, thn, glon, glat, elev, tz)
    b = ws.magrib(tgl, bln, thn, glon, glat, elev, tz)
    if a.is_normal and b.is_normal:
        return mod(b.time - a.time, 24.0)
    if UP in (a.status, b.status):
        return 24.0
    if DOWN in (a.status, b.status):
        return 0.0
    return None


def jadwal_lengkap(tgl, bln, thn, glon, glat, elev, tz, metode: PrayerMethod, *, ihtiyat_menit=0, imsak_menit=10,
                   is_ramadan=None) -> dict:
    """Jadwal satu hari: 'hisab' (mentah, berdetik), 'jadwal' (menit dibulatkan ke bawah + ihtiyat), 'astro' (fajar/senja
    sipil-nautis-astronomis, lama siang/malam). Bulan terbit/terbenam belum diport (butuh efemeris ELP-MPP02)."""
    ws = WaktuSalat()
    sv = {
        'subuh': ws.subuh(tgl, bln, thn, glon, glat, tz, metode.hm_subuh),
        'syuruk': ws.syuruk(tgl, bln, thn, glon, glat, elev, tz),
        'zuhur': ws.zuhur(tgl, bln, thn, glon, tz),
        'asar': ws.asar(tgl, bln, thn, glon, glat, tz),
        'magrib': ws.magrib(tgl, bln, thn, glon, glat, elev, tz),
    }
    ram = None
    if metode.isya_interval:
        ram = ramadan_malam(tgl, bln, thn) if is_ramadan is None else is_ramadan
        mnt = (metode.isya_menit_ramadan or metode.isya_menit) if ram else metode.isya_menit
        sv['isya'] = SalatValue(sv['magrib'].time + mnt / 60) if sv['magrib'].is_normal else sv['magrib']
    else:
        sv['isya'] = ws.isya(tgl, bln, thn, glon, glat, tz, metode.hm_isya)
    sv['duha'] = ws.duha(tgl, bln, thn, glon, glat, elev, tz)
    sv['nisfuLail'] = ws.nisfu_lail(tgl, bln, thn, glon, glat, elev, tz, metode)
    sv['imsak'] = SalatValue(sv['subuh'].time - imsak_menit / 60) if sv['subuh'].is_normal else sv['subuh']
    urut = ('imsak', 'subuh', 'syuruk', 'duha', 'zuhur', 'asar', 'magrib', 'isya', 'nisfuLail')
    jadwal = {}
    for k in urut:
        x = sv[k]
        if not x.is_normal:
            jadwal[k] = x
        elif k == 'imsak':
            jadwal[k] = SalatValue(ihtiyat(sv['subuh'].time, ihtiyat_menit) - imsak_menit / 60)
        else:
            jadwal[k] = SalatValue(ihtiyat(x.time, ihtiyat_menit))
    v = lambda s: s.time if s.is_normal else None
    siang = lama_siang(ws, tgl, bln, thn, glon, glat, elev, tz)
    astro = {
        'fajarAstro': v(ws.subuh(tgl, bln, thn, glon, glat, tz, -18)), 'fajarNaut': v(ws.subuh(tgl, bln, thn, glon, glat, tz, -12)),
        'fajarSipil': v(ws.subuh(tgl, bln, thn, glon, glat, tz, -6)),
        'senjaSipil': v(ws.isya(tgl, bln, thn, glon, glat, tz, -6)), 'senjaNaut': v(ws.isya(tgl, bln, thn, glon, glat, tz, -12)),
        'senjaAstro': v(ws.isya(tgl, bln, thn, glon, glat, tz, -18)),
        'lamaSiang': siang, 'lamaMalam': None if siang is None else 24 - siang,
    }
    return {'hisab': {k: sv[k] for k in urut}, 'jadwal': jadwal, 'astro': astro, 'ramadan': ram}
