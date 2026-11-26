"""Tes regresi pencari event terhadap nilai acuan hasil validasi (WIB; lihat knowledge.md). Mesin sementara: toleransi sengaja longgar."""
import json
import os
import unittest
from pathlib import Path
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
        """Acuan validasi: hilang 04:39 WIB, muncul 06:08 WIB."""
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


class VectorFinders(unittest.TestCase):
    """Jalur vektor (cepat) HARUS mereproduksi hasil jalur skalar lama yang dibekukan di fixture."""
    REF = json.loads((Path(__file__).parent / 'fixtures' / 'find_window_reference.json').read_text(encoding='utf-8'))

    def _compare(self, key, tol_s=5):
        y, m = map(int, key.split('-'))
        new = F.find_all(y, m, include_local=False)
        old = self.REF[key]
        self.assertEqual(len(new), len(old), key)
        for o in old:
            cand = [e for e in new if e['kind'] == o['kind'] and list(e['bodies']) == o['bodies']]
            self.assertTrue(cand, (key, o['kind'], o['bodies']))
            n = min(cand, key=lambda e: abs(e['jd'] - o['jd']))
            self.assertLess(abs(n['jd'] - o['jd']) * 86400, tol_s, (key, o['kind'], o['bodies']))
            for k in ('start', 'end'):
                if k in o:
                    self.assertLess(abs(n[k] - o[k]) * 86400, tol_s, (key, o['kind'], k))

    def test_batch_path_matches_frozen_reference(self):
        self.assertTrue(F.USE_BATCH or os.environ.get('ASTROLIFE_BATCH') == '0')
        for key in self.REF:
            self._compare(key)

    def test_scalar_fallback_still_matches(self):
        old = F.USE_BATCH
        F.USE_BATCH = False
        try:
            self._compare('2026-11')
        finally:
            F.USE_BATCH = old

    def test_month_end_minimum_is_not_lost(self):
        """Regresi: minimum Bulan-Mars 30 Nov 23:54 WIB jatuh 6 menit sebelum batas bulan."""
        evs = F.find_all(2026, 11, include_local=False)
        close = [e for e in evs if e['kind'] == 'close' and set(e['bodies']) == {'moon', 'mars'}]
        self.assertEqual(len(close), 2)
        self.assertLess(abs((F.jd_to_wib(close[-1]['jd']) - datetime(2026, 11, 30, 23, 54)).total_seconds()) / 60, 12)

    def test_vector_tools_on_synthetic_functions(self):
        import numpy as np
        r = F.roots_vec(lambda t: np.sin(t), 3.0, 7.0, 0.5)
        self.assertEqual(len(r), 2)
        self.assertAlmostEqual(r[0], np.pi, places=6)
        self.assertAlmostEqual(r[1], 2 * np.pi, places=6)
        # jarak sudut berbentuk V (lintasan hampir tepat): minimum harus eksak lewat f^2
        t0, d, v = 10.0, 0.01, 0.5 * 24            # derajat/hari
        f = lambda t: np.sqrt(d * d + (v * (np.asarray(t) - t0)) ** 2)
        (tm, fm), = F.minima_vec(f, 9.0, 11.0, 1 / 24, squared=True)
        self.assertLess(abs(tm - t0) * 86400, 1.0)
        self.assertAlmostEqual(fm, d, places=6)
        self.assertEqual(F.roots_vec(lambda t: np.cos(t) + 2, 0, 10, 0.5), [])      # tanpa akar
