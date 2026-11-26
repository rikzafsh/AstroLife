"""Perencana pengamatan berbasis katalog: event dapat diamati + skor cuaca pada waktu terbaiknya."""
import os
os.environ['ASTROLIFE_ENGINE'] = 'lite'

import unittest
from datetime import datetime
from pathlib import Path

import helpers as H
import test_catalog as TC
from app import create_app
from app.services import planner_service as P
from catalog import service as S

JKT = (-6.2088, 106.8456)
NOW = datetime(2026, 11, 16, 3, 0)         # 10:00 WIB; paruh kedua November kaya event yang dapat diamati
DOC = {'meta': TC.DOC['meta'], 'events': TC.EV}


def make_plan(instrument='all', days=14, net=None, **kw):
    ctx = net or H.net(H.payload(20, start=datetime(2026, 11, 15), days=20))
    with ctx:
        return P.plan(DOC, *JKT, 'pinggiran', 7.0, instrument, NOW, days, kw.get('limit', 50))


class PlanFromCatalog(unittest.TestCase):
    def test_only_observable_events_within_window_sorted_by_score(self):
        r = make_plan()
        self.assertTrue(r['weather_available'])
        self.assertGreater(len(r['items']), 3)
        scores = [i['score'] for i in r['items']]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for it in r['items']:
            self.assertTrue(it['time_local'] >= '2026-11-16 07:00' and it['time_local'] <= '2026-11-30 10:00', it['time_local'])
            self.assertIsNotNone(it['instrument'])
        # okultasi di wilayah lain (mis. Regulus 30 Nov) dan Bulan baru tidak boleh muncul sebagai 'dapat diamati'
        titles = [i['title'] for i in r['items']]
        self.assertNotIn('Bulan Baru', titles)
        self.assertFalse([t for t in titles if t.startswith('Okultasi') and 'Jupiter' not in t])

    def test_each_score_uses_best_time_of_that_event(self):
        r = make_plan()
        for it in r['items']:
            self.assertIsNotNone(it['best_local'])                                   # semua yang dapat diamati punya waktu terbaik
            self.assertEqual(it['wx']['default'], it['best_local'])

    def test_instrument_filter_is_cumulative(self):
        naked, binoc, allg = make_plan('naked_eye'), make_plan('binoculars'), make_plan('all')
        self.assertTrue(all(i['instrument'] == 'naked_eye' for i in naked['items']))
        self.assertTrue(all(i['instrument'] in ('naked_eye', 'binoculars') for i in binoc['items']))
        self.assertLessEqual(len(naked['items']), len(binoc['items']))
        self.assertLessEqual(len(binoc['items']), len(allg['items']))

    def test_clear_beats_cloudy(self):
        clear = make_plan(net=H.net(H.payload(5, start=datetime(2026, 11, 15), days=20)))
        cloudy = make_plan(net=H.net(H.payload(95, rain=70, start=datetime(2026, 11, 15), days=20)))
        mean = lambda r: sum(i['score'] for i in r['items']) / len(r['items'])
        self.assertGreater(mean(clear), mean(cloudy) + 30)

    def test_offline_never_fabricates_scores(self):
        r = make_plan(net=H.net(down=True))
        self.assertFalse(r['weather_available'])
        self.assertGreater(len(r['items']), 0)                                       # event tetap terdaftar
        self.assertTrue(all(i['score'] is None for i in r['items']))

    def test_days_are_clamped_to_forecast_horizon(self):
        self.assertEqual(make_plan(days=90)['days'], P.FORECAST_MAX_DAYS)

    def test_moon_event_not_penalised_for_moonlight(self):
        r = make_plan(net=H.net(H.payload(10, start=datetime(2026, 11, 15), days=20)))
        moon_items = [i for i in r['items'] if 'moon' in i['bodies']]
        self.assertTrue(moon_items)
        self.assertTrue(all(i['score'] >= 60 for i in moon_items))                    # langit cerah, Bulan = objek -> skor baik


class PlanApi(unittest.TestCase):
    def client(self, catalog_dir):
        app = create_app()
        app.config['CATALOG_DIR'] = Path(catalog_dir)
        return app.test_client()

    def test_missing_catalog_returns_404_with_hint(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r = self.client(d).get('/observation/api/plan')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()['status'], 'empty')

    def test_validation(self):
        c = self.client(TC.YEAR_DIR.name)
        self.assertEqual(c.get('/observation/api/plan?instrument=mata').status_code, 400)
        self.assertEqual(c.get('/observation/api/plan?lat=abc').status_code, 400)
        self.assertEqual(c.get('/observation/api/plan?langit=terang').status_code, 400)

    def test_page_has_no_event_source_controls_left(self):
        html = self.client(TC.YEAR_DIR.name).get('/observation/').get_data(as_text=True)
        for gone in ('sync-btn', 'Sinkron', 'modal', 'loadEvents'):
            self.assertNotIn(gone, html)
        self.assertIn('plan-list', html)


class ServiceUpcoming(unittest.TestCase):
    def test_upcoming_window_and_ordering(self):
        items = S.upcoming(DOC, *JKT, 'pinggiran', 7.0, NOW, days=7, observable_only=False)
        times = [i['time_utc'] for i in items]
        self.assertEqual(times, sorted(times))
        self.assertTrue(all('2026-11-16T00' <= t <= '2026-11-23T03' for t in times))

    def test_covers(self):
        self.assertTrue(S.covers(DOC, datetime(2026, 6, 1)))
        self.assertFalse(S.covers(DOC, datetime(2027, 6, 1)))
        self.assertFalse(S.covers(DOC, datetime(2026, 12, 20), margin_days=20))     # menjelang akhir rentang
        self.assertFalse(S.covers(None, datetime(2026, 6, 1)))


if __name__ == '__main__':
    unittest.main()
