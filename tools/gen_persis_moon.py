"""Membuat app/persis/_data/moon_elp_ringkas.npz: deret ELPMPP02 Bulan yang dipangkas dari data penuh persis-times-js.
Hanya suku dengan |amplitudo| >= ambang yang dipertahankan (bujur/lintang dalam detik busur, jarak dalam km).
Pemakaian: python tools/gen_persis_moon.py <folder persis-times-js>
Galat terhadap deret penuh (diukur 300 titik acak, 1950-2050): bujur < 0,4", lintang < 0,4", jarak < 0,4 km."""
import re
import sys
from pathlib import Path

import numpy as np

AMBANG = {'l': 0.01, 'b': 0.01, 'r': 0.02}
root = Path(sys.argv[1])
pola = re.compile(r'PERSIS_DATA\["moon_([lbr]\d+)"\]=\{w:(\d+),n:(\d+),d:\[([^\]]*)\]\}')
grup = {}
for f in ('moon_elp_longitude.js', 'moon_elp_latitude.js', 'moon_elp_distance.js'):
    for nama, w, n, d in pola.findall((root / 'js/data' / f).read_text(encoding='utf8')):
        a = np.array(d.split(','), dtype=float).reshape(int(n), int(w))
        grup.setdefault(nama[0] + nama[1], []).append(a)          # l001..l013 -> 'l0'; l101 -> 'l1'
out, total = {}, 0
for k, v in sorted(grup.items()):
    a = np.vstack(v)
    a = a[np.abs(a[:, 0]) >= AMBANG[k[0]]]
    a = a[np.argsort(-np.abs(a[:, 0]))]
    out[k] = a
    total += len(a)
np.savez_compressed(Path(__file__).resolve().parent.parent / 'app/persis/_data/moon_elp_ringkas.npz', **out)
print('suku dipertahankan:', {k: len(v) for k, v in out.items()}, 'total', total)
