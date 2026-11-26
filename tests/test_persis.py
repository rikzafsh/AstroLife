"""Uji port persis-times-js → Python (app/persis) terhadap hasil pustaka JS asli.
Fixture tests/fixtures/persis_golden.json dibuat dengan `node tools/persis_golden.js <persis-times-js> <keluaran>`."""
import json
import math
import unittest
from pathlib import Path

from app.persis import core, kalender, kiblat, salat

G = json.loads((Path(__file__).parent / 'fixtures' / 'persis_golden.json').read_text(encoding='utf8'))
DET = 1.0 / 86400          # 1 detik dalam hari/jam-detik
JAM_DET = 1.0 / 3600       # 1 detik dalam jam


class Matahari(unittest.TestCase):
    def test_kmjd(self):
        for c in G['kmjd']:
            self.assertAlmostEqual(core.kmjd(*c['a']), c['jd'], places=9)

    def test_delta_t(self):
        for c in G['deltat']:
            self.assertAlmostEqual(core.delta_t(c['jd']), c['dt'], places=9, msg=c)

    def test_posisi_matahari(self):
        s = core.Sun()
        for c in G['sun']:
            j, d = c['jd'], c['dt']
            self.assertAlmostEqual(core.delta_t(j), d, places=9)
            for nama, nilai in (('ra', s.right_ascension(j, d)), ('dec', s.declination(j, d)), ('lon', s.longitude(j, d)),
                                ('lat', s.latitude(j, d)), ('r', s.radius(j, d)), ('sd', s.semidiameter(j, d)),
                                ('eot', s.equation_of_time(j, d)), ('dpsi', core.nutation_longitude(j, d)),
                                ('deps', core.nutation_obliquity(j, d)), ('eps', core.true_obliquity(j, d)),
                                ('gast', s.gast(j, d))):
                self.assertAlmostEqual(nilai, c[nama], places=8, msg='%s @ %s' % (nama, j))


class Salat(unittest.TestCase):
    def test_jadwal_harian_cocok_dengan_js(self):
        svc = salat.SalatService()
        n = 0
        for c in G['salat']:
            l = c['lok']
            r = svc.harian(c['d'], c['m'], c['y'], l['lon'], l['lat'], l['elev'], l['tz'], salat.METODE[c['metode']],
                           ihty_subuh=2, ihty_zuhur=3, ihty_asar=2, ihty_magrib=2, ihty_isya=2, ihty_syuruk=-2, is_ramadan=False)
            for k, v in c['r'].items():
                self.assertEqual(r[k].status, v['s'], msg=(l['n'], c['d'], c['m'], c['metode'], k))
                if v['t'] is not None:
                    self.assertAlmostEqual(r[k].time, v['t'], places=7, msg=(l['n'], c['d'], c['m'], c['metode'], k))
                n += 1
        self.assertGreater(n, 1000)

    def test_metode_dan_ihtiyat(self):
        self.assertAlmostEqual(salat.ihtiyat(4.5999, 2), 4 + 37 / 60)   # 4:35,99 → 4:35 + 2 menit
        self.assertAlmostEqual(salat.ihtiyat(11.9999, 1), 12.0)        # 11:59 + 1 menit = 12:00
        self.assertAlmostEqual(salat.ihtiyat(5.5, 0), 5.5)
        self.assertEqual(len(salat.METODE), 9)

    def test_lintang_tinggi(self):
        # Tromsø 21 Juni: Matahari tengah malam → syuruk 'up'; Isya tidak ada
        r = salat.WaktuSalat().syuruk(21, 6, 2026, 18.9553, 69.6496, 10, 1)
        self.assertEqual(r.status, salat.UP)
        self.assertEqual(salat.WaktuSalat().isya(21, 6, 2026, 18.9553, 69.6496, 1, -18).status, salat.BRIGHT)


class Kiblat(unittest.TestCase):
    def test_arah_dan_jarak(self):
        for c in G['kiblat']:
            l = c['lok']
            self.assertAlmostEqual(kiblat.arah_bola(l['lon'], l['lat']), c['sph'], places=9)
            self.assertAlmostEqual(kiblat.arah_elipsoid(l['lon'], l['lat']), c['ell'], places=9)
            self.assertAlmostEqual(kiblat.vincenty(l['lon'], l['lat'], 'PtoQ'), c['vin'], places=7)
            self.assertAlmostEqual(kiblat.vincenty(l['lon'], l['lat'], 'Dist'), c['dist'], places=3)
            self.assertAlmostEqual(kiblat.jarak_bola_km(l['lon'], l['lat']), c['jarakSph'], places=6)

    def test_kiblat_yogyakarta(self):
        # kiblat Yogyakarta lazim dikutip ±294°43' dari utara
        self.assertAlmostEqual(kiblat.arah_bola(110.3695, -7.7956), 294 + 43 / 60, delta=0.05)

    def test_rasydulqiblat_tahunan(self):
        for c in G['rasydul']:
            r = kiblat.rasydulqiblat(c['y'], c['tz'], c['opt'])
            a = kiblat.antipoda_kabah(c['y'], c['tz'], c['opt'])
            for mine, js in ((r, c['r']), (a, c['a'])):
                self.assertAlmostEqual(mine['jd'], js['jd'], places=7)
                self.assertAlmostEqual(mine['jam_des'], js['jamDes'], places=5)
                self.assertAlmostEqual(mine['tinggi'], js['tinggi'], places=6)
                self.assertAlmostEqual(mine['deklinasi'], js['deklinasi'], places=6)
            b = kiblat.bayangan_kiblat_harian(110.3695, -7.7956, 10, 11, c['y'], 7, 'bola', c['opt'])
            if c['b'] is None:
                self.assertIsNone(b)
            else:
                self.assertAlmostEqual(b, c['b'], places=7)

    def test_rasydulqiblat_2026_nyata(self):
        """Fakta acuan: Rasydul 1 ±27/28 Mei ≈ 09:18 UTC, Rasydul 2 ±15/16 Juli ≈ 09:27 UTC."""
        for opt, bulan, hari in ((1, 5, (27, 28)), (2, 7, (15, 16))):
            r = kiblat.rasydulqiblat(2026, 0, opt)
            k = core.jdkm(r['jd'], 0)
            self.assertEqual(k['bln'], bulan)
            self.assertIn(k['tgl'], hari)
            self.assertAlmostEqual(k['jam_des'], 9.4, delta=0.15)

    def test_rasydul_harian(self):
        for c in G['rasydulHarian']:
            l = c['lok']
            ev = kiblat.rasydulqiblat_harian(c['d'], c['m'], c['y'], l['lat'], l['lon'], l['tz'], c['Q'])
            self.assertEqual(len(ev), len(c['ev']), msg=c)
            for a, b in zip(ev, c['ev']):
                self.assertEqual(a['jenis'], b['jenis'])
                for k in ('jam', 'tinggi', 'azimut'):
                    self.assertAlmostEqual(a[k], b[k], places=6)

    def test_istiwa_dan_sepertiga_malam(self):
        for c in G['istiwa']:
            l = c['lok']
            r = kiblat.istiwa(10, 11, 2026, l['lon'], l['lat'], l['tz'])
            for k in ('jam', 'tafawut', 'kwd', 'deklinasi', 'tinggi'):
                self.assertAlmostEqual(r[k], c['r'][k], places=7)
            m = kiblat.sepertiga_malam(10, 11, 2026, l['lon'], l['lat'], l['elev'], l['tz'])
            if c['sm'] is None:
                self.assertIsNone(m)
            else:
                for k, v in c['sm'].items():
                    self.assertAlmostEqual(m[k], v, places=7)

    def test_tinggi_azimut(self):
        for c in G['sunAltAz']:
            r = kiblat.tinggi_azimut_matahari(c['j'], c['la'], c['lo'])
            self.assertAlmostEqual(r['tinggi'], c['r']['tinggi'], places=7)
            self.assertAlmostEqual(r['azimut'], c['r']['azimut'], places=7)


class Kalender(unittest.TestCase):
    def test_jawa(self):
        for c in G['jawa']:
            r = kalender.jd_ke_jawa(c['jd'])
            self.assertEqual((r['tahun'], r['bulan'], r['tanggal']), (c['r']['tahunJawa'], c['r']['bulanJawa'], c['r']['tanggalJawa']))
            self.assertEqual(kalender.no_tahun_jawa(r['tahun']), c['no'])
        for c in G['jawa2jd']:
            self.assertAlmostEqual(kalender.jawa_ke_jd(*c['a']), c['jd'])

    def test_jawa_pembalikan(self):
        for jd in (2461000.5, 2459000.5, 2455000.5):
            j = kalender.jd_ke_jawa(jd)
            self.assertAlmostEqual(kalender.jawa_ke_jd(j['tanggal'], j['bulan'], j['tahun']), math.floor(jd) + 0.5, delta=1.0)

    def test_hijriah_aritmetis(self):
        for c in G['hijri']:
            r = kalender.hijri_dari_jd(c['jd'], 7, c['e'], c['l'])
            self.assertEqual([r['tgl'], r['bln'], r['thn'], r['nama_bulan']], c['r'][:4])
            self.assertEqual(r['pasaran'], c['cj'])
        for c in G['khcjdn']:
            self.assertEqual(kalender.hijri_ke_cjdn(*c['a']), c['r'])

    def test_fakta_acuan(self):
        # knowledge.md 6.1: 1 Muharram 1448 (urfi) = 17 Jun 2026; 17 Agustus 1945 = Jumat Legi
        m = kalender.hijri_ke_masehi(1, 1, 1448)
        self.assertEqual((m['tgl'], m['bln'], m['thn']), (17, 6, 2026))
        r = kalender.hijri_dari_jd(core.kmjd(17, 8, 1945, 12, 0))
        self.assertEqual((r['hari'], r['pasaran']), ('Jumat', 'Legi'))


if __name__ == '__main__':
    unittest.main()
