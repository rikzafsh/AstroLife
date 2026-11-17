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
