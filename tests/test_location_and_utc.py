"""
Regresi untuk kasus nyata: halaman in-the-sky.org dipakai dengan lokasi situs = IST (bukan Jakarta).
Fixture tests/fixtures/ist_sample.json berisi teks mentah ASLI dari scraping pengguna (30 event).
"""
import json
import statistics as st
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.services.scraper_service import enrich_raw_event, parse_event_time
from prototype import compare

FIX = Path(__file__).parent / 'fixtures' / 'ist_sample.json'
DATA = json.loads(FIX.read_text(encoding='utf-8'))


class UtcParsing(unittest.TestCase):
    def test_all_real_strings_parse(self):
        for e in DATA:
            self.assertIsNotNone(parse_event_time(e['peak_event_time']), e['title'])

    def test_conversion_to_wib_uses_utc_not_local_label(self):
        r = parse_event_time('Mon, 02 Nov 2026 at 01:58 IST (20:28 UTC)15\xa0days\xa0ago')     # IST jam 01:58 = UTC hari sebelumnya
        self.assertEqual((r['tz'], r['mid']), ('IST', datetime(2026, 11, 2, 3, 28)))
        r = parse_event_time('Tue, 03 Nov 2026from02:15 IST(20:45 UTC)to06:15 IST(00:45 UTC)14\xa0days\xa0ago')
        self.assertEqual((r['start'], r['end']), (datetime(2026, 11, 3, 3, 45), datetime(2026, 11, 3, 7, 45)))
        r = parse_event_time('Sat, 14 Nov 2026from01:31 IST(20:01 UTC)to06:09 IST(00:39 UTC)3\xa0days\xa0ago')
        self.assertEqual((r['start'], r['end']), (datetime(2026, 11, 14, 3, 1), datetime(2026, 11, 14, 7, 39)))

    def test_wib_and_utc_only_strings_still_work(self):
        self.assertEqual(parse_event_time('Mon, 02 Nov 2026 at 20:39 WIB')['mid'], datetime(2026, 11, 2, 20, 39))
        self.assertEqual(parse_event_time('Tue 03 November 2026 at 05:45 UTC')['mid'], datetime(2026, 11, 3, 12, 45))

    def test_unknown_zone_without_utc_is_refused(self):
        self.assertIsNone(parse_event_time('Mon, 02 Nov 2026 at 01:58 IST'))        # tidak menebak offset


class LocationGuard(unittest.TestCase):
    BASE = {'title': 'Close approach of the Moon and Mars', 'date': '2026-11-02', 'difficulty_key': 'naked_eye',
            'difficulty_label': 'Mata Telanjang', 'altitude': '58°', 'azimuth_direction': 'north-eastern horizon',
            'rising_time': '00:55', 'fading_time': '05:12', 'visibility_summary': 'From Mumbai, rising at 00:55.',
            'description': 'The Moon passes close to Mars.'}

    def test_non_jakarta_site_hides_location_specific_fields(self):
        e = enrich_raw_event(dict(self.BASE, peak_event_time='Mon, 02 Nov 2026 at 19:09 IST (13:39 UTC)', source_tz='IST'))
        self.assertFalse(e['location_ok'])
        self.assertEqual((e['sky_position']['altitude'], e['sky_position']['direction']), ('Tidak dirilis', 'Tidak dirilis'))
        self.assertNotIn('Mumbai', e['description'])
        self.assertEqual(e['peak_time'], '2026-11-02T20:39')          # jam puncak tetap benar (dari UTC)

    def test_guard_works_without_source_tz_field(self):
        """JSON hasil scraping lama pengguna belum punya source_tz: zona harus dibaca dari teks jam puncak."""
        e = enrich_raw_event(dict(self.BASE, peak_event_time='Mon, 02 Nov 2026 at 19:09 IST (13:39 UTC)15\xa0days\xa0ago'))
        self.assertFalse(e['location_ok'])
        self.assertEqual(e['sky_position']['altitude'], 'Tidak dirilis')

    def test_wib_site_keeps_fields(self):
        e = enrich_raw_event(dict(self.BASE, peak_event_time='Mon, 02 Nov 2026 at 20:39 WIB', source_tz='WIB'))
        self.assertTrue(e['location_ok'])
        self.assertEqual(e['sky_position']['altitude'], '58°')


class CompareOnRealData(unittest.TestCase):
    def test_real_ist_data_matches_computation(self):
        with tempfile.TemporaryDirectory() as d:
            _, deltas, rows, not_cov, unreadable, extra = compare.run(str(FIX), 2026, 11, d)
        self.assertEqual(unreadable, [])
        allv = [abs(x) for v in deltas.values() for x in v]
        self.assertEqual(len(allv), 39)
        self.assertLess(st.median(allv), 5)
        # Selisih > 15 menit hanya boleh pada kasus yang sudah dijelaskan (mesin sementara / definisi), bukan yang lain.
        known = ('Conjunction of Jupiter and Mars', 'Close approach of Jupiter and Mars', 'Venus at greatest brightness')
        for title, src, ours, delta, kind in rows:
            if ours is not None and abs(delta) > 15:
                self.assertIn(title, known, (title, delta))


if __name__ == '__main__':
    unittest.main()
