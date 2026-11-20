"""
Bandingkan posisi ephem_lite vs Skyfield/DE440s. Jalankan:  python -m prototype.verify_engine
Selisih besar (> 5 menit busur) pada benda tertentu berarti adapter keliru ATAU mesin sementara kasar.
Nilai yang diharapkan: Bulan/Matahari ~ <2', planet ~ 1-3' (itulah galat mesin sementara).
"""
import sys

from app.services import astro_core as ac

try:
    from prototype import ephem_lite as L
    from prototype import ephem_skyfield as S
except ImportError as e:
    sys.exit(f"Skyfield belum terpasang ({e}).\nJalankan: pip install -r requirements-prototype.txt")

DATES = [(2026, 11, 3, 0), (2026, 11, 10, 12), (2026, 11, 17, 0), (2026, 11, 24, 12), (2026, 12, 1, 0)]
BODIES = ['moon', 'sun', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'm45', 'regulus']


def jd(y, m, d, h):
    return ac.jd_from_jdn(ac.to_jdn(y, m, d), h)


print(f"Mesin: {S.NAME}\nSelisih posisi ephem_lite vs Skyfield (menit busur):\n")
print(f"{'benda':10}" + ''.join(f'{y}-{m:02d}-{d:02d}'.rjust(12) for y, m, d, h in DATES) + '   status')
worst = {}
for b in BODIES:
    vals = [L.separation(*L.eq(b, jd(*dt)), *S.eq(b, jd(*dt))) * 60 for dt in DATES]
    worst[b] = max(vals)
    print(f'{b:10}' + ''.join(f'{v:12.2f}' for v in vals) + ('   OK' if max(vals) < 5 else '   <-- CEK'))
bad = [b for b, v in worst.items() if v >= 5]
print('\nKesimpulan:', 'semua benda konsisten (< 5 menit busur).' if not bad else
      f"benda berikut menyimpang > 5': {', '.join(bad)}. Salah satu mesin (atau adapter) perlu diperiksa.")
t = jd(2026, 11, 3, 0)
print(f"\nContoh Bulan-Jupiter 3 Nov 00:00 UT: lite {L.sep('moon', 'jupiter', t):.4f} deg | skyfield {S.sep('moon', 'jupiter', t):.4f} deg")


# ---------------------------------------------------------------------------
# Uji jalur VEKTOR Skyfield: harus identik dengan jalur skalar, dan lebih cepat
# ---------------------------------------------------------------------------
import time

import numpy as np

print('\n=== Konsistensi jalur vektor vs skalar (Skyfield) ===')
grid = jd(2026, 11, 1, 0) + np.arange(0, 30, 1 / 24)
bad_batch = []
for b in ['moon', 'sun', 'mars', 'jupiter', 'saturn', 'uranus', 'regulus', 'm45']:
    ra_v, dec_v = S.eq_many(b, grid)
    lon_v, lat_v = S.ecl_many(b, grid)
    pick = [0, 100, 359, 719]
    err = max(max(abs(S.wrap180(ra_v[i] - S.eq(b, grid[i])[0])), abs(dec_v[i] - S.eq(b, grid[i])[1]),
                  abs(S.wrap180(lon_v[i] - S.ecl(b, grid[i])[0])), abs(lat_v[i] - S.ecl(b, grid[i])[1])) for i in pick)
    ok = err < 1e-6
    if not ok:
        bad_batch.append(b)
    print(f'  {b:10} selisih maks vektor-skalar: {err:.2e} deg   {"OK" if ok else "<-- CEK"}')
sd_v, hp_v = S.moon_radii_many(grid[:5])
err = max(abs(sd_v[i] - S.moon_semidiameter_deg(grid[i])) + abs(hp_v[i] - S.moon_horizontal_parallax_deg(grid[i])) for i in range(5))
print(f'  radii Bulan selisih maks: {err:.2e} deg   {"OK" if err < 1e-8 else "<-- CEK"}')

t = time.time(); [S.eq('mars', g + 1e-7) for g in grid[:100]]; t_scalar = (time.time() - t) / 100
t = time.time(); S.eq_many('mars', grid + 2e-7); t_vec = time.time() - t
print(f'\nKecepatan: skalar {t_scalar * 1000:.2f} ms/panggilan | vektor {t_vec * 1000:.1f} ms untuk {len(grid)} waktu '
      f'(~{t_scalar * len(grid) / max(t_vec, 1e-9):.0f}x lebih cepat per waktu)')
print('Kesimpulan vektor:', 'konsisten dengan skalar.' if not bad_batch and err < 1e-8 else f'ADA SELISIH ({bad_batch}); jalankan dengan ASTROLIFE_BATCH=0 dan laporkan.')
