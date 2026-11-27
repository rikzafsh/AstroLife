"""Bulan: posisi (deret ELPMPP02 ringkas), paralaks, tinggi toposentrik, elongasi, ijtimak, terbit/terbenam.
Port moon*.js dari persis-times-js. Deret ELPMPP02 dipangkas (1.036 suku dari 36.000+; amplitudo >= 0,01"):
galat < 0,4" dibanding deret penuh, tanpa berkas besar. Dihasilkan oleh tools/gen_persis_moon.py."""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from .core import Sun, delta_t, deg, jc, jdkm, kmjd, mod, nutation_longitude, rad, true_obliquity

_DATA = Path(__file__).resolve().parent / '_data' / 'moon_elp_ringkas.npz'


@lru_cache(maxsize=1)
def _elp():
    z = np.load(_DATA)
    return {k: z[k] for k in z.files}


def _jumlah(nama: str, t: float, pangkat: int) -> float:
    total = 0.0
    T = _elp()
    for k in range(pangkat):
        a = T['%s%d' % (nama, k)]
        if len(a):
            ph = a[:, 1] + a[:, 2] * t + a[:, 3] * t ** 2 + a[:, 4] * t ** 3 + a[:, 5] * t ** 4
            total += float(np.sum(a[:, 0] * np.sin(ph))) * t ** k
    return total


class Moon:
    def __init__(self, sun: Sun | None = None):
        self.sn = sun or Sun()
        self._c = {}

    def _ecl(self, jd, dt):
        """(bujur tampak, lintang tampak, jarak km) pada JDE = jd + dt/86400."""
        key = jd + dt / 86400.0
        if key in self._c:
            return self._c[key]
        t = jc(key)
        l = _jumlah('l', t, 4)
        w = 3.81034409083088 + 8399.68473007193 * t - 0.0000331895204255009 * t ** 2 + 3.11024944910606e-08 * t ** 3 - 2.03282376489228e-10 * t ** 4
        p = (5029.0966 - 0.29965) * t + 1.112 * t ** 2 + 0.000077 * t ** 3 - 0.00002353 * t ** 4
        lon = mod(deg(w) + l / 3600.0 + p / 3600.0, 360.0)
        lon += nutation_longitude(jd, dt) - 0.00019524 - 0.00001059 * math.sin(rad(225 + 477198.9 * t))
        lat = _jumlah('b', t, 3) / 3600.0 - 0.00001754 * math.sin(rad(183.3 + 483202.0 * t))
        r = _jumlah('r', t, 4) + 0.0708 * math.cos(rad(225.0 + 477198.9 * t))
        if len(self._c) > 64:
            self._c.clear()
        self._c[key] = (lon, lat, r)
        return self._c[key]

    def longitude(self, jd, dt): return self._ecl(jd, dt)[0]
    def latitude(self, jd, dt): return self._ecl(jd, dt)[1]
    def distance_km(self, jd, dt): return self._ecl(jd, dt)[2]

    def right_ascension(self, jd, dt):
        lam, beta, eps = self.longitude(jd, dt), self.latitude(jd, dt), true_obliquity(jd, dt)
        return mod(deg(math.atan2(math.sin(rad(lam)) * math.cos(rad(eps)) - math.tan(rad(beta)) * math.sin(rad(eps)),
                                  math.cos(rad(lam)))), 360.0)

    def declination(self, jd, dt):
        lam, beta, eps = self.longitude(jd, dt), self.latitude(jd, dt), true_obliquity(jd, dt)
        return deg(math.asin(math.sin(rad(beta)) * math.cos(rad(eps)) + math.cos(rad(beta)) * math.sin(rad(eps)) * math.sin(rad(lam))))

    def lha(self, jd, dt, glon):
        return mod(self.sn.gast(jd, dt) + glon - self.right_ascension(jd, dt), 360)

    def altitude_geosentris(self, jd, dt, glon, glat):
        lha, dec = self.lha(jd, dt, glon), self.declination(jd, dt)
        return deg(math.asin(math.sin(rad(glat)) * math.sin(rad(dec)) + math.cos(rad(glat)) * math.cos(rad(dec)) * math.cos(rad(lha))))

    def paralaks_horizontal(self, jd, dt): return deg(math.asin(6378.14 / self.distance_km(jd, dt)))

    def semidiameter(self, jd, dt):
        return deg(math.asin(0.272481 * math.sin(rad(self.paralaks_horizontal(jd, dt)))))

    def elongasi(self, jd, dt):
        ds, as_ = self.sn.declination(jd, dt), self.sn.right_ascension(jd, dt)
        dm, am = self.declination(jd, dt), self.right_ascension(jd, dt)
        c = math.sin(rad(ds)) * math.sin(rad(dm)) + math.cos(rad(ds)) * math.cos(rad(dm)) * math.cos(rad(as_ - am))
        return deg(math.acos(max(-1.0, min(1.0, c))))

    # ── toposentrik ──
    def _d_ra(self, jd, dt, glon, glat, elev):
        x, phi = self.sn.term_x(glat, elev), self.paralaks_horizontal(jd, dt)
        ha, dec = self.lha(jd, dt, glon), self.declination(jd, dt)
        return deg(math.atan2(-x * math.sin(rad(phi)) * math.sin(rad(ha)), math.cos(rad(dec)) - x * math.sin(rad(phi)) * math.cos(rad(ha))))

    def deklinasi_topo(self, jd, dt, glon, glat, elev):
        dec, y, x = self.declination(jd, dt), self.sn.term_y(glat, elev), self.sn.term_x(glat, elev)
        phi, da, ha = self.paralaks_horizontal(jd, dt), self._d_ra(jd, dt, glon, glat, elev), self.lha(jd, dt, glon)
        return deg(math.atan2((math.sin(rad(dec)) - y * math.sin(rad(phi))) * math.cos(rad(da)),
                              math.cos(rad(dec)) - x * math.sin(rad(phi)) * math.cos(rad(ha))))

    def lha_topo(self, jd, dt, glon, glat, elev):
        return self.lha(jd, dt, glon) - self._d_ra(jd, dt, glon, glat, elev)

    def _term_n(self, jd, dt, glon, glat, elev):
        lam, beta = self.longitude(jd, dt), self.latitude(jd, dt)
        theta = self.sn.last(jd, dt, glon)
        x, phi = self.sn.term_x(glat, elev), self.paralaks_horizontal(jd, dt)
        return math.cos(rad(lam)) * math.cos(rad(beta)) - x * math.sin(rad(phi)) * math.cos(rad(theta))

    def _topo_lon(self, jd, dt, glon, glat, elev):
        lam, beta, phi = self.longitude(jd, dt), self.latitude(jd, dt), self.paralaks_horizontal(jd, dt)
        theta, eps = self.sn.last(jd, dt, glon), true_obliquity(jd, dt)
        x, y, n = self.sn.term_x(glat, elev), self.sn.term_y(glat, elev), self._term_n(jd, dt, glon, glat, elev)
        return mod(deg(math.atan2(math.sin(rad(lam)) * math.cos(rad(beta)) - math.sin(rad(phi)) *
                                  (y * math.sin(rad(eps)) + x * math.cos(rad(eps)) * math.sin(rad(theta))), n)), 360)

    def _topo_lat(self, jd, dt, glon, glat, elev):
        lam_p, beta, phi = self._topo_lon(jd, dt, glon, glat, elev), self.latitude(jd, dt), self.paralaks_horizontal(jd, dt)
        theta, eps = self.sn.last(jd, dt, glon), true_obliquity(jd, dt)
        x, y, n = self.sn.term_x(glat, elev), self.sn.term_y(glat, elev), self._term_n(jd, dt, glon, glat, elev)
        return deg(math.atan(math.cos(rad(lam_p)) * (math.sin(rad(beta)) - math.sin(rad(phi)) *
                                                      (y * math.cos(rad(eps)) - x * math.sin(rad(eps)) * math.sin(rad(theta)))) / n))

    def semidiameter_topo(self, jd, dt, glon, glat, elev):
        lp, bp = self._topo_lon(jd, dt, glon, glat, elev), self._topo_lat(jd, dt, glon, glat, elev)
        return deg(math.sin(math.cos(rad(lp)) * math.cos(rad(bp)) * math.sin(rad(self.semidiameter(jd, dt))) / self._term_n(jd, dt, glon, glat, elev)))

    def altitude_topo(self, jd, dt, glon, glat, elev, pres, temp, opt: str = 'htc'):
        """Tinggi toposentrik: htc = pusat tanpa atmosfer; htoc/htou = teramati (refraksi + dip) pusat/tepi atas."""
        dec, lha = self.deklinasi_topo(jd, dt, glon, glat, elev), self.lha_topo(jd, dt, glon, glat, elev)
        htc = deg(math.asin(math.sin(rad(glat)) * math.sin(rad(dec)) + math.cos(rad(glat)) * math.cos(rad(dec)) * math.cos(rad(lha))))
        dip = 1.75 / 60 * math.sqrt(elev)
        sdc = self.semidiameter_topo(jd, dt, glon, glat, elev)
        htu = htc + sdc
        ref = Sun.refraksi_tanpa_atmosfer
        if opt == 'htc': return htc
        if opt == 'htu': return htu
        if opt == 'htoc': return htc + ref(htc, pres, temp) + dip
        if opt == 'htou': return htu + ref(htu, pres, temp) + dip
        raise ValueError(opt)

    # ── ijtimak ──
    @staticmethod
    def bulan_baru_perkiraan(bln_h: int, thn_h: int) -> float:
        """JDE bulan baru (Meeus bab 49) untuk bulan Hijriah bln_h/thn_h (moonPhasesModified, jenis 1)."""
        k = math.floor(bln_h + 12 * thn_h - 17050)
        t = k / 1236.85
        t2, t3, t4 = t * t, t ** 3, t ** 4
        jde = 2451550.09766 + 29.530588861 * k + 0.00015437 * t2 - 0.00000015 * t3 + 0.00000000073 * t4
        e = 1 - 0.002516 * t - 0.0000074 * t2
        R = lambda x: rad(mod(x, 360))
        m = R(2.5534 + 29.1053567 * k - 0.0000014 * t2 - 0.00000011 * t3)
        mp = R(201.5643 + 385.81693528 * k + 0.0107582 * t2 + 0.00001238 * t3 - 0.000000058 * t4)
        f = R(160.7108 + 390.67050284 * k - 0.0016118 * t2 - 0.00000227 * t3 + 0.000000011 * t4)
        om = R(124.7746 - 1.56375588 * k + 0.0020672 * t2 + 0.00000215 * t3)
        a = [R(299.77 + 0.107408 * k - 0.009173 * t * t), R(251.88 + 0.016321 * k), R(251.83 + 26.651886 * k), R(349.42 + 36.412478 * k),
             R(84.66 + 18.206239 * k), R(141.74 + 53.303771 * k), R(207.14 + 2.453732 * k), R(154.84 + 7.30686 * k), R(34.52 + 27.261239 * k),
             R(207.19 + 0.121824 * k), R(291.34 + 1.844379 * k), R(161.72 + 24.198154 * k), R(239.56 + 25.513099 * k), R(331.55 + 3.592518 * k)]
        s = math.sin
        c1 = (-0.4072 * s(mp) + 0.17241 * e * s(m) + 0.01608 * s(2 * mp) + 0.01039 * s(2 * f) + 0.00739 * e * s(mp - m) - 0.00514 * e * s(mp + m)
              + 0.00208 * e * e * s(2 * m) - 0.00111 * s(mp - 2 * f) - 0.00057 * s(mp + 2 * f) + 0.00056 * e * s(2 * mp + m) - 0.00042 * s(3 * mp)
              + 0.00042 * e * s(m + 2 * f) + 0.00038 * e * s(m - 2 * f) - 0.00024 * e * s(2 * mp - m) - 0.00017 * s(om) - 0.00007 * s(mp + 2 * m)
              + 0.00004 * s(2 * mp - 2 * f) + 0.00004 * s(3 * m) + 0.00003 * s(mp + m - 2 * f) + 0.00003 * s(2 * mp + 2 * f)
              - 0.00003 * s(mp + m + 2 * f) + 0.00003 * s(mp - m + 2 * f) - 0.00002 * s(mp - m - 2 * f) - 0.00002 * s(3 * mp + m) + 0.00002 * s(4 * mp))
        amp = (0.000325, 0.000165, 0.000164, 0.000126, 0.00011, 0.000062, 0.00006, 0.000056, 0.000047, 0.000042, 0.00004, 0.000037, 0.000035, 0.000023)
        c2 = sum(w * s(x) for w, x in zip(amp, a))
        return jde + c1 + c2

    def ijtimak(self, bln_h: int, thn_h: int, dt: float = 0.0) -> float:
        """Ijtimak geosentris (JD) = bujur ekliptika Matahari = Bulan (geocentricConjunction), interpolasi 3 titik ±1 jam."""
        jd_nm = self.bulan_baru_perkiraan(bln_h, thn_h)
        x = (jd_nm - 1 / 24, jd_nm, jd_nm + 1 / 24)
        y = [self.sn.longitude(j, dt) - self.longitude(j, dt) for j in x]
        a, b = y[1] - y[0], y[2] - y[1]
        c = b - a
        n0, hasil = 0.0, jd_nm
        for _ in range(2):
            n0 = -2 * y[1] / (a + b + c * n0)
            hasil = jd_nm + n0 / 24
        return hasil

    # ── terbit / transit / terbenam ──
    def terbit_terbenam(self, tgl, bln, thn, glon, glat, elev, tz, jenis: str, max_itr: int = 3) -> float:
        """Jam desimal (zona tz) Bulan 'RISE' | 'SET' | 'TRANSIT' (moonTransitRiseSet); 0 bila tidak terjadi pada tanggal itu."""
        jd00 = kmjd(tgl, bln, thn, tz, tz) - 1
        ttrs = 0.0
        for _ in range(3):
            jde00 = jd00 + delta_t(jd00) / 86400.0
            am1, a0, ap1 = (self.right_ascension(jde00 + d, 0) for d in (-1, 0, 1))
            if jenis == 'TRANSIT':
                dm1 = d0 = dp1 = 0.0
            else:
                dm1, d0, dp1 = (self.declination(jde00 + d, 0) for d in (-1, 0, 1))
            pi = self.paralaks_horizontal(jde00, 0)
            h0 = -(34 / 60) + 0.7275 * pi - 0.0353 * math.sqrt(elev)
            cos_ha0 = (math.sin(rad(h0)) - math.sin(rad(glat)) * math.sin(rad(d0))) / (math.cos(rad(glat)) * math.cos(rad(d0)))
            ha0 = deg(math.acos(cos_ha0)) if abs(cos_ha0) <= 1 else 0
            t = (jde00 - 2451545) / 36525
            th0 = mod(100.46061837 + 36000.770053608 * t + 0.000387933 * t * t - t ** 3 / 38710000
                      + nutation_longitude(jde00, 0) * math.cos(rad(true_obliquity(jde00, 0))), 360)
            m = (a0 - glon - th0) / 360
            if jenis == 'RISE': m -= ha0 / 360
            elif jenis == 'SET': m += ha0 / 360
            m = mod(m, 1)
            for _i in range(max_itr):
                s_th = mod(th0 + 360.985647 * m, 360)
                n = m
                dA1, dA2 = mod(a0 - am1, 360), mod(ap1 - a0, 360)
                a_m = mod(a0 + n / 2.0 * (dA1 + dA2 + n * (dA2 - dA1)), 360)
                d_m = 0 if jenis == 'TRANSIT' else d0 + n / 2.0 * ((d0 - dm1) + (dp1 - d0) + n * ((dp1 - d0) - (d0 - dm1)))
                ha = s_th + glon - a_m
                ha = mod(ha, 360) - 360 if mod(ha, 360) > 180 else mod(ha, 360)
                h = deg(math.asin(math.sin(rad(glat)) * math.sin(rad(d_m)) + math.cos(rad(glat)) * math.cos(rad(d_m)) * math.cos(rad(ha))))
                if jenis == 'TRANSIT':
                    dlt = -ha / 360
                else:
                    dlt = (h - h0) / (360 * math.cos(rad(d_m)) * math.cos(rad(glat)) * math.sin(rad(ha)))
                m = mod(m + dlt, 1)
            jd_trs = jd00 + m
            jd00_lt = kmjd(tgl, bln, thn, 0, tz)
            ttrs = jdkm(jd_trs, tz)['jam_des']
            if not (jd00_lt <= jd_trs <= jd00_lt + 1):
                jd00 += 1
                ttrs = 0.0
        return ttrs
