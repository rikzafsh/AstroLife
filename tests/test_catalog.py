"""
Tes katalog event (pencari gerhana/meteor, penormal, generator, keterlihatan, kelangkaan, API).
Memakai mesin sementara ephem_lite agar cepat dan tidak butuh internet; acuan: tabel gerhana NASA 2026
dan data in-the-sky.org November 2026 (WIB).
"""
import os
os.environ['ASTROLIFE_ENGINE'] = 'lite'     # harus sebelum prototype.engine diimpor (abjad: test_catalog dimuat lebih dulu)

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import catalog.generate as G
from app import create_app
from catalog import events as C
from catalog import rarity as R
from catalog import visibility as V
from prototype import find_events as F

JKT = (-6.2088, 106.8456)
YEAR_DIR = tempfile.TemporaryDirectory()
G.CATALOG_DIR = Path(YEAR_DIR.name)
DOC = G.generate(2026, 2026, Path(YEAR_DIR.name) / 'events.json', log=lambda *a: None)
EV = DOC['events']


def find(title_part, month=None, cat=None):
    return [e for e in EV if title_part in e['title'] and (month is None or e['time_utc'][5:7] == month) and (cat is None or e['category'] == cat)]


def minutes(a, b):
    f = lambda s: datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
    return abs((f(a) - f(b)).total_seconds()) / 60.0


class Eclipses(unittest.TestCase):
    def test_lunar_eclipses_2026_match_nasa(self):
        le = [e for e in EV if e['category'] == 'gerhana_bulan']
        self.assertEqual([(e['kind'], e['time_utc'][:10]) for e in le], [('total', '2026-03-03'), ('sebagian', '2026-08-28')])
        self.assertLess(minutes(le[0]['time_utc'], '2026-03-03T11:33:46'), 8)
        self.assertLess(minutes(le[1]['time_utc'], '2026-08-28T04:12:53'), 8)
        self.assertGreater(le[0]['details']['magnitudo_umbra'], 1.0)
        self.assertTrue(0.85 < le[1]['details']['magnitudo_umbra'] < 1.0)

    def test_solar_eclipses_2026_match_nasa(self):
        se = [e for e in EV if e['category'] == 'gerhana_matahari']
        self.assertEqual([(e['kind'], e['time_utc'][:10]) for e in se], [('cincin', '2026-02-17'), ('total', '2026-08-12')])
        self.assertLess(minutes(se[0]['time_utc'], '2026-02-17T12:11:58'), 10)
        self.assertLess(minutes(se[1]['time_utc'], '2026-08-12T17:46:06'), 10)


class MeteorShowers(unittest.TestCase):
    def test_standard_calendar_dates(self):
        win = {'Quadrantid': ('01-03', '01-04'), 'Lyrid': ('04-22', '04-23'), 'eta-Aquariid': ('05-05', '05-07'),
               'Perseid': ('08-12', '08-13'), 'Orionid': ('10-21', '10-22'), 'Leonid': ('11-17', '11-18'),
               'Geminid': ('12-13', '12-15'), 'Ursid': ('12-21', '12-23')}
        got = {e['details']['nama']: e['time_utc'][5:10] for e in EV if e['category'] == 'hujan_meteor'}
        self.assertEqual(set(got), set(win))
        for name, (a, b) in win.items():
            self.assertTrue(a <= got[name] <= b, (name, got[name]))


class Normalization(unittest.TestCase):
    def test_nov_2026_occultations_merged_into_nine_events(self):
        occ = [e for e in EV if e['category'] == 'okultasi' and e['time_utc'].startswith('2026-11')]
        self.assertEqual(len(occ), 9)
        self.assertTrue(all('start_utc' in e and 'end_utc' in e for e in occ))
        # pendekatan Bulan-Jupiter 3 Nov tidak boleh muncul lagi sebagai 'konjungsi' terpisah
        self.assertEqual([e for e in find('Konjungsi Bulan–Jupiter', '11')], [e for e in find('Konjungsi Bulan–Jupiter', '11') if e['time_utc'][8:10] == '30'])

    def test_conjunction_has_both_reference_times(self):
        e = find('Konjungsi Bulan–Saturnus', '11')[0]
        self.assertLess(minutes(e['details']['pendekatan_terdekat_utc'], '2026-11-20T20:02:00'), 12)         # 03:02 WIB (in-the-sky); mesin sementara: galat Saturnus ~9 menit
        self.assertLess(minutes(e['details']['konjungsi_asensio_rekta_utc'], '2026-11-21T01:26:00'), 12)     # 08:26 WIB

    def test_merged_pair_is_not_duplicated(self):
        mars = [e for e in EV if e['bodies'] == ['moon', 'mars'] and e['time_utc'].startswith('2026-11-02')]
        self.assertEqual([e['category'] for e in mars], ['okultasi'])        # 2 Nov: okultasi saja, bukan okultasi + konjungsi

    def test_ids_unique_and_sorted(self):
        ids = [e['id'] for e in EV]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([e['time_utc'] for e in EV], sorted(e['time_utc'] for e in EV))

    def test_meta(self):
        self.assertEqual(DOC['meta']['jumlah'], len(EV))
        self.assertEqual(sum(DOC['meta']['per_kategori'].values()), len(EV))


class Visibility(unittest.TestCase):
    def test_jupiter_occultation_local_at_jakarta_only(self):
        occ = [e for e in EV if e['category'] == 'okultasi' and e['time_utc'].startswith('2026-11')]
        local = [(e['title'], e['time_utc'][:10]) for e in occ if V.evaluate(e, *JKT)['local_occultation']['terjadi']]
        self.assertEqual(local, [('Okultasi Jupiter oleh Bulan', '2026-11-02')])
        lo = V.evaluate(find('Okultasi Jupiter', '11')[0], *JKT)['local_occultation']
        self.assertLess(minutes(lo['hilang_utc'], '2026-11-02T21:39:00'), 10)        # 04:39 WIB (in-the-sky)
        self.assertLess(minutes(lo['muncul_utc'], '2026-11-02T23:08:00'), 10)        # 06:08 WIB

    def test_best_time_inside_occultation(self):
        v = V.evaluate(find('Okultasi Jupiter', '11')[0], *JKT)
        lo = v['local_occultation']
        self.assertTrue(lo['hilang_utc'] <= v['best_time_utc'] <= lo['muncul_utc'])

    def test_instrument_follows_magnitude(self):
        uranus, neptune, jup = find('Uranus oposisi')[0], find('Neptunus oposisi')[0], find('Jupiter oposisi')
        u = V.evaluate(uranus, *JKT, naked_limit=5.0)
        self.assertEqual(u['instrument'], 'binoculars')                                               # mag ~5,6 > batas 5,0
        self.assertEqual(V.evaluate(uranus, *JKT, naked_limit=7.5)['instrument'], 'naked_eye')        # batas sangat longgar
        n = V.evaluate(neptune, *JKT)                                                                  # mag ~7,8
        self.assertAlmostEqual(n['required_magnitude'], 7.8, delta=0.3)
        # binokular (batas 9,0) cukup bila Bulan tidak mengganggu; bila gangguan > 1,2 mag, naik ke teleskop kecil
        self.assertEqual(n['instrument'], 'binoculars' if 9.0 - n['moon_glare_mag'] >= n['required_magnitude'] else 'small_telescope')
        self.assertTrue(all(V.evaluate(j, *JKT)['instrument'] == 'naked_eye' for j in jup))

    def test_bright_moon_lowers_effective_limit(self):
        u = V.evaluate(find('Uranus oposisi')[0], *JKT, naked_limit=6.0)     # 26 Nov: Bulan ~90% terang
        self.assertGreater(u['moon_illumination_pct'], 80)
        self.assertLess(u['effective_naked_limit'], 6.0)
        self.assertTrue(any('Bulan' in n for n in u['notes']))

    def test_states(self):
        self.assertEqual(V.evaluate(find('Bulan Baru', '11')[0], *JKT)['state'], 'not_observable')
        self.assertEqual(V.evaluate(find('Bulan Purnama', '11')[0], *JKT)['state'], 'visible')       # 21:53 WIB
        antares = [e for e in find('Okultasi Antares', '11')][0]                                      # 09:24-13:52 WIB
        self.assertEqual(V.evaluate(antares, *JKT)['state'], 'daylight')

    def test_eclipses_from_jakarta(self):
        mar = V.evaluate(find('Gerhana Bulan total')[0], *JKT)                                        # Bulan terbit saat gerhana
        self.assertIn(mar['state'], ('visible', 'low', 'twilight'))
        self.assertGreater(mar['min_altitude'], 0)
        self.assertEqual(V.evaluate(find('Gerhana Bulan sebagian')[0], *JKT)['state'], 'below_horizon')  # 11:13 WIB, siang
        for e in find('Gerhana Matahari'):
            self.assertFalse(V.evaluate(e, *JKT)['local_eclipse']['terlihat'], e['title'])            # tidak terlihat dari Indonesia

    def test_moon_glare_only_when_moon_is_not_the_object(self):
        v = V.evaluate(find('Perseid')[0], *JKT)
        self.assertGreaterEqual(v['moon_glare_mag'], 0)
        self.assertIn('expected_rate_per_hour', v)
        self.assertEqual(V.evaluate(find('Bulan Purnama', '11')[0], *JKT)['moon_glare_mag'], 0.0)

    def test_dichotomy_needs_telescope(self):
        d = find('dikotomi', '11')[0]
        self.assertEqual(V.evaluate(d, *JKT)['instrument'], 'small_telescope')


class Observable(unittest.TestCase):
    """Satu bendera `observable` yang jujur + ringkasan `headline` untuk antarmuka."""

    def test_local_occultation_is_observable_remote_ones_are_not(self):
        occ = [e for e in EV if e['category'] == 'okultasi' and e['time_utc'].startswith('2026-11')]
        res = {e['title'] + e['time_utc'][:10]: V.evaluate(e, *JKT) for e in occ}
        obs = [k for k, v in res.items() if v['observable']]
        self.assertEqual(obs, ['Okultasi Jupiter oleh Bulan2026-11-02'])
        self.assertTrue(res[obs[0]]['headline'].startswith('Terjadi di lokasi Anda'))
        for k, v in res.items():
            if k not in obs:
                self.assertIn('wilayah lain', v['headline'], k)       # tidak diberi label "terlihat jelas" yang menyesatkan

    def test_new_moon_and_invisible_solar_eclipse_not_observable(self):
        self.assertFalse(V.evaluate(find('Bulan Baru', '11')[0], *JKT)['observable'])
        for e in find('Gerhana Matahari'):
            v = V.evaluate(e, *JKT)
            self.assertFalse(v['observable'])
            self.assertIn('tidak terlihat', v['headline'])

    def test_full_moon_observable_with_headline(self):
        v = V.evaluate(find('Bulan Purnama', '11')[0], *JKT)
        self.assertTrue(v['observable'])
        self.assertTrue(v['headline'].startswith('Terbaik '))
        self.assertIn('Mata Telanjang', v['headline'])

    def test_slow_events_use_wide_window_and_show_best_day(self):
        d = find('dikotomi', '11')[0]
        t0, t1 = V._window(d)
        self.assertAlmostEqual((t1 - t0) * 24, 72, delta=0.5)                        # +-36 jam
        v = V.evaluate(d, *JKT)
        self.assertTrue(v['observable'])                                             # fajar terdekat tercakup
        self.assertIn('/', v['headline'])                                            # tanggal ditampilkan karena beda hari
        m = find('Konjungsi Bulan–Saturnus', '11')[0]
        t0, t1 = V._window(m)
        self.assertAlmostEqual((t1 - t0) * 24, 20, delta=0.5)                        # +-10 jam untuk event cepat


class Rarity(unittest.TestCase):
    def tier(self, title, month=None, loc=JKT):
        e = find(title, month)[0]
        return R.rarity(e, V.evaluate(e, *loc))['tier']

    def test_tiers(self):
        self.assertEqual(self.tier('Bulan Purnama', '11'), 'common')
        self.assertEqual(self.tier('Konjungsi Bulan–Mars', '11'), 'common')
        self.assertEqual(self.tier('Gerhana Bulan total'), 'rare')
        self.assertEqual(self.tier('Gerhana Bulan sebagian'), 'uncommon')
        self.assertEqual(self.tier('Gerhana Matahari total'), 'epic')
        self.assertEqual(self.tier('Gerhana Matahari cincin'), 'rare')
        self.assertEqual(self.tier('Venus paling terang'), 'rare')
        self.assertEqual(self.tier('Jupiter oposisi'), 'uncommon')
        self.assertEqual(self.tier('Mars oposisi'), 'rare') if find('Mars oposisi') else None

    def test_local_occultation_of_planet_is_rare_but_remote_one_is_not(self):
        jup = find('Okultasi Jupiter', '11')[0]
        self.assertEqual(R.rarity(jup, V.evaluate(jup, *JKT))['tier'], 'rare')                         # terjadi di Jakarta
        self.assertEqual(R.rarity(jup, V.evaluate(jup, 60.0, 10.0))['tier'], 'uncommon')                # lokasi lain (Skandinavia)

    def test_great_conjunction_rule(self):
        base = {'category': 'konjungsi', 'kind': 'conjunction', 'bodies': ['jupiter', 'saturn'], 'details': {}}
        self.assertEqual(R.rarity({**base, 'separation_deg': 0.1})['tier'], 'legendary')
        self.assertEqual(R.rarity({**base, 'separation_deg': 1.2})['tier'], 'rare')

    def test_central_solar_eclipse_at_location_is_legendary(self):
        e = find('Gerhana Matahari total')[0]
        fake = {'local_eclipse': {'terlihat': True, 'jenis_lokal': 'total/cincin'}}
        self.assertEqual(R.rarity(e, fake)['tier'], 'legendary')


class CatalogApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['CATALOG_DIR'] = Path(YEAR_DIR.name)
        cls.c = cls.app.test_client()

    def test_month_filter_and_summary(self):
        j = self.c.get('/catalog/api/events?year=2026&month=11&lat=-6.2088&lon=106.8456').get_json()
        self.assertEqual(j['status'], 'success')
        self.assertTrue(all(e['time_local'].startswith('2026-11') for e in j['events']))
        self.assertEqual(j['summary']['total'], len(j['events']))
        self.assertEqual(j['summary']['teramati'], sum(1 for e in j['events'] if e['visibility']['observable']))
        self.assertEqual(j['summary']['mata_telanjang'], sum(1 for e in j['events'] if e['visibility']['observable'] and e['visibility']['instrument'] == 'naked_eye'))
        self.assertTrue(all('headline' in e['visibility'] for e in j['events']))
        self.assertEqual(j['lokasi']['tz'], 7.0)
        self.assertEqual(j['body_names']['jupiter'], 'Jupiter')

    def test_timezone_changes_local_dates(self):
        wib = self.c.get('/catalog/api/events?year=2026&month=11&lon=106.8').get_json()
        wit = self.c.get('/catalog/api/events?year=2026&month=11&lon=140.7&lat=-2.5').get_json()
        self.assertEqual(wit['lokasi']['tz'], 9.0)
        self.assertNotEqual({e['id']: e['time_local'] for e in wib['events']}, {e['id']: e['time_local'] for e in wit['events']})

    def test_validation(self):
        self.assertEqual(self.c.get('/catalog/api/events?lat=abc').status_code, 400)
        self.assertEqual(self.c.get('/catalog/api/events?lat=100').status_code, 400)
        self.assertEqual(self.c.get('/catalog/api/events?langit=terang').status_code, 400)
        self.assertEqual(self.c.get('/catalog/api/events?tz=x').status_code, 400)

    def test_missing_catalog_explains_how_to_generate(self):
        app = create_app()
        with tempfile.TemporaryDirectory() as d:
            app.config['CATALOG_DIR'] = Path(d)
            r = app.test_client().get('/catalog/api/events')
        self.assertEqual(r.status_code, 404)
        self.assertIn('catalog.generate', r.get_json()['message'])

    def test_page_renders(self):
        r = self.c.get('/catalog/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Katalog Event Astronomi', r.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
