"""
Calendar Laboratory Service
===========================
Sistem yang didukung:
1. Masehi (Gregorian; otomatis Julian sebelum 15 Okt 1582)
2. Hijriah Aritmetis (tabular, epoch sipil Jumat 16 Juli 622 M Julian, siklus 30 tahun)
3. Jawa Mataraman / Sultan Agungan (pasaran, wuku/pawukon, neptu; tanggal/bulan/tahun Jawa dari siklus kurup persis-times-js)
4. Jyotisa / Saka (tithi, paksa, nakshatra, yoga, karana, bulan lunar amanta, tahun Saka)
   + pencari kandidat tanggal dari unsur prasasti (tahun Saka, bulan, paksa, tithi, wara)

Catatan metodologis (juga ditampilkan di UI):
- Hijriah aritmetis adalah hisab urfi, bukan rukyat/wujudul hilal; dapat berbeda 1-2 hari
  dengan penetapan resmi (Kemenag/Muhammadiyah).
- Jyotisa dihitung dengan efemeris modern (Matahari & Bulan, ayanamsa Lahiri), BUKAN
  Surya Siddhanta. Tithi ditentukan pada sekitar matahari terbit lokal (06:00 WIB).
  Bulan adhika/ksaya belum dimodelkan.
"""
from app.services import astro_core as ac

# ---------------------------------------------------------------------------
# Nama-nama
# ---------------------------------------------------------------------------
HARI = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu']
NEPTU_HARI = {'Minggu': 5, 'Senin': 4, 'Selasa': 3, 'Rabu': 7, 'Kamis': 8, 'Jumat': 6, 'Sabtu': 9}
PASARAN = ['Legi', 'Pahing', 'Pon', 'Wage', 'Kliwon']
NEPTU_PASARAN = {'Legi': 5, 'Pahing': 9, 'Pon': 7, 'Wage': 4, 'Kliwon': 8}

BULAN_MASEHI = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli',
                'Agustus', 'September', 'Oktober', 'November', 'Desember']
BULAN_HIJRIAH = ['Muharram', 'Safar', 'Rabiul Awal', 'Rabiul Akhir', 'Jumadil Awal', 'Jumadil Akhir',
                 'Rajab', 'Syaban', 'Ramadan', 'Syawal', 'Zulkaidah', 'Zulhijah']
BULAN_JAWA = ['Sura', 'Sapar', 'Mulud', 'Bakda Mulud', 'Jumadilawal', 'Jumadilakir',
              'Rejeb', 'Ruwah', 'Pasa', 'Sawal', 'Sela', 'Besar']
WINDU_TAHUN = ['Alip', 'Ehé', 'Jimawal', 'Jé', 'Dal', 'Bé', 'Wawu', 'Jimakir']

WUKU = ['Sinta', 'Landep', 'Wukir', 'Kurantil', 'Tolu', 'Gumbreg', 'Warigalit', 'Warigagung',
        'Julungwangi', 'Sungsang', 'Dungulan', 'Kuningan', 'Langkir', 'Medangsia', 'Pujut',
        'Pahang', 'Krulut', 'Merakih', 'Tambir', 'Medangkungan', 'Maktal', 'Wuye', 'Manahil',
        'Prangbakat', 'Bala', 'Wugu', 'Wayang', 'Kulawu', 'Dukut', 'Watugunung']
SADWARA = ['Tungleh', 'Aryang', 'Warukung', 'Paniron', 'Was', 'Maulu']

TITHI_NAMA = ['Pratipada', 'Dwitiya', 'Tritiya', 'Caturthi', 'Panchami', 'Shashthi', 'Saptami',
              'Ashtami', 'Navami', 'Dashami', 'Ekadashi', 'Dwadashi', 'Trayodashi', 'Chaturdashi']
NAKSHATRA = ['Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu', 'Pushya',
             'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati',
             'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana',
             'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati']
YOGA = ['Vishkambha', 'Priti', 'Ayushman', 'Saubhagya', 'Shobhana', 'Atiganda', 'Sukarma', 'Dhriti',
        'Shula', 'Ganda', 'Vriddhi', 'Dhruva', 'Vyaghata', 'Harshana', 'Vajra', 'Siddhi', 'Vyatipata',
        'Variyan', 'Parigha', 'Shiva', 'Siddha', 'Sadhya', 'Shubha', 'Shukla', 'Brahma', 'Indra', 'Vaidhriti']
KARANA_BERULANG = ['Bava', 'Balava', 'Kaulava', 'Taitila', 'Gara', 'Vanija', 'Vishti']
# Bulan lunar amanta, ejaan Jawa Kuno (Caitra = 1)
BULAN_SAKA = ['Caitra', 'Waisakha', 'Jyestha', 'Asadha', 'Srawana', 'Bhadrawada',
              'Asuji', 'Kartika', 'Margasira', 'Pausa', 'Magha', 'Phalguna']
RASI = ['Mesha', 'Wrsabha', 'Mithuna', 'Karkata', 'Simha', 'Kanya', 'Tula', 'Wrscika', 'Dhanus',
        'Makara', 'Kumbha', 'Mina']

# Jangkar kalibrasi (fakta historis yang diketahui)
_ANCHOR_PASARAN_JDN = ac.to_jdn(1945, 8, 17)    # Jumat Legi (Proklamasi Kemerdekaan RI)
_ANCHOR_WUKU_JDN = ac.to_jdn(2023, 8, 2)        # Rabu Kliwon, Wuku Dungulan (Hari Raya Galungan 2023)
_ANCHOR_WUKU_DAY = WUKU.index('Dungulan') * 7 + 3   # Rabu = hari ke-3 dalam wuku (Minggu = 0)

JAWA_OFFSET = 512      # tahun Jawa = tahun Hijriah + 512 (sejak Sultan Agung, 1633 M)
JAWA_ALIP_BASE = 1555  # 1 Sura 1555 = tahun Alip


# ---------------------------------------------------------------------------
# Hijriah aritmetis
# ---------------------------------------------------------------------------
def is_hijri_leap(y: int) -> bool:
    return (11 * y + 14) % 30 < 11


def hijri_month_length(y: int, m: int) -> int:
    if m == 12:
        return 30 if is_hijri_leap(y) else 29
    return 30 if m % 2 == 1 else 29


def hijri_to_jdn(y: int, m: int, d: int) -> int:
    # ceil(29.5 * (m - 1)) = (59*(m-1) + 1) // 2
    return d + (59 * (m - 1) + 1) // 2 + (y - 1) * 354 + (3 + 11 * y) // 30 + 1948440 - 1


def jdn_to_hijri(jdn: int):
    y = (30 * (jdn - 1948440) + 10646) // 10631
    start_year = hijri_to_jdn(y, 1, 1)
    m = min(12, -(-((jdn - 29 - start_year) * 2) // 59) + 1)
    d = jdn - hijri_to_jdn(y, m, 1) + 1
    return y, m, d


# ---------------------------------------------------------------------------
# Jawa Mataraman
# ---------------------------------------------------------------------------
def pasaran_index(jdn: int) -> int:
    """0 = Legi pada jangkar 17 Agustus 1945."""
    return (jdn - _ANCHOR_PASARAN_JDN) % 5


def pawukon_day(jdn: int) -> int:
    """Hari ke-n (0..209) dalam siklus pawukon 210 hari."""
    return (_ANCHOR_WUKU_DAY + (jdn - _ANCHOR_WUKU_JDN)) % 210


def javanese_info(jdn: int) -> dict:
    """Weton, wuku, neptu (pasaran & pawukon) dan tanggal Jawa Sultan Agungan menurut siklus kurup (app/persis, port persis-times-js)."""
    from app.persis import kalender as pk
    wd = HARI[ac.weekday_index(jdn)]
    pas = PASARAN[pasaran_index(jdn)]
    pd = pawukon_day(jdn)
    wuku = WUKU[pd // 7]
    j = pk.jd_ke_jawa(jdn - 0.5)
    hd, hm, aj = j['tanggal'], j['bulan'], j['tahun']
    windu_idx = pk.no_tahun_jawa(aj) - 1
    return {
        'hari': wd,
        'pasaran': pas,
        'weton': f"{wd} {pas}",
        'neptu': NEPTU_HARI[wd] + NEPTU_PASARAN[pas],
        'neptu_rincian': f"{wd} {NEPTU_HARI[wd]} + {pas} {NEPTU_PASARAN[pas]}",
        'wuku': wuku,
        'wuku_no': pd // 7 + 1,
        'hari_pawukon': pd + 1,
        'sadwara': SADWARA[pd % 6],
        'tanggal': hd,
        'bulan': BULAN_JAWA[hm - 1],
        'bulan_no': hm,
        'tahun': aj,
        'tahun_windu': WINDU_TAHUN[windu_idx],
        'windu_ke': (aj - JAWA_ALIP_BASE) // 8 + 1,
        'teks': f"{wd} {pas}, {hd} {BULAN_JAWA[hm - 1]} {WINDU_TAHUN[windu_idx]} {aj} AJ, Wuku {wuku}",
    }


# ---------------------------------------------------------------------------
# Jyotisa / Saka
# ---------------------------------------------------------------------------
def tithi_name(n: int) -> str:
    """n = 1..30"""
    if n == 15:
        return 'Purnama'
    if n == 30:
        return 'Amawasya'
    return TITHI_NAMA[(n - 1) % 15]


def karana_name(k: int) -> str:
    """k = 1..60 (setengah tithi)"""
    if k == 1:
        return 'Kimstughna'
    if k == 58:
        return 'Shakuni'
    if k == 59:
        return 'Chatushpada'
    if k == 60:
        return 'Naga'
    return KARANA_BERULANG[(k - 2) % 7]


def jyotisa_info(jdn: int, utc_offset: float = 7.0, local_hour: float = 6.0) -> dict:
    """Unsur panchanga pada jam lokal tertentu (default 06:00, kira-kira matahari terbit di Jawa)."""
    jd = ac.jd_from_jdn(jdn, local_hour - utc_offset)
    sun = ac.sun_position(jd)['longitude']
    moon = ac.moon_longitude(jd)
    ay = ac.lahiri_ayanamsa(jd)
    sun_s, moon_s = ac.norm360(sun - ay), ac.norm360(moon - ay)
    elong = ac.norm360(moon - sun)

    tithi_n = int(elong // 12) + 1                    # 1..30
    tithi_paksa = tithi_n if tithi_n <= 15 else tithi_n - 15
    nak = int(moon_s // (360 / 27))
    yoga = int(ac.norm360(sun_s + moon_s) // (360 / 27))
    karana = int(elong // 6) + 1

    # Bulan lunar amanta: ditentukan oleh rasi Matahari saat bulan baru terakhir
    nm = ac.prev_new_moon(jd)
    sun_nm = ac.norm360(ac.sun_position(nm)['longitude'] - ac.lahiri_ayanamsa(nm))
    rasi_idx = int(sun_nm // 30)
    bulan_no = (rasi_idx + 1) % 12 + 1
    gy, gm, _, _ = ac.from_jdn(jdn)
    saka = gy - 79 if (gm <= 4 and bulan_no >= 10) else gy - 78
    paksa_pendek = 'Sukla' if tithi_n <= 15 else 'Krsna'

    return {
        'tithi_no': tithi_n,
        'tithi': tithi_name(tithi_n),
        'tithi_paksa': tithi_paksa,
        'paksa': 'Sukla (menaik)' if tithi_n <= 15 else 'Krsna (menurun)',
        'paksa_pendek': paksa_pendek,
        'nakshatra': NAKSHATRA[nak],
        'nakshatra_no': nak + 1,
        'yoga': YOGA[yoga],
        'karana': karana_name(karana),
        'bulan_saka': BULAN_SAKA[bulan_no - 1],
        'bulan_saka_no': bulan_no,
        'tahun_saka': saka,
        'rasi_matahari': RASI[int(sun_s // 30)],
        'elongasi': round(elong, 2),
        'fase_bulan': ac.moon_phase_name(elong),
        'ayanamsa': round(ay, 3),
        'teks': f"Saka {saka}, {BULAN_SAKA[bulan_no - 1]}, {paksa_pendek}-paksa, "
                f"tithi {tithi_paksa} ({tithi_name(tithi_n)}), nakshatra {NAKSHATRA[nak]}",
    }


# ---------------------------------------------------------------------------
# API gabungan
# ---------------------------------------------------------------------------
def gregorian_info(jdn: int) -> dict:
    y, m, d, cal = ac.from_jdn(jdn)
    hari = HARI[ac.weekday_index(jdn)]
    return {
        'tahun': y, 'bulan': m, 'tanggal': d, 'kalender': cal, 'hari': hari,
        'teks': f"{hari}, {d} {BULAN_MASEHI[m - 1]} {y}" + ('' if cal == 'Gregorian' else ' (Julian)'),
    }


def hijri_info(jdn: int) -> dict:
    y, m, d = jdn_to_hijri(jdn)
    return {
        'tahun': y, 'bulan': m, 'tanggal': d, 'nama_bulan': BULAN_HIJRIAH[m - 1],
        'tahun_kabisat': is_hijri_leap(y),
        'teks': f"{d} {BULAN_HIJRIAH[m - 1]} {y} H",
    }


def describe(jdn: int, utc_offset: float = 7.0) -> dict:
    """Semua unsur kalender untuk satu hari."""
    result = {
        'jdn': jdn,
        'gregorian': gregorian_info(jdn),
        'hijriah': hijri_info(jdn),
        'jawa': javanese_info(jdn),
    }
    if 1 <= result['gregorian']['tahun'] <= 3000:
        result['jyotisa'] = jyotisa_info(jdn, utc_offset)
    return result


def _validate_gregorian(y: int, m: int, d: int):
    if not 1 <= m <= 12 or not 1 <= d <= 31:
        raise ValueError('Tanggal Masehi tidak valid.')
    if ac.from_jdn(ac.to_jdn(y, m, d))[:3] != (y, m, d):
        raise ValueError('Tanggal Masehi tidak valid (hari tidak ada di bulan tersebut atau di celah 1582).')


def convert_date(source_calendar: str, date_data: dict, target_calendar: str = 'all') -> dict:
    """source_calendar: gregorian | hijri | jawa ; date_data: {'year','month','day'}"""
    y, m, d = int(date_data['year']), int(date_data['month']), int(date_data['day'])
    src = source_calendar.lower()
    if src in ('gregorian', 'masehi'):
        _validate_gregorian(y, m, d)
        jdn = ac.to_jdn(y, m, d)
    elif src in ('hijri', 'hijriah'):
        if not 1 <= m <= 12 or not 1 <= d <= hijri_month_length(y, m):
            raise ValueError('Tanggal Hijriah tidak valid.')
        jdn = hijri_to_jdn(y, m, d)
    elif src in ('jawa', 'jawa_mataraman'):
        from app.persis import kalender as pk
        if not 1 <= m <= 12 or not 1 <= d <= 30:
            raise ValueError('Tanggal Jawa tidak valid.')
        jdn = int(pk.jawa_ke_jd(d, m, y) + 0.5)
        if pk.jd_ke_jawa(jdn - 0.5)['tanggal'] != d:
            raise ValueError('Tanggal Jawa tidak valid (bulan itu hanya 29 hari pada tahun tersebut).')
    else:
        raise ValueError(f"Sistem kalender '{source_calendar}' tidak dikenal.")
    out = describe(jdn)
    out['source'] = src
    out['target'] = target_calendar
    return out


def month_table(year: int, month: int) -> list:
    """Tabel satu bulan Masehi dengan padanan Hijriah, pasaran, wuku, dan tithi."""
    if not 1 <= month <= 12:
        raise ValueError('Bulan tidak valid.')
    first = ac.to_jdn(year, month, 1)
    nxt = ac.to_jdn(year + (month == 12), 1 if month == 12 else month + 1, 1)
    rows = []
    for jdn in range(first, nxt):
        h, j, t = hijri_info(jdn), javanese_info(jdn), jyotisa_info(jdn)
        rows.append({
            'tanggal': ac.from_jdn(jdn)[2],
            'hari': j['hari'],
            'pasaran': j['pasaran'],
            'wuku': j['wuku'],
            'hijriah': f"{h['tanggal']} {h['nama_bulan']}",
            'jawa': f"{j['tanggal']} {j['bulan']} {j['tahun']}",
            'tithi': f"{t['paksa_pendek']} {t['tithi_paksa']}",
            'fase': t['fase_bulan'],
        })
    return rows


# ---------------------------------------------------------------------------
# Pencari tanggal prasasti
# ---------------------------------------------------------------------------
def find_saka_date(saka_year: int, bulan: int, paksa: str, tithi: int,
                   hari: str = None, pasaran: str = None) -> list:
    """
    Kandidat tanggal dari unsur penanggalan Jawa Kuno.
    bulan: 1..12 (Caitra=1); paksa: 'sukla'|'krsna'; tithi: 1..15; hari/pasaran opsional.
    """
    paksa = paksa.lower()
    if paksa not in ('sukla', 'krsna') or not 1 <= tithi <= 15 or not 1 <= bulan <= 12:
        raise ValueError('Input unsur Saka tidak valid.')
    if hari and hari not in HARI:
        raise ValueError('Nama hari tidak dikenal.')
    if pasaran and pasaran not in PASARAN:
        raise ValueError('Nama pasaran tidak dikenal.')
    # Tahun Saka S berlangsung kira-kira Maret/April (S+78) s.d. Maret/April (S+79)
    start = ac.to_jdn(saka_year + 78, 1, 1)
    end = ac.to_jdn(saka_year + 79, 12, 31)
    cands = []
    for jdn in range(start, end):
        j = jyotisa_info(jdn)
        if (j['tahun_saka'] == saka_year and j['bulan_saka_no'] == bulan
                and j['paksa_pendek'].lower() == paksa and j['tithi_paksa'] == tithi):
            wd = HARI[ac.weekday_index(jdn)]
            pas = PASARAN[pasaran_index(jdn)]
            cands.append({
                'jdn': jdn,
                'tanggal': gregorian_info(jdn)['teks'],
                'hari': wd,
                'pasaran': pas,
                'wuku': WUKU[pawukon_day(jdn) // 7],
                'cocok_wara': (hari in (None, '', wd)) and (pasaran in (None, '', pas)),
            })
    cands.sort(key=lambda c: (not c['cocok_wara'], c['jdn']))
    return cands


# ---------------------------------------------------------------------------
# Materi edukasi sistem kalender (ditampilkan di UI)
# ---------------------------------------------------------------------------
CALENDAR_INFO = [
    {
        'id': 'hijriah', 'nama': 'Hijriah Aritmetis (Hisab Urfi)',
        'sejarah': "Kalender Hijriah dimulai dari 1 Muharram 1 H (16 Juli 622 M, Julian), tahun hijrah Nabi "
                   "Muhammad ke Madinah, dan ditetapkan sebagai sistem tahun pada masa Khalifah Umar bin Khattab. "
                   "Versi aritmetis memakai aturan tetap, bukan pengamatan hilal.",
        'prinsip': "Siklus 30 tahun berisi 11 tahun kabisat (tahun ke-2, 5, 7, 10, 13, 16, 18, 21, 24, 26, 29). "
                   "Bulan ganjil 30 hari, bulan genap 29 hari, Zulhijah 30 hari pada tahun kabisat. "
                   "Satu tahun = 354 atau 355 hari.",
        'catatan': "Hasil dapat berbeda 1-2 hari dari kalender resmi yang berbasis hisab hakiki/rukyat.",
    },
    {
        'id': 'jawa', 'nama': 'Jawa Mataraman (Sultan Agungan)',
        'sejarah': "Pada 1633 M (1043 H) Sultan Agung dari Mataram menyelaraskan tahun Jawa dengan peredaran "
                   "Bulan seperti Hijriah, tetapi meneruskan hitungan tahun Saka sehingga 1 Sura 1555 sama dengan "
                   "1 Muharram 1043 H.",
        'prinsip': "Tahun Jawa = tahun Hijriah + 512. Delapan tahun membentuk satu windu (Alip, Ehé, Jimawal, Jé, "
                   "Dal, Bé, Wawu, Jimakir). Pancawara/pasaran (5 hari) dan pawukon (210 hari = 30 wuku x 7 hari) "
                   "berjalan terus tanpa terikat bulan.",
        'catatan': "Weton = hari + pasaran. Neptu = jumlah nilai hari dan pasaran, dipakai dalam primbon.",
    },
    {
        'id': 'saka', 'nama': 'Saka & Jyotisa (Jawa Kuno)',
        'sejarah': "Era Saka dimulai 78 M. Prasasti Jawa Kuno umumnya ditanggali dalam tahun Saka lengkap dengan "
                   "bulan, tithi, paksa, dan wara (hari pasaran). Unsur-unsur itu menjadi dasar kajian epigrafi "
                   "untuk menentukan kronologi kerajaan.",
        'prinsip': "Kalender lunisolar: tithi = 1/30 siklus fase Bulan (tiap 12 derajat elongasi), 15 tithi "
                   "sukla-paksa (Bulan membesar) dan 15 tithi krsna-paksa (Bulan mengecil). Nakshatra = 27 rumah "
                   "Bulan sepanjang ekliptika sidereal; yoga dan karana diturunkan dari bujur Matahari dan Bulan.",
        'catatan': "Prasasti sering menyebut wuku, pancawara, dan sadwara sekaligus sehingga satu tanggal dapat "
                   "dicocokkan silang. Mesin ini memakai efemeris modern, bukan Surya Siddhanta.",
    },
]
