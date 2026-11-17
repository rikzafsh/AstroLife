"""
Uji modul Observation Planner. Jalankan:  python -m unittest discover -s tests -v
Respons Open-Meteo DITIRUKAN (mock) agar uji tidak butuh internet; ini menguji LOGIKA, bukan akurasi cuaca.
"""
import unittest
from datetime import datetime, timedelta
from unittest import mock

from app import create_app
from app.services import planner_service as pl
from app.services import weather_service as ws
from app.services.scraper_service import scrape_in_the_sky_events, determine_event_category

NOW = datetime(2026, 11, 16, 3, 0)          # 10:00 WIB
EVENTS = {e['id']: e for e in scrape_in_the_sky_events(2026, 11)}
LEONID = next(e for e in EVENTS.values() if 'Leonid' in e['title'])


def by_title(part, peak_prefix=None):
    return next(e for e in EVENTS.values() if part in e['title'] and (peak_prefix is None or (e['peak_time'] or '').startswith(peak_prefix)))


def payload(cloud, rain=5, off=25200, start=datetime(2026, 11, 15), days=17):
    cols = {k: [] for k in ['temperature_2m', 'relative_humidity_2m', 'precipitation_probability', 'precipitation',
                            'cloud_cover', 'cloud_cover_low', 'cloud_cover_mid', 'cloud_cover_high', 'visibility']}
    times = []
    for i in range(days * 24):
        t = start + timedelta(hours=i)
        c = cloud(t) if callable(cloud) else cloud
        times.append(t.strftime('%Y-%m-%dT%H:00'))
        for k, v in zip(cols, [26, 75, rain, 0.0, c, c * .5, c * .3, c * .2, 24000]):
            cols[k].append(v)
    return {'utc_offset_seconds': off, 'hourly': {'time': times, **cols}}


class Resp:
    def __init__(self, p): self.p = p
    def raise_for_status(self): pass
    def json(self): return self.p


def net(forecast=None, archive=None, down=False):
    ws._cache.clear()

    def fake(url, params=None, timeout=None):
        if down:
            raise ConnectionError('offline')
        if 'archive' in url:
            if archive is None:
                raise ConnectionError('archive down')
            return Resp(archive(params))
        return Resp(forecast)
    return mock.patch.object(ws.requests, 'get', side_effect=fake)


def archive_payload(params):
    n = 15 * 24
    t0 = datetime.strptime(params['start_date'], '%Y-%m-%d')
    return {'utc_offset_seconds': 25200, 'hourly': {
        'time': [(t0 + timedelta(hours=i)).strftime('%Y-%m-%dT%H:00') for i in range(n)],
        'cloud_cover': [60] * n, 'relative_humidity_2m': [80] * n,
        'precipitation': [0.2 if i % 48 == 0 else 0 for i in range(n)], 'temperature_2m': [25] * n}}


class Categories(unittest.TestCase):
    def test_moon_conjunction_is_not_phase(self):
        self.assertEqual(determine_event_category('Close approach of the Moon and Mars'), 'Konjungsi Planet')
        self.assertEqual(determine_event_category('Full Moon'), 'Fase Bulan')
        self.assertEqual(determine_event_category('Moon at First Quarter'), 'Fase Bulan')
        self.assertEqual(determine_event_category('Leonid meteor shower 2026'), 'Hujan Meteor')

    def test_observation_time_rules(self):
        self.assertEqual(LEONID['obs_time'], '2026-11-18T02:00')                       # meteor tanpa jam: 02:00
        self.assertEqual(by_title('Close approach of the Moon and Mars', '2026-11-02')['obs_time'], '2026-11-02T20:39')     # puncak malam hari
        self.assertTrue(by_title('Close approach of the Moon and Jupiter', '2026-11-03')['obs_time'].startswith('2026-11-03T04'))  # puncak setelah fajar


class DataIntegrity(unittest.TestCase):
    """Menjawab: apakah data tampilan benar-benar dari sumber, tanpa isian karangan?"""
    RAW = None

    def test_no_invented_placeholders(self):
        import json
        banned = ['Langit Malam', 'Jalur Ekliptika', 'Sesuai peta bintang', 'Di atas cakrawala',
                  'Di atas ufuk', 'Malam hari', 'Astronomical event:']
        blob = json.dumps(list(EVENTS.values()), ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_missing_fields_are_marked_not_filled(self):
        e = by_title('Moon at Last Quarter')       # sumber tidak memuat ketinggian/arah
        self.assertEqual(e['sky_position']['altitude'], 'Tidak dirilis')
        self.assertEqual(e['sky_position']['direction'], 'Tidak dirilis')

    def test_parser_takes_timezone_only_from_page(self):
        from app.services.detail_parser import parse_in_the_sky_detail_html as P
        h = ('<p class="widetitle">X - In-The-Sky.org</p><div class="link_green">Mon, 02 Nov 2026 at 20:39 WIB</div>'
             '<div class="newsbody"><p>x</p><p>From Jakarta, rising at 00:55 (WIB), altitude of 58° above the '
             'north-eastern horizon, dawn breaks at around 05:12</p></div>')
        r = P(h)
        self.assertEqual((r['rising_time'], r['fading_time']), ('00:55 (WIB)', '05:12 (WIB)'))
        r = P(h.replace('(WIB)', '(UTC)').replace('20:39 WIB', '20:39 UTC'))
        self.assertEqual((r['rising_time'], r['fading_time']), ('00:55 (UTC)', '05:12 (UTC)'))   # tidak dipaksa WIB
        r = P(h.replace(' (WIB)', '').replace('20:39 WIB', '20:39'))
        self.assertEqual((r['rising_time'], r['fading_time']), ('00:55', '05:12'))               # tanpa zona -> tanpa label
        self.assertIsNone(r['difficulty_level'])                                                 # tanpa default level 1

    def test_morning_events_not_scored_in_the_evening(self):
        for part in ['Mercury at dichotomy', 'Mercury at greatest elongation west', 'Mercury at highest altitude in morning']:
            e = by_title(part)
            self.assertTrue(e['obs_time'][11:13] in ('04', '05'), (part, e['obs_time']))

    def test_assumed_hours_are_flagged(self):
        for e in EVENTS.values():
            if not e['peak_time'] and e['obs_basis'] != 'transit':
                self.assertTrue(e['obs_assumed'], e['title'])
            if e['obs_basis'] in ('peak', 'transit'):
                self.assertFalse(e['obs_assumed'])
        self.assertEqual(by_title('Pleiades')['obs_time'], '2026-11-18T23:50')                  # kulminasi dari sumber


class SameMomentAsEvent(unittest.TestCase):
    def test_forecast_hour_equals_displayed_hour_for_every_event(self):
        """Untuk KEDUA-PULUH-LIMA event: jam prakiraan (waktu lokal WIB) == jam yang ditampilkan di kartu."""
        checked = 0
        for e in EVENTS.values():
            obs = datetime.strptime(e['obs_time'], '%Y-%m-%dT%H:%M')
            now = obs - timedelta(days=1)                 # selalu di dalam jangkauan prakiraan
            with net(payload(30, start=datetime(2026, 10, 31), days=36)):
                w = pl.evaluate_event(e, -6.2088, 106.8456, None, now - timedelta(hours=7))['weather']   # now dalam UTC
            self.assertTrue(w['available'], e['title'])
            expect = (obs + timedelta(minutes=30)).replace(minute=0)     # jam terdekat
            self.assertEqual(w['valid_local'], expect.strftime('%Y-%m-%d %H:%M'), e['title'])
            checked += 1
        self.assertEqual(checked, len(EVENTS))


class Moon(unittest.TestCase):
    def test_illumination_known_phases(self):
        self.assertGreater(pl.moon_illumination(datetime(2026, 11, 24, 14, 53)), 0.99)      # purnama
        self.assertAlmostEqual(pl.moon_illumination(datetime(2026, 11, 17, 11, 48)), 0.5, delta=0.03)

    def test_altitude_sanity(self):
        # kuartal awal: di atas ufuk pukul 21:00 WIB, sudah terbenam pukul 02:00 WIB (Yogyakarta)
        self.assertGreater(pl.moon_altitude_at(datetime(2026, 11, 17, 14, 0), -7.8, 110.37), 20)
        self.assertLess(pl.moon_altitude_at(datetime(2026, 11, 17, 19, 0), -7.8, 110.37), 0)


class Weather(unittest.TestCase):
    def test_forecast_hour_and_timezone(self):
        with net(payload(10)):
            r = pl.evaluate_event(LEONID, -7.8, 110.37, None, NOW)
        self.assertEqual(r['weather']['kind'], 'forecast')
        self.assertEqual(r['weather']['valid_local'], '2026-11-18 02:00')
        with net(payload(10, off=28800)):          # WITA: 02:00 WIB = 03:00 WITA
            r = pl.evaluate_event(LEONID, -5.15, 119.43, None, NOW)
        self.assertEqual(r['weather']['valid_local'], '2026-11-18 03:00')

    def test_clear_beats_cloudy(self):
        with net(payload(10)):
            clear = pl.evaluate_event(LEONID, -7.8, 110.37, None, NOW)['feasibility']['score']
        with net(payload(95, rain=70)):
            cloudy = pl.evaluate_event(LEONID, -7.8, 110.37, None, NOW)['feasibility']['score']
        self.assertGreater(clear, cloudy + 40)

    def test_moon_below_horizon_has_no_penalty(self):
        ev = dict(LEONID, obs_time='2026-11-17T20:00')        # 13:00 UTC; Bulan kuartal awal masih tinggi
        late = dict(LEONID, obs_time='2026-11-18T02:00')      # Bulan sudah terbenam
        with net(payload(10)):
            a = {b['faktor']: b['penalti'] for b in pl.evaluate_event(ev, -7.8, 110.37, None, NOW)['feasibility']['breakdown']}
            b = {b['faktor']: b['penalti'] for b in pl.evaluate_event(late, -7.8, 110.37, None, NOW)['feasibility']['breakdown']}
        self.assertGreater(a['bulan'], 5)
        self.assertEqual(b['bulan'], 0)

    def test_climatology_fallback_for_far_dates(self):
        far = dict(LEONID, obs_time='2026-12-20T21:00', id='far')
        with net(payload(10), archive=archive_payload):
            r = pl.evaluate_event(far, -7.8, 110.37, None, NOW)
        self.assertEqual(r['weather']['kind'], 'climatology')
        self.assertIn('Indikatif', r['feasibility']['confidence'])

    def test_offline_never_fabricates(self):
        with net(down=True):
            r = pl.evaluate_event(LEONID, -7.8, 110.37, None, NOW)
        self.assertFalse(r['weather']['available'])
        self.assertIsNone(r['feasibility']['score'])

    def test_past_event_unavailable(self):
        with net(payload(10)):
            r = pl.evaluate_event(by_title('Close approach of the Moon and Mars', '2026-11-02'), -6.2, 106.8, None, NOW)
        self.assertTrue(r['is_past'])
        self.assertIsNone(r['feasibility']['score'])


class Plan(unittest.TestCase):
    def test_plan_ranks_upcoming_only_and_respects_instrument(self):
        with net(payload(lambda t: 15 if t.day % 2 else 85)):
            P = pl.plan(-7.8, 110.37, 'naked_eye', 2026, 11, NOW)
        by_id = {i['id']: i for i in P['items']}
        self.assertTrue(P['top'])
        for tid in P['top']:
            self.assertFalse(by_id[tid]['is_past'])
            self.assertFalse(by_id[tid]['needs_better_instrument'])
        scores = [by_id[t]['score'] for t in P['top']]
        self.assertEqual(scores, sorted(scores, reverse=True))


class Api(unittest.TestCase):
    def setUp(self):
        self.c = create_app().test_client()

    def test_validation(self):
        r = self.c.post('/observation/api/feasibility', json={'lat': 'abc', 'lon': 1})
        self.assertEqual(r.status_code, 400)
        r = self.c.post('/observation/api/feasibility', json={'lat': 200, 'lon': 1})
        self.assertEqual(r.status_code, 400)
        r = self.c.get('/observation/api/plan?lat=-7.8&lon=999')
        self.assertEqual(r.status_code, 400)

    def test_unknown_event(self):
        r = self.c.post('/observation/api/event-forecast', json={'event_id': 'nope', 'lat': -7, 'lon': 110})
        self.assertEqual(r.status_code, 404)

    def test_event_forecast_endpoint(self):
        with net(payload(20)), mock.patch.object(pl, 'datetime') as dt:
            dt.utcnow.return_value = NOW
            dt.strptime = datetime.strptime
            r = self.c.post('/observation/api/event-forecast',
                            json={'event_id': LEONID['id'], 'lat': -7.8, 'lon': 110.37, 'year': 2026, 'month': 11})
        j = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(j['weather']['available'])
        self.assertIn('breakdown', j['feasibility'])


if __name__ == '__main__':
    unittest.main()
