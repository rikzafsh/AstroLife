"""Gazetir kota kecil (nama → lintang, bujur) untuk pertanyaan seperti 'jadwal salat di Surabaya'."""
from .teks import bersih

KOTA = {
    'yogyakarta': (-7.7956, 110.3695), 'jogja': (-7.7956, 110.3695), 'jakarta': (-6.2088, 106.8456), 'bandung': (-6.9175, 107.6191),
    'surabaya': (-7.2575, 112.7521), 'semarang': (-6.9667, 110.4167), 'surakarta': (-7.5666, 110.8281), 'solo': (-7.5666, 110.8281),
    'malang': (-7.9666, 112.6326), 'bogor': (-6.5950, 106.8166), 'bekasi': (-6.2383, 106.9756), 'tangerang': (-6.1783, 106.6319),
    'depok': (-6.4025, 106.7942), 'cirebon': (-6.7063, 108.5570), 'tasikmalaya': (-7.3274, 108.2207), 'purwokerto': (-7.4242, 109.2396),
    'magelang': (-7.4797, 110.2177), 'kediri': (-7.8166, 112.0116), 'madiun': (-7.6298, 111.5239), 'jember': (-8.1845, 113.7000),
    'banyuwangi': (-8.2192, 114.3691), 'denpasar': (-8.6705, 115.2126), 'bali': (-8.6705, 115.2126), 'mataram': (-8.5833, 116.1167),
    'kupang': (-10.1772, 123.6070), 'medan': (3.5952, 98.6722), 'banda aceh': (5.5483, 95.3238), 'aceh': (5.5483, 95.3238),
    'padang': (-0.9471, 100.4172), 'pekanbaru': (0.5071, 101.4478), 'batam': (1.0456, 104.0305), 'jambi': (-1.6101, 103.6131),
    'palembang': (-2.9761, 104.7754), 'bengkulu': (-3.7928, 102.2608), 'bandar lampung': (-5.4500, 105.2667), 'lampung': (-5.4500, 105.2667),
    'pontianak': (-0.0263, 109.3425), 'palangkaraya': (-2.2136, 113.9108), 'banjarmasin': (-3.3194, 114.5908), 'balikpapan': (-1.2379, 116.8529),
    'samarinda': (-0.5022, 117.1536), 'makassar': (-5.1477, 119.4327), 'manado': (1.4748, 124.8421), 'palu': (-0.8917, 119.8707),
    'kendari': (-3.9985, 122.5129), 'gorontalo': (0.5435, 123.0568), 'ambon': (-3.6954, 128.1814), 'ternate': (0.7833, 127.3667),
    'jayapura': (-2.5337, 140.7181), 'sorong': (-0.8762, 131.2558), 'merauke': (-8.4932, 140.4018),
    'makkah': (21.4225, 39.8262), 'mekah': (21.4225, 39.8262), 'mekkah': (21.4225, 39.8262), 'madinah': (24.4672, 39.6111), 'medina': (24.4672, 39.6111),
    'kairo': (30.0444, 31.2357), 'istanbul': (41.0082, 28.9784), 'kuala lumpur': (3.1390, 101.6869), 'singapura': (1.3521, 103.8198),
    'brunei': (4.9031, 114.9398), 'london': (51.5072, -0.1276), 'amsterdam': (52.3676, 4.9041), 'tokyo': (35.6762, 139.6503),
    'sydney': (-33.8688, 151.2093), 'new york': (40.7128, -74.0060), 'riyadh': (24.7136, 46.6753), 'dubai': (25.2048, 55.2708),
}
_URUT = sorted(KOTA, key=lambda k: -len(k))


def cari_kota(teks: str):
    """Cari nama kota dalam teks; kembalikan (nama, lat, lon) atau None. Pencocokan kata utuh, nama panjang diutamakan."""
    t = f' {bersih(teks)} '
    for k in _URUT:
        if f' {k} ' in t or t.find(f' {k}?') >= 0 or t.find(f' {k},') >= 0:
            lat, lon = KOTA[k]
            return k.title(), lat, lon
    return None
