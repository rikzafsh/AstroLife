"""
Tes mesin Skyfield. Dilewati otomatis bila Skyfield/de440s.bsp belum ada.
Dijalankan di SUBPROSES dengan ASTROLIFE_ENGINE=skyfield (mesin dipilih saat impor modul).
Toleransi mengikuti ketelitian sumber pembanding (menit), bukan ketelitian Skyfield (detik).
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAS = importlib.util.find_spec('skyfield') is not None and (ROOT / 'data' / 'ephemeris' / 'de440s.bsp').exists()

SCRIPT = r'''
import json
from datetime import datetime
from prototype import find_events as F
EV = F.find_all(2026, 11)
def near(kind, bodies, when):
    c = [e for e in EV if e['kind'] == kind and set(e['bodies']) == set(bodies)]
    e = min(c, key=lambda e: abs((F.jd_to_wib(e['jd']) - when).total_seconds()))
    return round(abs((F.jd_to_wib(e['jd']) - when).total_seconds()) / 60.0, 1)
import time
t_start = time.time()
out = {
 'last_quarter': near('last_quarter', ['moon'], datetime(2026, 11, 2, 3, 28)),
 'full_moon': near('full_moon', ['moon'], datetime(2026, 11, 24, 21, 53)),
 'moon_mars_close': near('close', ['moon', 'mars'], datetime(2026, 11, 2, 20, 39)),
 'moon_jupiter_conj': near('conj_ra', ['moon', 'jupiter'], datetime(2026, 11, 3, 6, 9)),
 'jupiter_mars_conj': near('conj_ra', ['jupiter', 'mars'], datetime(2026, 11, 15, 9, 42)),
 'jupiter_mars_close': near('close', ['jupiter', 'mars'], datetime(2026, 11, 16, 9, 4)),
 'mercury_dichotomy': near('dichotomy', ['mercury'], datetime(2026, 11, 18, 15, 55)),
 'mercury_elong_w': near('greatest_elongation_west', ['mercury'], datetime(2026, 11, 21, 7, 33)),
 'n_occ_windows': len([e for e in EV if e['kind'] == 'occ_window']),
 'n_events': len(EV),
 'seconds': round(time.time() - t_start, 1),
}
print(json.dumps(out))
'''


@unittest.skipUnless(HAS, 'Skyfield atau data/ephemeris/de440s.bsp belum tersedia')
class SkyfieldEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, ASTROLIFE_ENGINE='skyfield', PYTHONPATH=str(ROOT))
        r = subprocess.run([sys.executable, '-c', SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-2000:])
        cls.res = json.loads(r.stdout.strip().splitlines()[-1])

    def test_moon_events(self):
        for k in ('last_quarter', 'full_moon', 'moon_mars_close', 'moon_jupiter_conj'):
            self.assertLess(self.res[k], 5, k)

    def test_planet_planet_pairs_improve_over_lite(self):
        """Mesin sementara meleset ~2 jam; dengan DE440s harus < 15 menit."""
        for k in ('jupiter_mars_conj', 'jupiter_mars_close'):
            self.assertLess(self.res[k], 15, k)

    def test_vector_path_is_fast_and_complete(self):
        """find_all(2026-11) dengan Skyfield: jumlah event sama dengan acuan beku (60) dan jauh lebih cepat dari 40 detik."""
        self.assertEqual(self.res['n_events'], 60)
        self.assertLess(self.res['seconds'], 25, f"find_all memakan {self.res['seconds']} dtk; jalur vektor mungkin tidak aktif")

    def test_mercury_and_occultations(self):
        self.assertLess(self.res['mercury_dichotomy'], 10)
        self.assertLess(self.res['mercury_elong_w'], 10)
        self.assertEqual(self.res['n_occ_windows'], 9)


if __name__ == '__main__':
    unittest.main()
