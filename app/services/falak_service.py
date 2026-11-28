"""Layanan falak untuk antarmuka web: jadwal salat, kiblat, rasydulqiblat, dan konversi kalender.
Semua perhitungan dilakukan oleh app/persis (port persis-times-js); modul ini hanya memeriksa masukan dan
memformat hasil menjadi struktur JSON-siap-pakai."""
from __future__ import annotations

from datetime import date, timedelta

from app.persis import core, hisab, kalender, kiblat, salat
from app.services import astro_core as ac
from app.services import calendar_service as cs
from app.services import ejaan_jyotisa as EJ
from app.services.timezones import tz_from_lon, tz_label

NAMA_WAKTU = (('imsak', 'Imsak'), ('subuh', 'Subuh'), ('syuruk', 'Syuruk (terbit)'), ('duha', 'Duha'), ('zuhur', 'Zuhur'),
              ('asar', 'Asar'), ('magrib', 'Magrib'), ('isya', 'Isya'), ('nisfuLail', 'Tengah malam (nisfu lail)'))
NAMA_ASTRO = (('fajarAstro', 'Fajar astronomis (−18°)'), ('fajarNaut', 'Fajar nautis (−12°)'), ('fajarSipil', 'Fajar sipil (−6°)'),
              ('senjaSipil', 'Senja sipil (−6°)'), ('senjaNaut', 'Senja nautis (−12°)'), ('senjaAstro', 'Senja astronomis (−18°)'),
              ('lamaSiang', 'Lama siang'), ('lamaMalam', 'Lama malam'))


class InputError(ValueError):
    pass


# ── masukan ─────────────────────────────────────────────────────────
def _float(v, nama, lo, hi, default=None):
    if v in (None, ''):
        if default is None:
            raise InputError(f'{nama} wajib diisi.')
        return default
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise InputError(f'{nama} harus berupa angka.') from None
    if not lo <= x <= hi:
        raise InputError(f'{nama} harus di antara {lo:g} dan {hi:g}.')
    return x


def parse_lokasi(args, default: dict) -> dict:
    lat = _float(args.get('lat'), 'Lintang', -90, 90, default['lat'])
    lon = _float(args.get('lon'), 'Bujur', -180, 180, default['lon'])
    elev = _float(args.get('elev'), 'Elevasi', -400, 9000, 0.0)
    tz = _float(args.get('tz'), 'Zona waktu', -12, 14, tz_from_lon(lon))
    return {'lat': lat, 'lon': lon, 'elev': elev, 'tz': tz, 'tz_label': tz_label(tz)}


def parse_tanggal(s, default: date | None = None) -> date:
    if not s:
        if default is None:
            raise InputError('Tanggal wajib diisi.')
        return default
    try:
        return date.fromisoformat(str(s))
    except ValueError:
        raise InputError('Format tanggal harus YYYY-MM-DD.') from None


def parse_metode(key) -> salat.PrayerMethod:
    key = key or 'persatuanIslam'
    if key not in salat.METODE:
        raise InputError('Metode salat tidak dikenal.')
    return salat.METODE[key]


# ── pemformat ───────────────────────────────────────────────────────
def hms(h: float | None, detik: bool = True) -> str | None:
    if h is None:
        return None
    total = round((h % 24) * 3600) if detik else int((h % 24) * 60 + 1e-9) * 60
    total %= 86400
    jam, sisa = divmod(total, 3600)
    mnt, dtk = divmod(sisa, 60)
    return f'{jam:02d}:{mnt:02d}:{dtk:02d}' if detik else f'{jam:02d}:{mnt:02d}'


def _durasi(h):
    if h is None:
        return None
    return '24:00:00' if h >= 24 - 1e-9 else hms(h)


def dms(derajat: float) -> str:
    d = int(derajat)
    m = int((derajat - d) * 60)
    s = ((derajat - d) * 60 - m) * 60
    return f"{d}° {m:02d}′ {s:04.1f}″"


def mata_angin(az: float) -> str:
    n = ('utara', 'utara-timur laut', 'timur laut', 'timur-timur laut', 'timur', 'timur-tenggara', 'tenggara',
         'selatan-tenggara', 'selatan', 'selatan-barat daya', 'barat daya', 'barat-barat daya', 'barat',
         'barat-barat laut', 'barat laut', 'utara-barat laut')
    return n[int((az % 360 + 11.25) // 22.5) % 16]


def _nilai(v: salat.SalatValue, detik=True):
    return {'jam': hms(v.time, detik), 'status': v.status,
            'keterangan': None if v.is_normal else salat.KETERANGAN_STATUS.get(v.status, v.status)}


# ── jadwal salat ────────────────────────────────────────────────────
def jadwal_salat(d: date, lok: dict, metode: salat.PrayerMethod, ihtiyat: int = 2, imsak: int = 10) -> dict:
    if not 0 <= ihtiyat <= 10:
        raise InputError('Ihtiyat harus 0–10 menit.')
    if not 0 <= imsak <= 60:
        raise InputError('Imsak harus 0–60 menit sebelum Subuh.')
    r = salat.jadwal_lengkap(d.day, d.month, d.year, lok['lon'], lok['lat'], lok['elev'], lok['tz'], metode,
                             ihtiyat_menit=ihtiyat, imsak_menit=imsak)
    baris = [{'kunci': k, 'nama': n, 'jadwal': _nilai(r['jadwal'][k], False), 'hisab': _nilai(r['hisab'][k])}
             for k, n in NAMA_WAKTU]
    astro = []
    for k, n in NAMA_ASTRO:
        v = r['astro'][k]
        astro.append({'kunci': k, 'nama': n, 'jam': _durasi(v) if k.startswith('lama') else hms(v)})
    ist = kiblat.istiwa(d.day, d.month, d.year, lok['lon'], lok['lat'], lok['tz'])
    sm = kiblat.sepertiga_malam(d.day, d.month, d.year, lok['lon'], lok['lat'], lok['elev'], lok['tz'], metode)
    isya = (f'{metode.isya_menit} menit setelah Magrib' + (f' ({metode.isya_menit_ramadan} menit pada Ramadan)' if metode.isya_menit_ramadan else '')
            if metode.isya_interval else f'Matahari {metode.hm_isya:g}°')
    return {
        'tanggal': d.isoformat(), 'lokasi': lok, 'metode': {'kunci': metode.key, 'nama': metode.name,
                                                            'subuh': f'Matahari {metode.hm_subuh:g}°', 'isya': isya},
        'ihtiyat_menit': ihtiyat, 'imsak_menit': imsak, 'ramadan': r['ramadan'],
        'waktu': baris, 'astronomis': astro,
        'istiwa': {'jam': hms(ist['jam']), 'tafawut_menit': round(ist['tafawut'] * 60, 2), 'kwd_menit': round(ist['kwd'] * 60, 2),
                   'tinggi': round(ist['tinggi'], 2)},
        'sepertiga_malam': None if sm is None else {k: _durasi(v) if k == 'lama' else hms(v) for k, v in sm.items()},
        'catatan': 'Jadwal = menit hisab dibulatkan ke bawah + ihtiyat; kolom hisab = nilai mentah berdetik. '
                   'Bulan terbit/terbenam belum tersedia.',
    }


# ── kiblat ──────────────────────────────────────────────────────────
def info_kiblat(lok: dict) -> dict:
    lon, lat = lok['lon'], lok['lat']
    bola, elp, vin = kiblat.arah_bola(lon, lat), kiblat.arah_elipsoid(lon, lat), kiblat.vincenty(lon, lat, 'PtoQ')
    return {'lokasi': lok, 'bola': {'derajat': round(bola, 4), 'dms': dms(bola)}, 'elipsoid': {'derajat': round(elp, 4), 'dms': dms(elp)},
            'vincenty': {'derajat': round(vin, 4), 'dms': dms(vin)}, 'mata_angin': mata_angin(vin),
            'jarak_km': round(kiblat.vincenty(lon, lat, 'Dist') / 1000, 1),
            'kabah': {'lat': kiblat.LAT_KABAH, 'lon': kiblat.LON_KABAH}}


# ── rasydulqiblat ───────────────────────────────────────────────────
def _fmt_jd(jd: float, tz: float) -> dict:
    k = core.jdkm(jd, tz)
    mk = core.jdkm(jd, 3.0)
    return {'tanggal': f"{k['tgl']:02d}-{k['bln']:02d}-{k['thn']}", 'hari': k['hari'], 'jam': hms(k['jam_des']),
            'jam_makkah': hms(mk['jam_des']), 'jd': round(jd, 6)}


def rasydulqiblat(d: date, lok: dict, metode_arah: str = 'vincenty', hari: int = 7, tahun: int | None = None, jumlah_tahun: int = 1) -> dict:
    if metode_arah not in ('bola', 'elipsoid', 'vincenty'):
        raise InputError('Metode arah kiblat tidak dikenal.')
    if not 1 <= hari <= 31:
        raise InputError('Jumlah hari harus 1–31.')
    if not 1 <= jumlah_tahun <= 10:
        raise InputError('Jumlah tahun harus 1–10.')
    tz, lat, lon = lok['tz'], lok['lat'], lok['lon']
    q = kiblat.arah_kiblat(lon, lat, metode_arah)
    harian = []
    for i in range(hari):
        t = d + timedelta(days=i)
        ev = kiblat.rasydulqiblat_harian(t.day, t.month, t.year, lat, lon, tz, q)
        harian.append({'tanggal': t.isoformat(), 'hari': core.jdkm(core.kmjd(t.day, t.month, t.year, 12, 0), 0)['hari'],
                       'bayangan_ke_kiblat': [_ev(e) for e in ev if e['jenis'] == 1],
                       'matahari_di_kiblat': [_ev(e) for e in ev if e['jenis'] == 0]})
    y0 = tahun or d.year
    tahunan = []
    for y in range(y0, y0 + jumlah_tahun):
        tahunan.append({'tahun': y,
                        'rasydul1': _tahunan(kiblat.rasydulqiblat(y, tz, 1), lok), 'rasydul2': _tahunan(kiblat.rasydulqiblat(y, tz, 2), lok),
                        'antipoda1': _tahunan(kiblat.antipoda_kabah(y, tz, 1), lok), 'antipoda2': _tahunan(kiblat.antipoda_kabah(y, tz, 2), lok)})
    return {'lokasi': lok, 'arah_kiblat': {'derajat': round(q, 4), 'dms': dms(q), 'metode': metode_arah},
            'azimut_bayangan': round((q + 180) % 360, 4), 'harian': harian, 'tahunan': tahunan,
            'catatan': 'Harian: tegakkan tongkat pada jam tertera; bayangan menuju kiblat (kolom 1) atau Matahari berada di arah kiblat (kolom 2). '
                       'Tahunan: Matahari tepat di atas Ka\'bah (rasydul) atau di bawahnya (antipoda). Tinggi tanpa refraksi.'}


def _ev(e):
    return {'jam': hms(e['jam']), 'tinggi': round(e['tinggi'], 1), 'azimut': round(e['azimut'], 2), 'dekat_zenit': e['tinggi'] > 85}


def _tahunan(e, lok):
    a = kiblat.tinggi_azimut_matahari(e['jd'], lok['lat'], lok['lon'])
    return {**_fmt_jd(e['jd'], lok['tz']), 'deklinasi': round(e['deklinasi'], 4),
            'matahari_di_lokasi': {'tinggi': round(a['tinggi'], 1), 'terlihat': a['tinggi'] > 0}}


# ── konversi kalender ───────────────────────────────────────────────
# ── padanan ringkas + rincian (Lab Kalender) ────────────────────────
WINDU_NAMA = ('Kuntara', 'Sengara', 'Sancaya', 'Adi')       # urutan windu ke-n mod 4 (terjangkar: tahun Jawa 1960 = windu Sancaya)
_SING_HARI = {'Senin': 'nen', 'Selasa': 'sa', 'Rabu': 'bo', 'Kamis': 'mis', 'Jumat': 'jem', 'Sabtu': 'tu', 'Minggu': 'ha'}
_SING_PASARAN = {'Legi': 'gi', 'Pahing': 'hing', 'Pon': 'pon', 'Wage': 'ge', 'Kliwon': 'won'}


def _kapital(nama: str) -> str:
    """Huruf pertama kapital (sebagian nama di daftar sumber JS ditulis huruf kecil)."""
    return nama[:1].upper() + nama[1:]


def tanggal_julian(cjdn: int) -> tuple:
    """CJDN → (tahun, bulan, hari) kalender Julian (proleptik, juga untuk tanggal modern)."""
    c = cjdn + 1524
    d = int((c - 122.1) // 365.25)
    e = int(365.25 * d)
    g = int((c - e) // 30.6001)
    hari = c - e - int(30.6001 * g)
    bulan = g - 1 if g < 14 else g - 13
    return (d - 4716 if bulan > 2 else d - 4715), bulan, hari


def kurup_jawa(tahun_jawa: int) -> dict:
    """Kurup (siklus 120 tahun) = singkatan hari-pasaran 1 Sura tahun Alip pertamanya: 1867 → Asapon, 1747 → Aboge."""
    awal = tahun_jawa - ((tahun_jawa - 427) % 120)
    cj = int(kalender.jawa_ke_jd(1, 1, awal) + 0.5)
    hari, pas = cs.HARI[ac.weekday_index(cj)], cs.PASARAN[cs.pasaran_index(cj)]
    return {'nama': 'A' + _SING_HARI[hari] + _SING_PASARAN[pas], 'awal': awal, 'dasar': f'1 Sura {awal} jatuh pada {hari} {pas}'}


def padanan(cjdn: int, out: dict, epoch: int, kabisat: int) -> dict:
    """Struktur siap-tampil untuk empat baris Padanan: AD, AH, AJ, AS (masing-masing ringkas + rincian)."""
    y, m, d, cal = ac.from_jdn(cjdn)
    bm = cs.BULAN_MASEHI
    gy, gm, gd, _ = ac.from_jdn(cjdn, True)
    jy_, jm_, jd_ = tanggal_julian(cjdn)
    def mas(yy, mm, dd): return f"{dd} {bm[mm - 1]} {yy}"
    ad = {'ringkas': mas(y, m, d) + ' AD' + ('' if cal == 'Gregorian' else ' (Julian)'),
          'rincian': [{'nama': 'Kalender Gregorian', 'teks': mas(gy, gm, gd) + (' (proleptik)' if cal != 'Gregorian' else '')},
                      {'nama': 'Kalender Julian', 'teks': mas(jy_, jm_, jd_)}]}
    arit = []
    for kab in (1, 2, 3, 4):
        h = kalender.cjdn_ke_hijri(cjdn, epoch, kab)
        arit.append({'kunci': f'aritmetis-{kab}', 'nama': f'Aritmetis tipe {"I" * kab if kab < 4 else "IV"}', 'teks': f"{h['tgl']} {h['nama_bulan']} {h['thn']} AH",
                     'aktif': kab == kabisat})
    ah = {'aritmetis': arit,
          'kriteria': [{'kunci': k['kunci'], 'nama': k['nama'], 'teks': (k['teks'][:-2] + ' AH') if k['teks'] else None} for k in out['hijriah_kriteria']]}
    w = out['jawa']
    ku = kurup_jawa(w['tahun'])
    windu = WINDU_NAMA[((w['tahun'] - cs.JAWA_ALIP_BASE) // 8) % 4]
    aj = {'ringkas': f"{w['tanggal']} {w['bulan']} {w['tahun']} AJ",
          'rincian': [{'nama': 'Nama tahun', 'teks': w['tahun_windu']}, {'nama': 'Nama windu', 'teks': windu}, {'nama': 'Kurup', 'teks': ku['nama']}]}
    jy = out.get('jyotisa')
    if jy:
        # Ejaan unsur jyotisa mengikuti JS (ejaan_jyotisa); š/k = singkatan śuklapakṣa/kṛṣṇapakṣa
        paksa = EJ.PAKSA[0 if jy['tithi_no'] <= 15 else 1]
        masa = EJ.MASA[jy['bulan_saka_no'] - 1]
        a_s = {'ringkas': f"{jy['tithi_paksa']}{paksa[0].lower()} {masa} {jy['tahun_saka']} AS",
               'rincian': [{'nama': 'Tithi', 'teks': f"{_kapital(EJ.TITHI[(jy['tithi_no'] - 1) % 15])} (ke-{jy['tithi_paksa']})"},
                           {'nama': 'Paksa', 'teks': paksa},
                           {'nama': 'Masa (bulan Saka)', 'teks': masa},
                           {'nama': 'Nakshatra', 'teks': f"{_kapital(EJ.NAKSATRA[jy['nakshatra_no'] - 1])} (ke-{jy['nakshatra_no']})"},
                           {'nama': 'Yoga', 'teks': f"{_kapital(EJ.YOGA[jy['yoga_no'] - 1])} (ke-{jy['yoga_no']})"},
                           {'nama': 'Karana', 'teks': _kapital(EJ.nama_karana(jy['karana_no']))},
                           {'nama': 'Rasi Matahari', 'teks': _kapital(EJ.RASI[jy['rasi_no'] - 1])}]}
    else:
        a_s = None
    return {'ad': ad, 'ah': ah, 'aj': aj, 'as': a_s}


def konversi(sumber: str, tahun: int, bulan: int, hari: int, epoch: int = 2, kabisat: int = 2) -> dict:
    """sumber: masehi | hijriah | jawa. Hasil: padanan di semua sistem (hari dihitung sebagai tanggal sipil)."""
    s = (sumber or '').lower()
    if s in ('masehi', 'gregorian'):
        if not 1 <= bulan <= 12 or not 1 <= hari <= 31 or ac.from_jdn(ac.to_jdn(tahun, bulan, hari))[:3] != (tahun, bulan, hari):
            raise InputError('Tanggal Masehi tidak valid (hari tidak ada di bulan itu atau jatuh di celah 1582).')
        cjdn = ac.to_jdn(tahun, bulan, hari)
    elif s in ('hijriah', 'hijri'):
        if not 1 <= bulan <= 12 or not 1 <= hari <= 30:
            raise InputError('Tanggal Hijriah tidak valid.')
        cjdn = kalender.hijri_ke_cjdn(hari, bulan, tahun, epoch, kabisat)
        if kalender.cjdn_ke_hijri(cjdn, epoch, kabisat)['tgl'] != hari:
            raise InputError('Tanggal Hijriah tidak valid (bulan itu hanya 29 hari pada tahun tersebut).')
    elif s == 'jawa':
        if not 1 <= bulan <= 12 or not 1 <= hari <= 30:
            raise InputError('Tanggal Jawa tidak valid.')
        cjdn = int(kalender.jawa_ke_jd(hari, bulan, tahun) + 0.5)
        if kalender.jd_ke_jawa(cjdn - 0.5)['tanggal'] != hari:
            raise InputError('Tanggal Jawa tidak valid (bulan itu hanya 29 hari pada tahun tersebut).')
    else:
        raise InputError("Sistem kalender harus 'masehi', 'hijriah', atau 'jawa'.")
    if not 1 <= ac.from_jdn(cjdn)[0] <= 3000:
        raise InputError('Rentang tahun yang didukung: 1–3000 M.')
    out = cs.describe(cjdn)                                    # masehi, Jawa (Hijriah+512), pawukon, Jyotisa
    h = kalender.cjdn_ke_hijri(cjdn, epoch, kabisat)
    out['hijriah'] = {'tahun': h['thn'], 'bulan': h['bln'], 'tanggal': h['tgl'], 'nama_bulan': h['nama_bulan'],
                      'hari': h['hari'], 'pasaran': h['pasaran'], 'teks': f"{h['tgl']} {h['nama_bulan']} {h['thn']} H"}
    out['hijriah_kriteria'] = []
    for kunci, nama in zip(hisab.KRITERIA, hisab.NAMA_KRITERIA):
        h2 = hisab.hijri_kriteria(cjdn, kunci)
        out['hijriah_kriteria'].append({'kunci': kunci, 'nama': nama,
                                        'teks': f"{h2['tgl']} {h2['nama_bulan']} {h2['thn']} H" if h2 else None})
    out['jd'] = cjdn - 0.5
    out['padanan'] = padanan(cjdn, out, epoch, kabisat)
    out['catatan'] = ('Hijriah aritmetis = hisab urfi. MABIMS, Ummul Qura, Wujudul Hilal, dan KHGT dihitung dari ijtimak, tinggi/elongasi hilal, '
                      'dan Bulan terbenam menurut kriteria & lokasi acuan masing-masing; hasilnya dapat berbeda 1–2 hari dari penetapan resmi. '
                      'Tanggal Jawa memakai siklus kurup (Sultan Agungan).')
    return out


# ── perbandingan kalender Hijriah & Jawa ────────────────────────────
HARI_SEKUEN = ('Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu')       # indeks = CJDN mod 7


def hukum_puasa(d: int, m: int, hari: int, panjang_bulan: int | None, sk: bool, ab: bool) -> dict:
    """Hukum puasa pada satu hari (tab_hilal.js: hukumPuasa). hari: CJDN mod 7 (0 Senin … 4 Jumat).
    Hasil: {k: wajib|sunah|makruh|haram|'', t: keterangan, n: jumlah sebab sunah}."""
    haram = []
    if m == 10 and d == 1: haram.append('Idulfitri')
    if m == 12 and d == 10: haram.append('Iduladha')
    if m == 12 and 11 <= d <= 13: haram.append('Hari Tasyrik')
    if haram:
        return {'k': 'haram', 't': 'Haram: ' + ', '.join(haram), 'n': 0}
    if m == 9:
        return {'k': 'wajib', 't': 'Puasa wajib Ramadan', 'n': 0}
    if m == 8 and panjang_bulan and d >= 16:
        return {'k': 'makruh', 'n': 0, 't': 'Makruh: Hari Syak (akhir Syakban)' if d == panjang_bulan else 'Makruh: puasa setelah pertengahan Syakban'}
    sunah = []
    if sk:
        if hari == 0: sunah.append('Senin')
        if hari == 3: sunah.append('Kamis')
    if ab and 13 <= d <= 15: sunah.append('Ayyamulbid')
    if m == 1 and d == 9: sunah.append('Tasua')
    if m == 1 and d == 10: sunah.append('Asyura')
    if m == 10 and 2 <= d <= 7: sunah.append('Syawal')
    if m == 12 and 1 <= d <= 7: sunah.append('Awal Zulhijah')
    if m == 12 and d == 8: sunah.append('Tarwiah')
    if m == 12 and d == 9: sunah.append('Arafah')
    if sunah:
        return {'k': 'sunah', 'n': len(sunah), 't': 'Sunah' + (f' ({len(sunah)} sebab)' if len(sunah) > 1 else '') + ': ' + ', '.join(sunah)}
    if hari == 4:
        return {'k': 'makruh', 't': 'Makruh: Jumat', 'n': 0}
    return {'k': '', 't': '', 'n': 0}


def perbandingan_kalender(d: date, sk: bool = True, ab: bool = True) -> dict:
    """Tabel perbandingan: kolom = tanggal Masehi (satu bulan Hijriah penuh di sekitar d), baris = MABIMS, Ummul Qura, Wujudul Hilal,
    KHGT, Aritmetis I–IV, Mataraman; tiap sel memuat tanggal/bulan/tahun dan hukum puasa (kecuali baris Mataraman)."""
    if not 1700 <= d.year <= 2300:
        raise InputError('Perbandingan hisab tersedia untuk tahun 1700–2300 M.')
    c0 = ac.to_jdn(d.year, d.month, d.day)
    t = hisab.banding(c0)
    kolom = []
    for c in range(t['cjdn_awal'], t['cjdn_akhir'] + 1):
        y, m, dd, _ = ac.from_jdn(c)
        kolom.append({'cjdn': c, 'tgl': dd, 'bln': m, 'thn': y, 'hari': HARI_SEKUEN[c % 7], 'hari_no': c % 7})
    baris = []
    for r in t['baris']:
        sel = []
        for c, x in zip(range(t['cjdn_awal'], t['cjdn_akhir'] + 1), r['sel']):
            if x is None:
                sel.append(None)
                continue
            nama_bln = (hisab.BULAN_JAWA if r['jawa'] else kalender.BULAN_H)[x['m'] - 1]
            e = {'d': x['d'], 'm': x['m'], 'y': x['y'], 'bulan': nama_bln,
                 'puasa': hukum_puasa(x['d'], x['m'], c % 7, x['panjang_bulan'], sk, ab)}
            sel.append(e)
        baris.append({'nama': r['nama'], 'jawa': r['jawa'], 'sel': sel})
    return {'tanggal': d.isoformat(), 'bulan_acuan': {'no': t['bulan_acuan'], 'nama': kalender.BULAN_H[t['bulan_acuan'] - 1]},
            'kolom': kolom, 'baris': baris, 'awal': t['cjdn_awal'], 'akhir': t['cjdn_akhir'],
            'catatan': 'Hisab (MABIMS, Ummul Qura, Wujudul Hilal, KHGT) memakai kriteria & lokasi bawaan tiap kalender, bukan lokasi di formulir. '
                       'Aritmetis I–IV = pola kabisat 1–4 (epoch Jumat). Mataraman memakai nomor bulan Jawa (Sura = Muharam) dan diwarnai dengan aturan puasa yang sama. '
                       'Prioritas: haram > wajib > makruh Syakban > sunah > Jumat (makruh bila tidak bertepatan puasa sunah).'}


def nama_kriteria(kunci: str) -> str:
    """Nama tampilan kriteria Hijriah (kunci: aritmetis | mabims | ummulqura | wujudulhilal | turki)."""
    if kunci == 'aritmetis':
        return 'Aritmetis (urfi)'
    return dict(zip(hisab.KRITERIA, hisab.NAMA_KRITERIA))[kunci]
