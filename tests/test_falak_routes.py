"""Uji endpoint /islamic dan /calendar (tanpa internet)."""
import unittest

from app import create_app


class FalakRoutes(unittest.TestCase):
    def setUp(self):
        self.c = create_app().test_client()

    def test_halaman(self):
        for url in ('/islamic/', '/calendar/'):
            r = self.c.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertNotIn('Menunggu', r.get_data(as_text=True))

    def test_jadwal_salat(self):
        j = self.c.get('/islamic/api/prayer-times?date=2026-11-26&lat=-7.7956&lon=110.3695&elev=100&ihtiyat=2').get_json()
        self.assertEqual(j['status'], 'success')
        w = {x['kunci']: x for x in j['waktu']}
        self.assertEqual(j['lokasi']['tz_label'], 'WIB')
        self.assertEqual(w['zuhur']['hisab']['jam'], '11:25:42')       # sama dengan hasil JS asli (golden)
        self.assertTrue(w['subuh']['jadwal']['jam'] < w['syuruk']['jadwal']['jam'] < w['zuhur']['jadwal']['jam']
                        < w['asar']['jadwal']['jam'] < w['magrib']['jadwal']['jam'] < w['isya']['jadwal']['jam'])
        self.assertEqual(w['subuh']['jadwal']['jam'], '03:47')           # hisab 03:45:51 → menit 45 + ihtiyat 2

    def test_kutub_tidak_dikarang(self):
        j = self.c.get('/islamic/api/prayer-times?date=2026-06-21&lat=69.6496&lon=18.9553&tz=1').get_json()
        w = {x['kunci']: x for x in j['waktu']}
        self.assertIsNone(w['syuruk']['jadwal']['jam'])
        self.assertEqual(w['syuruk']['jadwal']['status'], 'up')
        self.assertTrue(w['syuruk']['jadwal']['keterangan'])

    def test_masukan_salah(self):
        for q in ('lat=abc', 'lat=95', 'date=2026-13-01', 'method=xyz', 'ihtiyat=99'):
            r = self.c.get('/islamic/api/prayer-times?' + q)
            self.assertEqual(r.status_code, 400, q)
            self.assertEqual(r.get_json()['status'], 'error')

    def test_kiblat(self):
        j = self.c.get('/islamic/api/qibla?lat=-7.7956&lon=110.3695').get_json()
        self.assertAlmostEqual(j['bola']['derajat'], 294.7111, places=3)
        self.assertEqual(j['mata_angin'], 'barat-barat laut')

    def test_rasydul_2026(self):
        j = self.c.get('/islamic/api/rasydulqiblat?date=2026-11-26&lat=-7.7956&lon=110.3695&days=3&year=2026').get_json()
        t = j['tahunan'][0]
        self.assertEqual((t['rasydul1']['tanggal'], t['rasydul1']['jam']), ('28-05-2026', '16:17:58'))
        self.assertEqual(t['rasydul2']['tanggal'], '15-07-2026')
        self.assertEqual(len(j['harian']), 3)
        self.assertTrue(all(h['bayangan_ke_kiblat'] or h['matahari_di_kiblat'] for h in j['harian']))

    def test_konversi(self):
        def post(**kw):
            return self.c.post('/calendar/api/convert', json=kw)
        j = post(source='hijriah', year=1448, month=1, day=1).get_json()
        self.assertEqual(j['gregorian']['teks'], 'Rabu, 17 Juni 2026')
        self.assertTrue(j['jawa']['teks'].endswith('1 Sura Bé 1960 AJ, Wuku Dungulan'))
        self.assertEqual([k['kunci'] for k in j['hijriah_kriteria']], ['mabims', 'ummulqura', 'wujudulhilal', 'turki'])
        self.assertTrue(all(k['teks'] for k in j['hijriah_kriteria']))
        j = post(source='masehi', year=1945, month=8, day=17).get_json()
        self.assertEqual((j['hijriah']['hari'], j['hijriah']['pasaran']), ('Jumat', 'Legi'))
        self.assertEqual(post(source='masehi', year=2026, month=2, day=30).status_code, 400)
        self.assertEqual(post(source='hijriah', year=1448, month=2, day=30).status_code, 400)
        self.assertEqual(post(source='maya', year=1, month=1, day=1).status_code, 400)
        self.assertEqual(post(source='masehi', year='x', month=1, day=1).status_code, 400)

    def test_perbandingan_kalender(self):
        j = self.c.get('/calendar/api/compare?date=2026-11-26').get_json()
        self.assertEqual(j['status'], 'success')
        self.assertEqual(j['bulan_acuan']['nama'], 'Jumadal Akhirah')
        self.assertEqual([b['nama'] for b in j['baris']][-1], 'Mataraman')
        self.assertEqual(len(j['baris']), 9)
        self.assertTrue(all(len(b['sel']) == len(j['kolom']) for b in j['baris']))
        mat = j['baris'][-1]['sel'][0]
        self.assertNotIn('puasa', mat)                                  # Mataraman tanpa hukum puasa
        # opsi puasa: matikan Senin-Kamis dan Ayyamulbid -> tidak ada sunah di Jumadal Akhirah
        j2 = self.c.get('/calendar/api/compare?date=2026-11-26&sk=0&ab=0').get_json()
        self.assertFalse(any(x and x['puasa']['k'] == 'sunah' for x in j2['baris'][0]['sel']))
        self.assertTrue(any(x and x['puasa']['k'] == 'sunah' for x in j['baris'][0]['sel']))
        self.assertEqual(self.c.get('/calendar/api/compare?date=1200-01-01').status_code, 400)
        self.assertEqual(self.c.get('/calendar/api/compare?date=xx').status_code, 400)

    def test_puasa_harian(self):
        j = self.c.get('/islamic/api/puasa?date=2026-11-26&days=14').get_json()
        self.assertEqual(j['status'], 'success')
        self.assertTrue(any('Senin' in p['jenis'] for p in j['jadwal']))


if __name__ == '__main__':
    unittest.main()
