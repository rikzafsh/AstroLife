"""
Meniru data nyata pengguna: scraping dengan lokasi situs = IST (bukan Jakarta), event bertanggal '2026-11' (komet),
dan jam kulminasi yang bergantung zona. Dibangun dari fixture teks mentah ASLI (ist_sample.json).
"""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import test_observation as T
from app import create_app
from app.services import planner_service as pl
from app.services import scraper_service as ss

FIX = Path(__file__).parent / 'fixtures' / 'ist_sample.json'


def build_dataset():
    recs = []
    for e in json.loads(FIX.read_text(encoding='utf-8')):
        p = ss.parse_event_time(e['peak_event_time'])
        r = {'title': e['title'], 'peak_event_time': e['peak_event_time'], 'source_tz': 'IST',
             'date': p['utc_start'].strftime('%Y-%m-%d'), 'difficulty_key': 'naked_eye',
             'difficulty_label': 'Mata Telanjang', 'description': 'Deskripsi global.', 'visibility_summary': ''}
        if e['title'] == 'Close approach of the Moon and Jupiter' and p['mid'].day == 3:
            r.update(rising_time='02:10 (IST)', fading_time='05:30 (IST)', altitude='51°', azimuth_direction='north-eastern horizon')
        recs.append(r)
    recs.append({'title': 'Comet 69P/Taylor passes perihelion', 'date': '2026-11', 'peak_event_time': 'Sun, 08 Nov 2026',
                 'source_tz': 'IST', 'difficulty_key': 'large_telescope', 'difficulty_label': 'Teleskop Besar'})
    recs.append({'title': 'Comet X without any date', 'date': '2026-11', 'peak_event_time': '', 'source_tz': 'IST'})
    recs.append({'title': 'The Pleiades cluster is well placed', 'date': '2026-11-18', 'peak_event_time': 'Wed, 18 Nov 2026',
                 'source_tz': 'IST', 'visibility_summary': 'visible between 18:58 and 04:43, highest point in the sky at 23:50.'})
    recs.append({'title': 'The Hyades cluster is well placed', 'date': '2026-11-28', 'peak_event_time': 'Sat, 28 Nov 2026',
                 'source_tz': 'WIB', 'visibility_summary': 'visible between 18:58 and 04:43, highest point in the sky at 23:50.'})
    for i, r in enumerate(recs, 1):                 # scraper asli selalu memberi id unik
        r['id'] = f"evt-{r['date'].replace('-', '')}-{i}"
    return recs


class IstPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        (Path(cls.tmp.name) / 'astronomy_events.json').write_text(json.dumps(build_dataset()), encoding='utf-8')
        with mock.patch.object(ss, 'DATASETS_DIR', Path(cls.tmp.name)):
            cls.events = ss.scrape_in_the_sky_events(2026, 11)
        cls.by = {}
        for e in cls.events:
            cls.by.setdefault(e['title'], []).append(e)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_loaded_everything(self):
        self.assertEqual(len(self.events), len(build_dataset()))

    def test_every_dated_event_has_observation_time(self):
        for e in self.events:
            if e['title'] == 'Comet X without any date':
                self.assertIsNone(e['obs_time'])
                self.assertTrue(e['obs_note'])             # alasan tertulis, bukan kosong
            else:
                self.assertIsNotNone(e['obs_time'], e['title'])

    def test_month_only_date_uses_page_date_and_is_flagged_assumed(self):
        c = self.by['Comet 69P/Taylor passes perihelion'][0]
        self.assertEqual(c['obs_time'], '2026-11-08T20:00')
        self.assertTrue(c['obs_assumed'])

    def test_location_specific_fields_hidden(self):
        for e in self.events:
            if e['title'] == 'The Hyades cluster is well placed':     # sengaja berzona WIB
                self.assertTrue(e['location_ok'])
                continue
            self.assertFalse(e['location_ok'], e['title'])
            self.assertEqual(e['sky_position']['altitude'], 'Tidak dirilis')
            self.assertEqual(e['sky_position']['direction'], 'Tidak dirilis')

    def test_morning_object_still_detected_despite_foreign_location(self):
        e = [x for x in self.by['Close approach of the Moon and Jupiter'] if x['date_wib'] == '2026-11-03'][0]
        self.assertEqual((e['obs_basis'], e['obs_time']), ('predawn', '2026-11-03T04:15'))

    def test_transit_time_only_trusted_for_wib_sites(self):
        self.assertEqual(self.by['The Pleiades cluster is well placed'][0]['obs_basis'], 'assumed_evening')   # IST: diabaikan
        h = self.by['The Hyades cluster is well placed'][0]
        self.assertEqual((h['obs_basis'], h['obs_time']), ('transit', '2026-11-28T23:50'))                   # WIB: dipakai

    def test_forecast_hour_equals_displayed_hour_for_all_dated_events(self):
        n = 0
        for e in self.events:
            if not e['obs_time']:
                continue
            obs = datetime.strptime(e['obs_time'], '%Y-%m-%dT%H:%M')
            with T.net(T.payload(30, start=datetime(2026, 10, 31), days=36)):
                w = pl.evaluate_event(e, -6.2088, 106.8456, None, obs - timedelta(days=1, hours=7))['weather']
            self.assertTrue(w['available'], e['title'])
            expect = (obs + timedelta(minutes=30)).replace(minute=0)
            self.assertEqual(w['valid_local'], expect.strftime('%Y-%m-%d %H:%M'), e['title'])
            n += 1
        self.assertGreaterEqual(n, 30)

    def test_telescope_keys_are_normalized_for_ui_but_detail_kept(self):
        c = self.by['Comet 69P/Taylor passes perihelion'][0]
        self.assertEqual((c['difficulty'], c['difficulty_detail']), ('telescope', 'large_telescope'))

    def test_plan_survives_all_difficulty_keys_and_respects_instrument(self):
        now = datetime(2026, 11, 16, 3, 0)
        with mock.patch.object(ss, 'DATASETS_DIR', Path(self.tmp.name)), T.net(T.payload(20)):
            p_tel = pl.plan(-6.2088, 106.8456, 'telescope', 2026, 11, now)
        with mock.patch.object(ss, 'DATASETS_DIR', Path(self.tmp.name)), T.net(T.payload(20)):
            p_bin = pl.plan(-6.2088, 106.8456, 'binoculars', 2026, 11, now)
        comet = lambda P: next(i for i in P['items'] if i['title'].startswith('Comet 69P'))
        self.assertTrue(comet(p_tel)['needs_better_instrument'])        # teleskop besar > teleskop 4-inci
        self.assertEqual(comet(p_tel)['required_instrument'], 'Teleskop Besar')
        self.assertNotIn(comet(p_bin)['id'], p_bin['top'])

    def test_events_api_serializes_everything(self):
        with mock.patch.object(ss, 'DATASETS_DIR', Path(self.tmp.name)):
            r = create_app().test_client().get('/observation/api/events?year=2026&month=11')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['count'], len(build_dataset()))


if __name__ == '__main__':
    unittest.main()
