"""
Waktu lokal di API katalog, tautan 'analisis cuaca', API feasibility berwaktu lokal, dan konsistensi ID halaman.
"""
import os
os.environ['ASTROLIFE_ENGINE'] = 'lite'

import re
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import test_catalog as TC          # menyediakan katalog hasil hitung (lite) di folder sementara
import helpers as T                # pembantu: net(), payload(), fake_now()
from app import create_app
from app.services.timezones import tz_from_lon, tz_label
import app.routes.observation as O
from helpers import fake_now


def client():
    app = create_app()
    app.config['CATALOG_DIR'] = Path(TC.YEAR_DIR.name)
    return app.test_client()


class Timezones(unittest.TestCase):
    def test_labels_and_lon_mapping(self):
        self.assertEqual([tz_label(7), tz_label(8), tz_label(9)], ['WIB', 'WITA', 'WIT'])
        self.assertEqual(tz_label(5.5), 'UTC+5.5')
        self.assertEqual(tz_label(-5), 'UTC-5')
        self.assertEqual((tz_from_lon(110.4), tz_from_lon(119.4), tz_from_lon(140.7)), (7.0, 8.0, 9.0))


class CatalogLocalTimes(unittest.TestCase):
    def setUp(self):
        self.c = client()

    def ev(self, j, part):
        return next(e for e in j['events'] if part in e['title'])

    def test_api_exposes_zone_label_and_no_utc_in_ui_fields(self):
        j = self.c.get('/catalog/api/events?year=2026&month=11&lat=-6.2088&lon=106.8456').get_json()
        self.assertEqual(j['lokasi']['tz_label'], 'WIB')
        for e in j['events']:
            for t in e['times_local']:
                self.assertRegex(t['value'], r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')
                self.assertNotIn('UTC', t['label'])

    def test_times_follow_selected_location(self):
        jkt = self.c.get('/catalog/api/events?year=2026&month=11&lat=-6.2088&lon=106.8456').get_json()
        jpr = self.c.get('/catalog/api/events?year=2026&month=11&lat=-2.5337&lon=140.7181').get_json()
        self.assertEqual(jpr['lokasi']['tz_label'], 'WIT')
        a, b = self.ev(jkt, 'Okultasi Jupiter'), self.ev(jpr, 'Okultasi Jupiter')
        f = lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M')
        self.assertEqual((f(b['time_local']) - f(a['time_local'])).total_seconds(), 2 * 3600)      # WIT = WIB + 2 jam
        self.assertEqual((f(b['times_local'][0]['value']) - f(a['times_local'][0]['value'])).total_seconds(), 2 * 3600)

    def test_wx_link_material(self):
        j = self.c.get('/catalog/api/events?year=2026&month=11&lat=-6.2088&lon=106.8456').get_json()
        occ = self.ev(j, 'Okultasi Jupiter')
        self.assertEqual(occ['wx']['peak'], occ['time_local'].replace(' ', 'T'))
        self.assertTrue(occ['wx']['best'] and occ['wx']['best'] != occ['wx']['peak'])            # terbaik = saat okultasi lokal
        self.assertEqual(occ['wx']['default'], occ['wx']['best'])
        new_moon = self.ev(j, 'Bulan Baru')                                                      # tak dapat diamati -> waktu event
        self.assertIsNone(new_moon['wx']['best'])
        self.assertEqual(new_moon['wx']['default'], new_moon['wx']['peak'])


class EventTimePreferred(unittest.TestCase):
    def test_full_moon_is_evaluated_at_its_own_moment(self):
        j = client().get('/catalog/api/events?year=2026&month=11&lat=-6.2088&lon=106.8456').get_json()
        fm = next(e for e in j['events'] if e['title'] == 'Bulan Purnama')
        self.assertEqual(fm['wx']['best'], fm['wx']['peak'])                                     # 21:53 WIB, sudah dapat diamati
        self.assertTrue(fm['visibility']['headline'].startswith('Terbaik ' + fm['time_local'][11:]))

    def test_lunar_eclipse_uses_umbral_window(self):
        e = next(x for x in TC.EV if x['title'].startswith('Gerhana Bulan total'))
        from catalog import visibility as V
        v = V.evaluate(e, -6.2088, 106.8456)
        u0, u1 = e['details']['umbra_mulai_utc'], e['details']['umbra_selesai_utc']
        self.assertTrue(u0 <= v['best_time_utc'] <= u1)                                          # bukan fase penumbra


class FeasibilityLocalTime(unittest.TestCase):
    NOW = datetime(2026, 11, 2, 3, 0)

    def post(self, body, off=25200, now=None):
        """off = utc_offset_seconds yang dilaporkan penyedia cuaca untuk lokasi (WIB 25200, WIT 32400)."""
        with T.net(T.payload(20, off=off, start=datetime(2026, 11, 1), days=30)), mock.patch.object(O, 'datetime', fake_now(now or self.NOW)):
            return create_app().test_client().post('/observation/api/feasibility', json=body)

    def test_local_time_conversion_and_default_tz(self):
        r = self.post({'lat': -6.2088, 'lon': 106.8456, 'datetime_local': '2026-11-03T04:45'})
        j = r.get_json()
        self.assertEqual((r.status_code, j['when_local'], j['tz_label']), (200, '2026-11-03 04:45', 'WIB'))
        self.assertEqual(j['weather']['valid_local'], '2026-11-03 05:00')                         # jam prakiraan terdekat
        r = self.post({'lat': -2.5337, 'lon': 140.7181, 'datetime_local': '2026-11-03T06:45'}, off=32400).get_json()   # WIT = 21:45 UTC
        self.assertEqual((r['tz_label'], r['weather']['valid_local']), ('WIT', '2026-11-03 07:00'))

    def test_same_local_clock_different_zone_means_different_instant(self):
        wib = self.post({'lat': -6.2, 'lon': 106.8, 'datetime_local': '2026-11-03T04:45'}).get_json()
        wita = self.post({'lat': -6.2, 'lon': 106.8, 'datetime_local': '2026-11-03T04:45', 'tz': 8}, off=28800).get_json()
        self.assertEqual((wib['tz_label'], wita['tz_label']), ('WIB', 'WITA'))
        self.assertNotEqual(wib['moon_altitude_deg'], wita['moon_altitude_deg'])                  # satu jam berbeda -> Bulan bergeser

    def test_validation(self):
        self.assertEqual(self.post({'lat': -6, 'lon': 106, 'tz': 'x'}).status_code, 400)
        self.assertEqual(self.post({'lat': -6, 'lon': 106, 'tz': 20}).status_code, 400)
        self.assertEqual(self.post({'lat': -6, 'lon': 106, 'datetime_local': '03/11/2026 04:45'}).status_code, 400)

    def test_moon_as_object_is_not_penalised_for_moonlight(self):
        """17 Nov 2026 20:00 WIB: Bulan kuartal awal tinggi. Bila Bulan objek event, tak ada penalti cahaya Bulan."""
        body = {'lat': -6.2088, 'lon': 106.8456, 'datetime_local': '2026-11-17T20:00', 'event_type': 'General', 'difficulty': 'telescope'}
        now = datetime(2026, 11, 10, 3, 0)
        plain = self.post(body, now=now).get_json()
        moon = self.post({**body, 'involves_moon': True}, now=now).get_json()
        pen = lambda j: {b['faktor']: b['penalti'] for b in j['feasibility']['breakdown']}
        self.assertIsNotNone(plain['feasibility']['score'])
        self.assertGreater(pen(plain)['bulan'], 5)
        self.assertEqual(pen(moon).get('bulan', 0), 0)
        self.assertGreater(moon['feasibility']['score'], plain['feasibility']['score'])


class PageIds(unittest.TestCase):
    """Setiap id yang dirujuk JS harus ada di HTML (kecuali yang memang dibuat dinamis)."""
    DYNAMIC = {'show-all', 'ctx-clear'}

    def check(self, path):
        html = client().get(path).get_data(as_text=True)
        js = max(re.findall(r'<script>(.*?)</script>', html, re.S), key=len)
        ids = set(re.findall(r"(?:getElementById|byId)\('([\w-]+)'\)", js)) | set(re.findall(r"\$\('([\w-]+)'\)", js))
        have = set(re.findall(r'id="([\w-]+)"', html))
        self.assertEqual(sorted(ids - have - self.DYNAMIC), [], path)

    def test_catalog_page(self):
        self.check('/catalog/')
        html = client().get('/catalog/').get_data(as_text=True)
        for needle in ('cat-wrap', 'data-theme-set="light"', 'wx-mini', 'Analisis cuaca'):
            self.assertIn(needle, html)

    def test_observation_page(self):
        self.check('/observation/')
        html = client().get('/observation/').get_data(as_text=True)
        for needle in ('input-datetime', 'event-context', 'btn-now', 'tz-note'):
            self.assertIn(needle, html)


if __name__ == '__main__':
    unittest.main()
