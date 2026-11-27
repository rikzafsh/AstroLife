"""Gazetir kota/kabupaten untuk AstroBot. Sumber utama: kota_data.csv (±500 titik acuan lengkap dengan elevasi dan zona waktu),
ditambah beberapa alias dan kota luar negeri. Mengembalikan hasil terstruktur agar bot dapat menanyakan ulang bila ambigu
atau menolak dengan jelas bila kota tidak dikenal (tidak diam-diam memakai lokasi Pengaturan)."""
import csv
import re
from functools import lru_cache
from pathlib import Path

from app.services.timezones import tz_from_lon

from .teks import bersih

CSV = Path(__file__).with_name('kota_data.csv')

# Koreksi atas kekeliruan jelas pada data sumber (dilaporkan kepada pemilik data):
KOREKSI_LINTANG = {'tarakan': 3.29823888888889}       # sumber bertanda minus; Tarakan di ±3,3° LU
TOLAK = {'limapuluh'}                                  # lintang 3,17 tidak mungkin untuk Sumatera Barat; gunakan "Sarilamak"

ALIAS = {'jogja': 'yogyakarta', 'jogjakarta': 'yogyakarta', 'yogya': 'yogyakarta', 'solo': 'surakarta', 'bali': 'denpasar',
         'aceh': 'banda aceh', 'lampung': 'bandarlampung', 'bandar lampung': 'bandarlampung', 'lubuk linggau': 'lubuklinggau',
         'kutai': 'tenggarong', 'banjar': 'banjar'}
LUAR_NEGERI = {'makkah': (21.4225, 39.8262), 'mekah': (21.4225, 39.8262), 'mekkah': (21.4225, 39.8262), 'madinah': (24.4672, 39.6111),
               'medina': (24.4672, 39.6111), 'kairo': (30.0444, 31.2357), 'istanbul': (41.0082, 28.9784), 'kuala lumpur': (3.1390, 101.6869),
               'singapura': (1.3521, 103.8198), 'brunei': (4.9031, 114.9398), 'london': (51.5072, -0.1276), 'amsterdam': (52.3676, 4.9041),
               'tokyo': (35.6762, 139.6503), 'sydney': (-33.8688, 151.2093), 'new york': (40.7128, -74.0060), 'riyadh': (24.7136, 46.6753),
               'dubai': (25.2048, 55.2708)}
# kata biasa yang juga nama tempat: baru dianggap kota bila didahului kata penunjuk (di/dari/untuk/kota ...)
PERLU_PENUNJUK = {'sumber', 'tanjung', 'benteng', 'banda', 'seram', 'salak', 'tais', 'baros', 'maba', 'weda', 'talu', 'batu', 'pati',
                  'serang', 'rantau', 'metro', 'duri', 'baa', 'soe', 'raha', 'ende', 'liwa', 'koba', 'lebak', 'bima', 'buton', 'natuna', 'mesuji'}
PENUNJUK = {'di', 'dari', 'untuk', 'ke', 'kota', 'kabupaten', 'kab', 'kalau', 'wilayah', 'daerah', 'lokasi', 'sekitar', 'dekat', 'area'}
BUKAN_KOTA = {'tempatku', 'lokasiku', 'rumahku', 'disini', 'sekitarku', 'kotaku', 'daerahku', 'tempat', 'sini', 'situ', 'sana', 'saya', 'aku', 'kami', 'kita', 'lokasi', 'pengaturan', 'rumah', 'hari', 'besok', 'lusa', 'kemarin',
              'sekarang', 'nanti', 'tanggal', 'tahun', 'bulan', 'minggu', 'pekan', 'jam', 'berapa', 'ini', 'itu', 'indonesia', 'dunia',
              'mana', 'bumi', 'langit', 'yogyakarta_', 'setempat', 'tempat', 'kamu', 'anda', 'wib', 'wita', 'wit', 'islam', 'aplikasi',
              'astrolife', 'sini', 'pagi', 'siang', 'sore', 'malam', 'subuh', 'zuhur', 'asar', 'magrib', 'isya', 'imsak', 'duha', 'terbit',
              'peta', 'kompas', 'ka\'bah', 'kabah', 'makkah_', 'menurut', 'dengan', 'dan', 'atau', 'yang', 'apa', 'bagaimana', 'cara'}
BERHENTI = BUKAN_KOTA | {'jam', 'pada', 'saat', 'kalau', 'jika', 'bila', 'yaitu', 'adalah', 'dengan', 'menurut', 'tahun', 'metode'}


@lru_cache(maxsize=1)
def _muat():
    kota = {}                                        # kunci tanpa spasi -> daftar entri
    with open(CSV, encoding='utf8') as fh:
        baris_csv = list(csv.DictReader(fh, delimiter=';'))
    for r in baris_csv:
        nama = r['Kota_Kabupaten'].strip()
        kunci = bersih(nama).replace(' ', '')
        if kunci in TOLAK:
            continue
        lat = float(r['Lintang'].replace(',', '.'))
        lat = KOREKSI_LINTANG.get(kunci, lat)
        lon = float(r['Bujur'].replace(',', '.'))
        pusat = r['Pusat_Koordinat'].strip()
        e = {'nama': nama, 'provinsi': r['Provinsi'].strip(), 'pusat': None if pusat in ('', '0') else pusat, 'lat': lat, 'lon': lon,
             'elev': float(r['Elevasi'].replace(',', '.')), 'tz': float(r['Zona_Waktu']), 'sumber': 'csv'}
        kota.setdefault(kunci, []).append(e)
    for al, asli in ALIAS.items():
        k = bersih(asli).replace(' ', '')
        if k in kota:
            kota.setdefault(bersih(al).replace(' ', ''), kota[k])
    for n, (lat, lon) in LUAR_NEGERI.items():
        kota.setdefault(bersih(n).replace(' ', ''), [{'nama': n.title(), 'provinsi': 'Luar negeri', 'pusat': None, 'lat': lat, 'lon': lon,
                                                      'elev': 0.0, 'tz': tz_from_lon(lon), 'sumber': 'luar', }])
    prov = sorted({e['provinsi'] for v in kota.values() for e in v if e['sumber'] == 'csv'}, key=lambda p: -len(p))
    return kota, prov


def _tok(teks):
    return re.findall(r"[a-z0-9']+", bersih(teks))


def _entri(e, ambigu=None):
    return {'status': 'ok', 'nama': e['nama'], 'provinsi': e['provinsi'], 'pusat': e['pusat'], 'lat': e['lat'], 'lon': e['lon'],
            'elev': e['elev'], 'tz': e['tz'], 'sumber': e['sumber']}


def cari_lokasi(teks: str):
    """None bila tidak menyebut lokasi. Selain itu dict dengan status:
    ok (nama, lat, lon, elev, tz, provinsi, pusat) | ambigu (nama, pilihan[provinsi]) | koordinat | tak_dikenal (nama)."""
    kota, provinsi = _muat()
    m = re.search(r'(-?\d{1,2}[.,]\d{2,})\s*[,;/]?\s*(-?\d{1,3}[.,]\d{2,})', teks.replace(' ,', ','))
    if m and '.' in m.group(1) + m.group(2):
        la, lo = float(m.group(1).replace(',', '.')), float(m.group(2).replace(',', '.'))
        if -90 <= la <= 90 and -180 <= lo <= 180:
            return {'status': 'koordinat', 'nama': f'{la:.4f}, {lo:.4f}', 'lat': la, 'lon': lo, 'elev': 0.0, 'tz': tz_from_lon(lo),
                    'provinsi': None, 'pusat': None, 'sumber': 'koordinat'}
    t = _tok(teks)
    ttxt = ' '.join(t)
    i = 0
    while i < len(t):
        for n in (4, 3, 2, 1):                       # nama panjang diutamakan; spasi diabaikan (Lubuk Linggau = Lubuklinggau)
            if i + n > len(t):
                continue
            kunci = ''.join(t[i:i + n])
            if kunci in kota:
                if kunci in PERLU_PENUNJUK and not any(x in PENUNJUK for x in t[max(0, i - 3):i]):
                    continue
                if n == 1 and kunci in BUKAN_KOTA:
                    continue
                daftar = kota[kunci]
                if len(daftar) > 1:
                    cocok = [e for e in daftar if bersih(e['provinsi']) in ttxt]
                    if len(cocok) == 1:
                        return _entri(cocok[0])
                    return {'status': 'ambigu', 'nama': daftar[0]['nama'], 'pilihan': [e['provinsi'] for e in daftar]}
                return _entri(daftar[0])
        i += 1
    # kota tidak dikenal: kata setelah penunjuk (di/dari/untuk/ke/kota) yang bukan kata umum
    for i, w in enumerate(t):
        if w in ('di', 'dari', 'untuk', 'ke', 'kota', 'kabupaten', 'kab') and i + 1 < len(t):
            nm = []
            for x in t[i + 1:i + 4]:
                if x in BERHENTI or x.isdigit() or x in PENUNJUK:
                    break
                nm.append(x)
            if nm and nm[0] not in BUKAN_KOTA and len(' '.join(nm)) >= 3:
                return {'status': 'tak_dikenal', 'nama': ' '.join(nm).title()}
    return None


cari_kota = cari_lokasi                                   # nama lama


def cari_semua_lokasi(teks: str) -> list:
    """Semua kota yang dikenal (status ok) dalam teks, berurutan menurut kemunculan, tanpa duplikat. Untuk perbandingan dua lokasi."""
    kota, _ = _muat()
    t = _tok(teks)
    ttxt = ' '.join(t)
    hasil, i = [], 0
    while i < len(t):
        maju = 1
        for n in (4, 3, 2, 1):
            if i + n > len(t):
                continue
            kunci = ''.join(t[i:i + n])
            if kunci not in kota:
                continue
            if kunci in PERLU_PENUNJUK and not any(x in PENUNJUK for x in t[max(0, i - 3):i]):
                continue
            if n == 1 and kunci in BUKAN_KOTA:
                continue
            daftar = kota[kunci]
            if len(daftar) > 1:
                cocok = [e for e in daftar if bersih(e['provinsi']) in ttxt]
                if len(cocok) != 1:
                    hasil.append({'status': 'ambigu', 'nama': daftar[0]['nama'], 'pilihan': [e['provinsi'] for e in daftar]})
                    maju = n
                    break
                daftar = cocok
            e = _entri(daftar[0])
            if all(e['nama'] != x.get('nama') for x in hasil):
                hasil.append(e)
            maju = n
            break
        i += maju
    return hasil
