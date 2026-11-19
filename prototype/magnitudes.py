"""
Magnitudo tampak (rumus Astronomical Almanac) dan data bintang tetap. Murni matematika, dipakai kedua mesin posisi.
Ketelitian ~0,1-0,3 mag: cukup untuk kategori keterlihatan (mata telanjang / binokular / teleskop), bukan fotometri.
"""
import math

# Magnitudo visual bintang/gugus tetap
FIXED_MAG = {'regulus': 1.35, 'antares': 1.06, 'spica': 0.97, 'aldebaran': 0.85,
             'sigma_sagittarii': 2.05, 'beta_tauri': 1.65, 'm45': 1.6, 'm44': 3.1}

# Kutub utara bidang cincin Saturnus (J2000), untuk koreksi cincin
SATURN_POLE_RA, SATURN_POLE_DEC = 40.589, 83.537


def saturn_ring_sin_b(ra_deg: float, dec_deg: float) -> float:
    a0, d0, a, d = map(math.radians, (SATURN_POLE_RA, SATURN_POLE_DEC, ra_deg, dec_deg))
    return abs(math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a0 - a))


def planet_mag(body: str, r: float, delta: float, i_deg: float, ra=None, dec=None):
    """r: jarak Matahari-planet (AU); delta: jarak Bumi-planet (AU); i: sudut fase (derajat)."""
    base = 5 * math.log10(r * delta)
    i = i_deg
    if body == 'mercury':
        return -0.42 + base + 0.0380 * i - 0.000273 * i ** 2 + 0.000002 * i ** 3
    if body == 'venus':
        return -4.40 + base + 0.0009 * i + 0.000239 * i ** 2 - 0.00000065 * i ** 3
    if body == 'mars':
        return -1.52 + base + 0.016 * i
    if body == 'jupiter':
        return -9.40 + base + 0.005 * i
    if body == 'saturn':
        sb = saturn_ring_sin_b(ra, dec) if ra is not None else 0.2
        return -8.88 + base - 2.60 * sb + 1.25 * sb * sb
    if body == 'uranus':
        return -7.19 + base + 0.002 * i
    if body == 'neptune':
        return -6.87 + base
    raise KeyError(body)


def moon_mag(elongation_deg: float) -> float:
    """Magnitudo Bulan dari elongasi (sudut fase = 180 - elongasi)."""
    i = 180.0 - elongation_deg
    return -12.74 + 0.026 * abs(i) + 4e-9 * i ** 4
