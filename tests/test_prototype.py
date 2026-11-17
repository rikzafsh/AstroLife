"""Tes regresi prototipe pencari event terhadap data in-the-sky.org (WIB). Mesin sementara: toleransi sengaja longgar."""
import unittest
from datetime import datetime

from prototype import find_events as F

EV = F.find_all(2026, 11)


def near(kind, bodies, when):
    c = [e for e in EV if e['kind'] == kind and set(e['bodies']) == set(bodies)]
    e = min(c, key=lambda e: abs((F.jd_to_wib(e['jd']) - when).total_seconds()))
    return abs((F.jd_to_wib(e['jd']) - when).total_seconds()) / 60.0, e


class Prototype(unittest.TestCase):
    def test_moon_phases_within_5_min(self):
        for kind, when in [('last_quarter', datetime(2026, 11, 2, 3, 28)), ('first_quarter', datetime(2026, 11, 17, 18, 48)),
                           ('full_moon', datetime(2026, 11, 24, 21, 53))]:
            self.assertLess(near(kind, ['moon'], when)[0], 5, kind)

    def test_moon_planet_events_within_15_min(self):
        for kind, b, when in [('close', ['moon', 'mars'], datetime(2026, 11, 2, 20, 39)),
                              ('conj_ra', ['moon', 'mars'], datetime(2026, 11, 2, 21, 24)),
                              ('close', ['moon', 'jupiter'], datetime(2026, 11, 3, 5, 45)),
                              ('close', ['moon', 'saturn'], datetime(2026, 11, 21, 3, 2)),
                              ('close', ['moon', 'm45'], datetime(2026, 11, 24, 18, 45)),
                              ('close', ['moon', 'mars'], datetime(2026, 11, 30, 23, 54))]:
            self.assertLess(near(kind, b, when)[0], 15, (kind, b))

    def test_mercury_definitions(self):
        self.assertLess(near('dichotomy', ['mercury'], datetime(2026, 11, 18, 15, 55))[0], 10)
        self.assertLess(near('greatest_elongation_west', ['mercury'], datetime(2026, 11, 21, 7, 33))[0], 10)

    def test_jakarta_occultation_of_jupiter(self):
        """Sumber (screenshot): hilang 04:39 WIB, muncul 06:08 WIB."""
        occ = [e for e in EV if e['kind'] == 'occultation' and 'jupiter' in e['bodies']]
        self.assertEqual(len(occ), 1)
        o = occ[0]
        self.assertLess(abs((F.jd_to_wib(o['ingress']) - datetime(2026, 11, 3, 4, 39)).total_seconds()) / 60, 10)
        self.assertLess(abs((F.jd_to_wib(o['egress']) - datetime(2026, 11, 3, 6, 8)).total_seconds()) / 60, 10)

    def test_planet_planet_known_engine_limit(self):
        """Batas mesin sementara: pasangan planet-planet lambat bisa meleset ~2 jam (galat posisi ~2 menit busur)."""
        d, _ = near('close', ['jupiter', 'mars'], datetime(2026, 11, 16, 9, 4))
        self.assertLess(d, 180)


if __name__ == '__main__':
    unittest.main()


class Parsing(unittest.TestCase):
    def test_event_time_formats(self):
        from app.services.scraper_service import parse_event_time as P
        r = P('Mon, 02 Nov 2026 at 20:39 WIB · 5 days ago')
        self.assertEqual((r['start'], r['tz'], r['end']), (datetime(2026, 11, 2, 20, 39), 'WIB', None))
        for t in ['TUE, 03 NOV 2026 FROM 03:45 WIB (20:45 UTC) TO 07:45 WIB 14 DAYS AGO',
                  'Tue, 03 Nov 2026from03:45 WIB(20:45 UTC)to07:45 WIB']:
            r = P(t)
            self.assertEqual((r['start'], r['end'], r['tz']), (datetime(2026, 11, 3, 3, 45), datetime(2026, 11, 3, 7, 45), 'WIB'))
            self.assertEqual(r['mid'], datetime(2026, 11, 3, 5, 45))
        self.assertIsNone(P('Wed, 18 Nov 2026'))        # tanpa jam -> tidak ditebak
        self.assertEqual(P('Tue 03 November 2026 at 05:45 UTC')['tz'], 'UTC')

    def test_occultation_paragraph_is_parsed(self):
        from app.services.detail_parser import parse_in_the_sky_detail_html as D
        html = ('<p class="widetitle">Lunar occultation of Jupiter - In-The-Sky.org</p>'
                '<div class="link_green">TUE, 03 NOV 2026 FROM 03:45 WIB (20:45 UTC) TO 07:45 WIB</div>'
                '<div class="newsbody"><p>The Moon will pass in front of Jupiter, creating a lunar occultation visible '
                'from countries and territories including Indonesia.</p><p>The occultation will be visible from Jakarta. '
                'It will begin with the disappearance of Jupiter behind the Moon at 04:39 WIB in the north-eastern sky at an '
                'altitude of 51.5 degrees. Its reappearance will be visible at 06:08 WIB, though in daylight.</p></div>')
        r = D(html)
        self.assertEqual((r['occultation_ingress'], r['occultation_egress']), ('04:39 (WIB)', '06:08 (WIB)'))
        self.assertEqual(r['occultation_altitude'], '51.5')
        self.assertIn('visible from Jakarta', r['visibility_summary'])
        self.assertTrue(r['description'].startswith('The Moon will pass'))


class Occultations(unittest.TestCase):
    def test_nine_global_occultations_found_with_expected_objects(self):
        w = [e for e in EV if e['kind'] == 'occ_window']
        got = sorted((F.jd_to_wib(e['jd']).day, e['bodies'][1]) for e in w)
        self.assertEqual(got, [(2, 'mars'), (3, 'jupiter'), (3, 'regulus'), (7, 'venus'), (11, 'antares'),
                               (14, 'sigma_sagittarii'), (26, 'beta_tauri'), (30, 'jupiter'), (30, 'regulus')])

    def test_jupiter_window_matches_source(self):
        e = next(e for e in EV if e['kind'] == 'occ_window' and e['bodies'][1] == 'jupiter' and F.jd_to_wib(e['jd']).day == 3)
        self.assertLess(abs((F.jd_to_wib(e['start']) - datetime(2026, 11, 3, 3, 45)).total_seconds()) / 60, 10)
        self.assertLess(abs((F.jd_to_wib(e['end']) - datetime(2026, 11, 3, 7, 45)).total_seconds()) / 60, 10)
