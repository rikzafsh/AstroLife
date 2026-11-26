"""Tes AstroBot: intent operasional, slot lanjutan, retrieval (akurasi top-1/top-3), kontrak API, keamanan masukan."""
import unittest
from datetime import datetime, timezone

from app import create_app
from app.bot import jawab
from app.bot.pengetahuan import Basis

NOW = datetime(2026, 11, 26, 3, 0, tzinfo=timezone.utc)          # Kamis 26 Nov 2026, 10.00 WIB

# (pertanyaan, id artikel yang diharapkan)
SOAL = [
    ('apa itu rasydulqiblat', 'rasydulqiblat'), ('kapan matahari tepat di atas kabah', 'rasydulqiblat'),
    ('bagaimana cara menghitung arah kiblat', 'arah-kiblat'), ('apa itu azimut kiblat', 'arah-kiblat'),
    ('kenapa sudut subuh berbeda antar metode', 'kriteria-subuh-isya'), ('berapa derajat sudut isya kemenag', 'kriteria-subuh-isya'),
    ('apa itu ihtiyat', 'ihtiyat'), ('kenapa waktu salat ditambah menit pengaman', 'ihtiyat'),
    ('bagaimana waktu asar ditentukan', 'waktu-salat'), ('apa dasar penentuan waktu magrib', 'waktu-salat'),
    ('apa itu kalender hijriah aritmetis', 'hijriah-aritmetis'), ('berapa tahun kabisat dalam siklus 30 tahun hijriah', 'hijriah-aritmetis'),
    ('bagaimana awal ramadan ditentukan', 'awal-bulan-hijriah'), ('apa beda hisab dan rukyat', 'awal-bulan-hijriah'),
    ('apa itu kriteria mabims', 'kriteria-mabims'), ('berapa tinggi hilal minimal menurut mabims', 'kriteria-mabims'),
    ('apa itu kriteria ummul qura', 'kriteria-ummul-qura'), ('apa itu wujudul hilal', 'wujudul-hilal'),
    ('apa itu khgt', 'khgt'), ('apa itu kalender hijriah global tunggal', 'khgt'),
    ('apa itu ijtimak', 'ijtimak-hilal-elongasi'), ('apa bedanya elongasi dan tinggi hilal', 'ijtimak-hilal-elongasi'),
    ('apa itu kalender jawa sultan agung', 'kalender-jawa'), ('apa itu kurup dan windu', 'kalender-jawa'),
    ('apa itu weton', 'pasaran-weton-neptu'), ('berapa neptu kamis pahing', 'pasaran-weton-neptu'),
    ('apa itu pawukon', 'pawukon-wuku'), ('berapa lama siklus wuku', 'pawukon-wuku'),
    ('kenapa fase bulan berubah', 'fase-bulan'), ('berapa lama siklus bulan sinodis', 'fase-bulan'),
    ('kenapa gerhana tidak terjadi tiap bulan', 'gerhana'), ('apa itu gerhana cincin', 'gerhana'),
    ('apa itu oposisi planet', 'konjungsi-oposisi'), ('berapa elongasi maksimum venus', 'konjungsi-oposisi'),
    ('kapan puncak hujan meteor geminid', 'hujan-meteor'), ('apa itu zhr', 'hujan-meteor'),
    ('apa itu magnitudo', 'magnitudo'), ('bintang paling redup yang terlihat mata', 'magnitudo'),
    ('apa itu skala bortle', 'kualitas-langit'), ('bagaimana polusi cahaya mempengaruhi pengamatan', 'kualitas-langit'),
    ('bagaimana skor kelayakan dihitung', 'skor-kelayakan'), ('apa artinya skor pengamatan 80', 'skor-kelayakan'),
    ('apa itu delta t', 'delta-t-efemeris'), ('efemeris apa yang dipakai astrolife', 'delta-t-efemeris'),
    ('puasa sunah apa saja', 'puasa-sunah'), ('hari apa yang haram puasa', 'puasa-sunah'),
    ('apa itu tithi', 'kalender-saka-jyotisa'), ('apa itu nakshatra', 'kalender-saka-jyotisa'),
    ('wib wita wit selisih berapa', 'zona-waktu'), ('apa itu zenit dan deklinasi', 'istilah-astronomi'),
    ('fitur apa saja di astrolife', 'fitur-astrolife'), ('seberapa akurat hasil astrolife', 'akurasi-batasan'),
    ('sholat dhuhur dasar astronomisnya', 'waktu-salat'), ('ejaan qiblat arah ka\'bah', 'arah-kiblat'),
]


class TesRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Basis()

    def test_jumlah_artikel_dan_front_matter(self):
        self.assertGreaterEqual(len(self.b.artikel), 25)
        for a in self.b.artikel.values():
            self.assertTrue(a['judul'] and a['ringkas'] and a['isi'] and a['kata_kunci'], a['id'])

    def test_akurasi_top1_top3(self):
        top1 = top3 = 0
        salah = []
        for q, aid in SOAL:
            ids = [a['id'] for _, a in self.b.cari(q, 3)]
            top1 += bool(ids) and ids[0] == aid
            top3 += aid in ids
            if not ids or ids[0] != aid:
                salah.append((q, aid, ids[:2]))
        n = len(SOAL)
        print(f'\n[retrieval] {n} soal: top-1 {top1}/{n} = {top1/n:.0%}, top-3 {top3}/{n} = {top3/n:.0%}')
        for s in salah:
            print('   meleset:', s)
        self.assertGreaterEqual(top1 / n, 0.80)
        self.assertGreaterEqual(top3 / n, 0.92)

    def test_tanpa_hasil_untuk_omong_kosong(self):
        self.assertEqual(self.b.cari('zxqv plmk', 3), [])


class TesIntent(unittest.TestCase):
    def j(self, q, ctx=None, slots=None):
        return jawab(q, ctx, slots, NOW)

    def test_salat_hari_ini_dan_waktu_tunggal(self):
        r = self.j('jadwal salat hari ini')
        self.assertEqual(r['intent'], 'salat')
        self.assertIn('Yogyakarta', r['reply'])
        self.assertEqual(r['cards'][0]['baris'][0][0], 'Imsak')
        r = self.j('magrib jam berapa di Medan')
        self.assertIn('18:12', r['reply'])

    def test_slot_lanjutan_kota_dan_tanggal(self):
        r1 = self.j('jadwal salat hari ini')
        r2 = self.j('kalau di Surabaya?', None, r1['slots'])
        self.assertIn('Surabaya', r2['reply'])
        r3 = self.j('besok?', None, r2['slots'])
        self.assertIn('Jumat, 27 November 2026', r3['reply'])
        self.assertIn('Surabaya', r3['reply'])

    def test_pengaturan_dipakai(self):
        ctx = {'lokasi': {'nama': 'Medan', 'lat': 3.5952, 'lon': 98.6722, 'tz': 7}, 'salat': {'metode': 'muslimWorldLeague', 'ihtiyat': 0}}
        r = self.j('jadwal salat', ctx)
        self.assertIn('Medan', r['reply'])
        self.assertNotIn('Persatuan Islam', r['reply'])

    def test_kiblat_yogya(self):
        r = self.j('arah kiblat dari yogyakarta')
        self.assertEqual(r['intent'], 'kiblat')
        self.assertIn('294', r['reply'])

    def test_rasydulqiblat_operasional(self):
        r = self.j('rasydulqiblat tahun ini')
        self.assertEqual(r['intent'], 'rasydulqiblat')
        self.assertTrue(any('28-05-2026' in b[1] for b in r['cards'][0]['baris']))

    def test_hijri_ke_masehi_per_kriteria(self):
        r = self.j('kapan 1 Ramadan 1448?')
        self.assertEqual(r['intent'], 'hijri_ke_masehi')
        self.assertIn('Februari 2027', r['reply'])
        self.assertEqual(len(r['cards'][0]['baris']), 5)
        r = self.j('1 zulhijah 1447 menurut khgt')
        self.assertIn('18 Mei 2026', r['reply'])
        self.assertIn('KHGT', r['reply'])

    def test_kriteria_pengaturan_dipakai_untuk_puasa(self):
        a = self.j('puasa sunah minggu ini', {'hijriah': {'kriteria': 'aritmetis'}})
        self.assertIn('Aritmetis', a['reply'])
        b = self.j('puasa sunah minggu ini', {'hijriah': {'kriteria': 'mabims'}})
        self.assertIn('MABIMS', b['reply'])

    def test_konversi_dan_tanggal(self):
        r = self.j('17 agustus 2026')
        self.assertEqual(r['intent'], 'konversi')
        self.assertIn('Senin, 17 Agustus 2026', r['reply'])
        r = self.j('tanggal hari ini')
        self.assertIn('Kamis, 26 November 2026', r['reply'])

    def test_fase_bulan_bukan_lanjutan(self):
        r = self.j('fase bulan malam ini', None, {'intent': 'konversi', 'tanggal': '2026-08-17'})
        self.assertEqual(r['intent'], 'fase_bulan')

    def test_konsep_tidak_dikira_operasional(self):
        self.assertEqual(self.j('apa itu rasydulqiblat')['intent'], 'pengetahuan')
        self.assertEqual(self.j('bagaimana cara menghitung arah kiblat')['intent'], 'pengetahuan')

    def test_banding_dua_kriteria(self):
        r = self.j('bedanya mabims dan ummul qura')
        self.assertEqual(len(r['cards'][0]['baris']), 2)

    def test_sapaan_bantuan_dan_tidak_paham(self):
        self.assertEqual(self.j('halo')['intent'], 'sapaan')
        self.assertEqual(self.j('bantuan')['intent'], 'bantuan')
        r = self.j('zxqv plmk')
        self.assertEqual(r['intent'], 'tidak_paham')
        self.assertTrue(r['suggestions'])

    def test_masukan_aneh_tidak_menjatuhkan(self):
        for q in ('17 februari 2026 31 31', '99 agustus 2026', '1 ramadan 99999', 'jadwal salat 2026-13-45', '<script>alert(1)</script>', 'a' * 2000):
            r = self.j(q, {'lokasi': {'lat': 'x', 'lon': 999}}, {'intent': 'salat', 'lat': 'bukan', 'lon': None})
            self.assertIn(r['status'], ('success', 'error'))
            self.assertIn('reply', r)


class TesApi(unittest.TestCase):
    def setUp(self):
        self.c = create_app().test_client()

    def test_kontrak_chat(self):
        r = self.c.post('/bot/api/chat', json={'message': 'jadwal salat', 'context': {}, 'slots': {}})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        for k in ('status', 'reply', 'intent', 'slots', 'cards', 'links', 'sources', 'suggestions'):
            self.assertIn(k, d)

    def test_kosong_dan_non_json(self):
        self.assertEqual(self.c.post('/bot/api/chat', json={'message': '  '}).status_code, 400)
        self.assertEqual(self.c.post('/bot/api/chat', data='bukan json').status_code, 400)

    def test_artikel(self):
        d = self.c.get('/bot/api/artikel').get_json()
        self.assertGreaterEqual(len(d['artikel']), 25)
        self.assertEqual(self.c.get('/bot/api/artikel/khgt').status_code, 200)
        self.assertEqual(self.c.get('/bot/api/artikel/..%2Fapp').status_code, 404)

    def test_halaman_dan_xss_dirender_aman(self):
        h = self.c.get('/bot/').get_data(as_text=True)
        self.assertIn('bot-form', h)
        self.assertIn('function md(', h)
        self.assertIn('esc(', h)            # semua teks di-escape sebelum markdown-lite


if __name__ == '__main__':
    unittest.main()
