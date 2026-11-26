"""Uji Bulan & hisab awal bulan terhadap JS asli (deret ELPMPP02 penuh) lewat tests/fixtures/persis_golden_bulan.json
(dibuat: node tools/persis_golden_bulan.js <persis-times-js> <keluaran> 1440 1460)."""
import json
import math
import re
import unittest
from pathlib import Path

from app.persis import bulan, core, hisab, salat

G = json.loads((Path(__file__).parent / 'fixtures' / 'persis_golden_bulan.json').read_text(encoding='utf8'))
DET = 1 / 86400


def norm(n):
    """Samakan ejaan nama bulan (JS: Syawwal; aplikasi: Syawal): huruf kembar dan tanda baca dibuang."""
    return re.sub(r'(.)\1+', r'\1', re.sub(r'[^a-z]', '', n.lower()))


class Posisi(unittest.TestCase):
    def test_posisi_bulan_dalam_detik_busur(self):
        m = bulan.Moon()
        for c in G['posisi']:
            j, d = c['jd'], c['dt']
            self.assertLess(abs(m.longitude(j, d) - c['lon']) * 3600, 0.6, c)
            self.assertLess(abs(m.latitude(j, d) - c['lat']) * 3600, 0.6, c)
            self.assertLess(abs(m.distance_km(j, d) - c['r']), 1.0, c)
            self.assertLess(abs(m.right_ascension(j, d) - c['ra']) * 3600, 0.6)
            self.assertLess(abs(m.declination(j, d) - c['dec']) * 3600, 0.6)
            self.assertLess(abs(m.elongasi(j, d) - c['elong']) * 3600, 1.0)
            for opt in ('htoc', 'htou'):
                self.assertLess(abs(m.altitude_topo(j, d, 110.37, -7.8, 10, 1010, 10, opt) - c[opt]) * 3600, 0.6)

    def test_terbit_terbenam_sama_dengan_js(self):
        m = bulan.Moon()
        for c in G['terbit']:
            v = m.terbit_terbenam(c['d'], c['m'], c['y'], c['lo'], c['la'], c['el'], c['tz'], c['t'])
            self.assertEqual(v == 0, c['v'] == 0, c)
            if v:
                self.assertLess(min(abs(v - c['v']), 24 - abs(v - c['v'])) * 60, 0.05, c)

    def test_ijtimak(self):
        m = bulan.Moon()
        for c in G['ijtimak']:
            dt = core.delta_t(m.ijtimak(c['m'], c['y'], 0.0))
            self.assertLess(abs(m.ijtimak(c['m'], c['y'], dt) - c['jd']), 2 * DET, c)


class AwalBulan(unittest.TestCase):
    def test_empat_kriteria_sama_dengan_js_1008_bulan(self):
        n = 0
        for c in G['awal']:
            for k, f in (('mabims', hisab.awal_mabims), ('uq', hisab.awal_ummul_qura), ('wh', hisab.awal_wujudul_hilal), ('turki', hisab.awal_turki)):
                self.assertEqual(f(c['m'], c['y']), c[k], (k, c['m'], c['y']))
                n += 1
        self.assertEqual(n, 1008)

    def test_tanggal_hijriah_per_kriteria_sama_dengan_js(self):
        for c in G['hijri']:
            cjdn = math.floor(core.kmjd(c['d'], c['m'], c['y']) + 0.5)
            for k, nama in (('mabims', 'mabims'), ('uq', 'ummulqura'), ('wh', 'wujudulhilal'), ('turki', 'turki')):
                mm = re.search(r'\| (\d+) (.+) (\d+) H', c[k])
                h = hisab.hijri_kriteria(cjdn, nama)
                self.assertEqual((h['tgl'], norm(h['nama_bulan']), h['thn']), (int(mm.group(1)), norm(mm.group(2)), int(mm.group(3))), (k, c['d'], c['m'], c['y']))

    def test_ramadan_ummul_qura(self):
        # 1 Ramadan 1447 (UQ) = 19 Feb 2026? Hitungan: malam sebelum awal Ramadan ikut dianggap Ramadan
        awal = hisab.awal_ummul_qura(9, 1447)
        y, m, d, _ = __import__('app.services.astro_core', fromlist=['x']).from_jdn(awal)
        self.assertEqual((y, m), (2026, 2))
        self.assertTrue(salat.ramadan_malam(d - 1, m, y))              # malam 1 Ramadan
        self.assertFalse(salat.ramadan_malam(d - 3, m, y))
        self.assertFalse(salat.ramadan_malam(1, 6, 2026))

    def test_isya_ummul_qura_interval_ramadan(self):
        awal = hisab.awal_ummul_qura(9, 1447)
        y, m, d, _ = __import__('app.services.astro_core', fromlist=['x']).from_jdn(awal)
        ws = salat.SalatService()
        biasa = ws.harian(1, 6, 2026, 39.8262, 21.4225, 300, 3, salat.METODE['ummulQura'])
        ram = ws.harian(d + 5, m, y, 39.8262, 21.4225, 300, 3, salat.METODE['ummulQura'])
        sel = lambda r: round((r['isya'].time - r['magrib'].time) * 60)
        self.assertEqual(sel(biasa), 90)
        self.assertEqual(sel(ram), 120)


class Perbandingan(unittest.TestCase):
    def test_tabel(self):
        t = hisab.banding(2461371)                                   # 26 Nov 2026
        self.assertEqual(len(t['baris']), 9)
        self.assertEqual(t['bulan_acuan'], 6)
        n = t['cjdn_akhir'] - t['cjdn_awal'] + 1
        self.assertTrue(30 <= n <= 34)
        self.assertTrue(all(len(b['sel']) == n for b in t['baris']))
        # setiap baris memuat tanggal 1 bulan acuan atau tanggal sebelumnya (varian paling awal) — dan tanggal berurutan
        for b in t['baris']:
            xs = [x['d'] for x in b['sel'] if x]
            for a, c in zip(xs, xs[1:]):
                self.assertTrue(c == a + 1 or c == 1, (b['nama'], xs))


if __name__ == '__main__':
    unittest.main()
