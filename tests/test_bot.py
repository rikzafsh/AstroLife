"""Tes AstroBot: intent operasional, slot lanjutan, retrieval (akurasi top-1/top-3), kontrak API, keamanan masukan."""
import unittest
from datetime import datetime, timezone
from unittest import mock

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
        self.assertIn('18:13', r['reply'])      # koordinat+elevasi Masjid Agung Medan (data kota_data.csv)

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


class TesKota(unittest.TestCase):
    def j(self, q, slots=None, ctx=None):
        return jawab(q, ctx, slots, NOW)

    def test_csv_utuh(self):
        from app.bot.kota import _muat
        kota, _ = _muat()
        n = len({id(e) for v in kota.values() for e in v if e['sumber'] == 'csv'})
        self.assertEqual(n, 499)                                   # 500 baris dikurangi "Limapuluh" yang ditolak

    def test_kiblat_kota_disebut_bukan_pengaturan(self):
        r = self.j('Arah kiblat di Lubuklinggau')
        self.assertEqual(r['intent'], 'kiblat')
        self.assertIn('Lubuklinggau', r['reply'])
        self.assertIn('294.99', r['reply'])
        self.assertNotIn('Yogyakarta', r['reply'])
        r2 = self.j('arah kiblat di lubuk linggau')                 # spasi diabaikan
        self.assertIn('Lubuklinggau', r2['reply'])

    def test_salat_memakai_elevasi_dan_zona_data(self):
        r = self.j('jadwal salat di Tarakan')
        self.assertIn('WITA', r['reply'])
        self.assertIn('elevasi 1 m', r['reply'])
        r = self.j('jadwal salat di Lubuklinggau')
        self.assertIn('elevasi 135 m', r['reply'])

    def test_ambigu_dan_lanjutan_provinsi(self):
        r = self.j('jadwal salat di Martapura')
        self.assertEqual(r['intent'], 'lokasi_ambigu')
        r2 = self.j('Martapura Kalimantan Selatan', r['slots'])
        self.assertEqual(r2['intent'], 'salat')
        self.assertIn('WITA', r2['reply'])
        r3 = self.j('Martapura Sumatera Selatan', r['slots'])
        self.assertIn('WIB', r3['reply'])

    def test_kota_tak_dikenal_tidak_diam_diam_pakai_pengaturan(self):
        for q in ('arah kiblat di Xyzkota', 'jadwal salat untuk Qwertyville besok'):
            r = self.j(q)
            self.assertEqual(r['intent'], 'lokasi_tak_dikenal')
            self.assertNotIn('Yogyakarta', r['reply'])

    def test_tanpa_kota_tetap_pengaturan(self):
        for q in ('arah kiblat dari lokasi saya', 'jadwal salat di sini', 'jadwal salat hari ini'):
            r = self.j(q, None, {'lokasi': {'nama': 'Medan', 'lat': 3.5952, 'lon': 98.6722, 'tz': 7}})
            self.assertIn('Medan', r['reply'])

    def test_koordinat_dan_kata_biasa(self):
        r = self.j('kiblat -3.2954, 102.8655')
        self.assertIn('294.99', r['reply'])
        r = self.j('apa itu sumber data astrolife')                 # "sumber" bukan kota tanpa penunjuk
        self.assertNotIn('Titik acuan', r['reply'])

    def test_koreksi_data_sumber(self):
        from app.bot.kota import cari_lokasi
        self.assertGreater(cari_lokasi('kiblat di Tarakan')['lat'], 3)    # lintang sumber bertanda minus
        self.assertEqual(cari_lokasi('kiblat di Limapuluh')['status'], 'tak_dikenal')

    def test_lanjutan_kota_dan_tanggal_tetap_jalan(self):
        r1 = self.j('arah kiblat di Lubuklinggau')
        r2 = self.j('kalau di Medan?', r1['slots'])
        self.assertIn('Medan', r2['reply'])
        r3 = self.j('jadwal salat di Lubuklinggau')
        r4 = self.j('besok?', r3['slots'])
        self.assertIn('Lubuklinggau', r4['reply'])
        self.assertIn('Jumat, 27 November 2026', r4['reply'])


def _prakiraan_palsu(offset=7 * 3600):
    """Prakiraan Open-Meteo buatan (tanpa jaringan) untuk 26-30 Nov 2026: berawan sebagian, hujan sore hari 27 Nov."""
    jam = {}
    for n in range(11):
        bln, hari = (11, 25 + n) if 25 + n <= 30 else (12, 25 + n - 30)
        for h in range(24):
            hujan = 80 if (bln == 11 and hari == 27 and 15 <= h <= 18) else 10
            awan = 90 if (bln == 11 and hari == 28) else 30
            jam[f'2026-{bln:02d}-{hari:02d}T{h:02d}:00'] = {'temp_c': 26.0, 'humidity_pct': 80, 'precipitation_prob': hujan, 'precipitation_mm': 0.0,
                                                   'cloud_cover_pct': awan, 'cloud_low': 10, 'cloud_mid': 10, 'cloud_high': 10, 'visibility_m': 20000}
    return {'offset': offset, 'hours': jam}


class TesBaru(unittest.TestCase):
    def j(self, q, ctx=None, slots=None):
        return jawab(q, ctx, slots, datetime(2026, 11, 27, 0, 30, tzinfo=timezone.utc))        # Jumat 27 Nov 2026, 07.30 WIB

    def test_jumlah_hari_ramadan(self):
        r = self.j('Jumlah hari bulan Ramadan 1448')
        self.assertEqual(r['intent'], 'jumlah_hari')
        self.assertIn('Ramadan 1448 H', r['reply'])
        self.assertEqual(len(r['cards'][0]['baris']), 5)
        umur = {b[0]: b[3] for b in r['cards'][0]['baris']}
        self.assertEqual(umur['Aritmetis'], '30 hari')                 # bulan ke-9 aritmetis = 30 hari
        for v in umur.values():
            self.assertIn(v, ('29 hari', '30 hari'))
        r = self.j('berapa hari bulan syawal 1448 menurut mabims')
        self.assertIn('MABIMS', r['reply'])

    def test_weton_hari_ini(self):
        r = self.j('Weton hari ini berapa?')
        self.assertEqual(r['intent'], 'weton')
        self.assertIn('Jumat Pon', r['reply'])
        self.assertIn('neptu **13**', r['reply'])
        self.assertIn('Kurantil', r['reply'])
        self.assertIn('Kamis Pahing', self.j('weton 26 november 2026')['reply'])

    def test_hujan_meteor_berbahaya_ke_artikel_keselamatan(self):
        r = self.j('Apakah hujan meteor berbahaya?')
        self.assertEqual(r['intent'], 'pengetahuan')
        self.assertEqual(r['slots']['artikel'], 'keamanan-pengamatan')
        self.assertIn('Tidak berbahaya', r['reply'])

    def test_cuaca_tanpa_jaringan_jujur(self):
        with mock.patch('app.services.weather_service.fetch_hourly_forecast', return_value=None):
            r = self.j('Bagaimana cuaca hari ini di Batang?')
        self.assertEqual(r['intent'], 'cuaca')
        self.assertIn('Batang', r['reply'])
        self.assertIn('tidak dapat dihubungi', r['reply'])
        self.assertEqual(r['cards'], [])

    def test_cuaca_dengan_prakiraan(self):
        with mock.patch('app.services.weather_service.fetch_hourly_forecast', return_value=_prakiraan_palsu()):
            r = self.j('Bagaimana cuaca hari ini di Batang?')
            self.assertEqual(r['intent'], 'cuaca')
            baris = {b[0].split()[0]: b for b in r['cards'][0]['baris']}
            self.assertEqual(baris['Sore'][3], '80%')                  # peluang hujan sore
            self.assertEqual(baris['Pagi'][3], '10%')
            self.assertIn('Batang', r['reply'])
            r2 = self.j('cuaca hari ini di tempatku', {'lokasi': {'nama': 'Medan', 'lat': 3.59, 'lon': 98.67, 'tz': 7}})
            self.assertIn('Medan', r2['reply'])                         # "tempatku" = lokasi Pengaturan, bukan kota tak dikenal

    def test_rekomendasi_observasi(self):
        with mock.patch('app.services.weather_service.fetch_hourly_forecast', return_value=None):
            r = self.j('Rekomendasi observasi langit minggu ini')
            self.assertEqual(r['intent'], 'observasi')
            self.assertEqual(len(r['cards'][0]['baris']), 7)
            self.assertIn('Prakiraan cuaca tidak dapat dimuat', r['reply'])
        with mock.patch('app.services.weather_service.fetch_hourly_forecast', return_value=_prakiraan_palsu()):
            r = self.j('Rekomendasi observasi langit minggu ini')
            self.assertIn('Malam terbaik', r['reply'])
            skor = [b[3] for b in r['cards'][0]['baris']]
            self.assertTrue(any(x != '—' for x in skor))

    def test_hari_ini_saja_bukan_tanggal(self):
        with mock.patch('app.services.weather_service.fetch_hourly_forecast', return_value=None):
            self.assertEqual(self.j('bagaimana cuaca hari ini')['intent'], 'cuaca')
        self.assertEqual(self.j('tanggal hari ini')['intent'], 'tanggal')


class TesLagi(unittest.TestCase):
    def j(self, q, ctx=None, slots=None):
        return jawab(q, ctx, slots, datetime(2026, 11, 27, 2, 30, tzinfo=timezone.utc))        # Jumat 27 Nov 2026, 09.30 WIB

    def test_bulan_baru_berikutnya(self):
        r = self.j('Kapan fase bulan baru berikutnya?')
        self.assertEqual(r['intent'], 'fase_berikut')
        self.assertIn('9 Desember 2026', r['reply'])               # ijtimak 9 Des 2026 00:52 UTC = 07:52 WIB
        self.assertIn('07:52', r['reply'])
        self.assertIn('9 Desember', self.j('kapan bulan baru berikutnya')['reply'])
        self.assertIn('24 Desember 2026', self.j('kapan purnama berikutnya?')['reply'])

    def test_gerhana_terdekat_cocok_dengan_data_nasa(self):
        r = self.j('Kapan gerhana matahari terdekat?')
        self.assertEqual(r['intent'], 'gerhana')
        self.assertIn('cincin', r['reply'])
        self.assertIn('6 Februari 2027', r['reply'])               # gerhana cincin 6 Feb 2027 (puncak global 16:00 UTC)
        self.assertEqual(r['cards'][0]['baris'][1][0], 'Gerhana Matahari total')   # 2 Agt 2027
        self.assertIn('Jangan menatap Matahari', r['reply'])
        r = self.j('kapan gerhana bulan berikutnya')
        self.assertIn('21 Februari 2027', r['reply'])

    def test_tahun_saka_dan_jawa(self):
        r = self.j('Berapa tahun Saka sekarang?')
        self.assertEqual(r['intent'], 'tahun')
        self.assertIn('1948 Saka', r['reply'])
        self.assertNotEqual(r['intent'], 'salat')
        r = self.j('Berapa tahun Jawa sekarang?')
        self.assertIn('Bé 1960 AJ', r['reply'])
        r = self.j('sekarang tahun berapa')
        self.assertEqual(len(r['cards'][0]['baris']), 4)

    def test_selisih_zuhur_dua_kota(self):
        r = self.j('Selisih waktu zuhur di Lubuklinggau dan Yogyakarta berapa?')
        self.assertEqual(r['intent'], 'banding_salat')
        self.assertIn('29 mnt', r['reply'])                        # 7,497° bujur ≈ 29,99 menit
        self.assertIn('Yogyakarta lebih awal', r['reply'])
        r = self.j('selisih waktu salat Medan dan Jayapura')       # beda zona: selisih pada saat sebenarnya
        self.assertIn('Zona waktu berbeda', r['reply'])
        self.assertGreater(len(r['cards'][0]['baris']), 3)


class TesHariRelatif(unittest.TestCase):
    NOW = datetime(2026, 11, 27, 6, 19, tzinfo=timezone.utc)                                # Jumat 27 Nov 2026 (H)

    def j(self, q, slots=None):
        return jawab(q, None, slots, self.NOW)

    def test_istilah_dan_selisih(self):
        casos = {'kila mulai': 'Selasa, 24 November', 'selumbari': 'Rabu, 25 November', 'basarai': 'Rabu, 25 November',
                 'kemarin dulu': 'Rabu, 25 November', 'kemarin lusa': 'Rabu, 25 November', 'kemarin': 'Kamis, 26 November',
                 'besok': 'Sabtu, 28 November', 'lusa': 'Minggu, 29 November', 'besok lusa': 'Minggu, 29 November',
                 'tulat': 'Senin, 30 November', 'langkat': 'Senin, 30 November', 'tubin': 'Selasa, 1 Desember',
                 'tungging': 'Selasa, 1 Desember', 'cekelong': 'Rabu, 2 Desember', 'embute': 'Kamis, 3 Desember'}
        for kata, hari in casos.items():
            r = self.j(f'{kata} hari apa?')
            self.assertEqual(r['intent'], 'tanggal', kata)
            self.assertIn(hari, r['reply'], kata)

    def test_lanjutan_dan_intent_lain(self):
        r1 = self.j('Tubin hari apa?')
        r2 = self.j('Kalau tulat?', r1['slots'])
        self.assertIn('H+3', r2['reply'])
        self.assertIn('Senin, 30 November', r2['reply'])
        self.assertIn('30 November 2026', self.j('jadwal salat tulat')['reply'])
        self.assertIn('Selasa, 1 Desember', self.j('weton tubin')['reply'])
        self.assertIn('terdekat', self.j('senantu hari apa')['reply'])

    def test_istilah_dijelaskan_dari_artikel(self):
        r = self.j('apa itu tubin')
        self.assertEqual(r['slots']['artikel'], 'istilah-hari-relatif')
        self.assertIn('H+4', r['reply'])


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
