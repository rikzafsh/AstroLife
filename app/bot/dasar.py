"""Dasar AstroBot: konstanta bahasa, pembacaan konteks klien, pengambilan entitas dari teks (tanggal Masehi/Hijriah, istilah hari relatif,
lokasi, kriteria) dan bentuk balasan standar. Dipakai oleh semua modul intent."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from app.persis import hisab, salat
from app.services import astro_core as ac
from app.services.timezones import tz_from_lon, tz_label

from .kota import cari_lokasi

BULAN_ID = {'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8, 'september': 9,
            'oktober': 10, 'november': 11, 'desember': 12, 'agu': 8, 'agt': 8, 'ags': 8, 'sept': 9, 'okt': 10, 'nov': 11, 'des': 12, 'jan': 1,
            'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'nop': 11}


BULAN_ID_NAMA = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']


# nama bulan Hijriah (KBBI) → nomor; kunci memakai teks.bersih tanpa spasi
HIJRI = {'muharam': 1, 'safar': 2, 'rabiulawal': 3, 'rabiulakhir': 4, 'rabiulakir': 4, 'jumadilawal': 5, 'jumadilakhir': 6, 'jumadilakir': 6,
         'rajab': 7, 'syakban': 8, 'ramadan': 9, 'syawal': 10, 'zulkaidah': 11, 'zulhijah': 12}


HIJRI_NAMA = ['', 'Muharam', 'Safar', 'Rabiulawal', 'Rabiulakhir', 'Jumadilawal', 'Jumadilakhir', 'Rajab', 'Syakban', 'Ramadan', 'Syawal', 'Zulkaidah', 'Zulhijah']


HARI_ID = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']


KRIT_NAMA = {'aritmetis': 'Aritmetis', 'mabims': 'MABIMS', 'ummulqura': 'Ummul Qura', 'wujudulhilal': 'Wujudul Hilal', 'turki': 'KHGT'}


KRIT_KATA = {'aritmetis': 'aritmetis', 'urfi': 'aritmetis', 'mabims': 'mabims', 'ummul': 'ummulqura', 'wujudul': 'wujudulhilal',
             'khgt': 'turki', 'turki': 'turki'}


WAKTU_SALAT = {'imsak': 'imsak', 'subuh': 'subuh', 'terbit': 'syuruk', 'duha': 'duha', 'zuhur': 'zuhur', 'asar': 'asar',
               'magrib': 'magrib', 'isya': 'isya'}


AWAL_KONSEP = re.compile(r'\b(apa itu|apa yang dimaksud|apa maksud|apa arti|artinya|pengertian|definisi|jelaskan|jelasin|mengapa|kenapa|'
                         r'bedanya|perbedaan|beda antara|bagaimana cara kerja|bagaimana cara menghitung|cara menghitung|rumus|dasar|'
                         r'apa bedanya|maksud dari|apa saja|apa fungsi)\b')


def baca_konteks(context: dict | None) -> dict:
    c = context or {}
    lok = (c.get('lokasi') or {})
    try:
        lat, lon = float(lok.get('lat')), float(lok.get('lon'))
        tz = float(lok['tz']) if lok.get('tz') not in (None, '') else tz_from_lon(lon)
        elev = float(lok.get('elev') or 0)
        nama = str(lok.get('nama') or 'lokasi Anda')[:60]
    except (TypeError, ValueError):
        lat, lon, tz, elev, nama = -7.7956, 110.3695, 7.0, 0.0, 'Yogyakarta'
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        lat, lon, tz, elev, nama = -7.7956, 110.3695, 7.0, 0.0, 'Yogyakarta'
    s = c.get('salat') or {}
    metode = s.get('metode') if s.get('metode') in salat.METODE else 'persatuanIslam'
    def _int(v, d, lo, hi):
        try:
            return max(lo, min(hi, int(v)))
        except (TypeError, ValueError):
            return d
    krit = (c.get('hijriah') or {}).get('kriteria')
    krit = krit if krit in KRIT_NAMA else 'aritmetis'
    return {'lok': {'lat': lat, 'lon': lon, 'elev': elev, 'tz': tz, 'tz_label': tz_label(tz)}, 'nama': nama, 'metode': metode,
            'ihtiyat': _int(s.get('ihtiyat'), 2, 0, 10), 'imsak': _int(s.get('imsak'), 10, 0, 60), 'krit': krit}


def _sekarang(ctx) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=ctx['lok']['tz'])


# istilah hari relatif terhadap hari ini (H): (pola, selisih hari, nama baku, keterangan H)
REL = [(r'\bbesok lusa\b', 2, 'besok lusa'), (r'\bkemarin lusa\b', -2, 'kemarin lusa'), (r'\bkemarin dulu\b', -2, 'kemarin dulu'),
       (r'\bselumbari\b', -2, 'selumbari'), (r'\bbasarai\b', -2, 'basarai'), (r'\bkila mulai\b|\bkila\b', -3, 'kila mulai'),
       (r'\bsenantu\b', -4, 'senantu'), (r'\bhari h\b', 0, 'hari-H'),
       (r'\bkemarin\b', -1, 'kemarin'), (r'\bbesok\b|\besok\b', 1, 'besok'), (r'\blusa\b', 2, 'lusa'),
       (r'\btulat\b', 3, 'tulat'), (r'\blangkat\b', 3, 'langkat'), (r'\btubin\b', 4, 'tubin'), (r'\btungging\b', 4, 'tungging'),
       (r'\bcekelong\b', 5, 'cekelong'), (r'\bembute\b', 6, 'embute')]


REL_KET = {'senantu': 'H-4 dan sebelumnya', 'embute': 'H+6 dan seterusnya'}


def tanggal_relatif(t: str, hari_ini: date):
    """Kembalikan (tanggal, nama istilah). Mendukung besok/lusa/kemarin dan istilah Jawa/Melayu: kila mulai (H-3), selumbari/basarai (H-2),
    tulat/langkat (H+3), tubin/tungging (H+4), cekelong (H+5), embute (H+6 dst.), senantu (H-4 dst.)."""
    if re.search(r'\b(hari ini|sekarang|nanti|malam ini|pagi ini|siang ini|sore ini)\b', t):
        return hari_ini, 'hari ini'
    for pola, off, nama in REL:
        if re.search(pola, t):
            return hari_ini + timedelta(days=off), nama
    m = re.search(r'\b(\d{1,3}) hari (lagi|lalu|yang lalu|ke depan)\b', t)
    if m:
        n = int(m.group(1)) * (-1 if m.group(2) in ('lalu', 'yang lalu') else 1)
        return hari_ini + timedelta(days=n), None
    return None, None


def awalan_relatif(label, d, hari_ini):
    if label in (None, 'hari ini'):
        return ''
    n = (d - hari_ini).days
    if label in REL_KET:                                     # istilah terbuka: tampilkan tanggal terdekat
        return f"**{label.capitalize()}** = {REL_KET[label]}; ini tanggal terdekatnya (H{n:+d}). "
    ket = f'H{n:+d}' if n else 'H'
    return f"**{label.capitalize()}** = {ket} ({'+' if n > 0 else ''}{n} hari dari hari ini). "


def tanggal_masehi(t: str):
    m = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    nama = '|'.join(sorted(BULAN_ID, key=lambda x: -len(x)))
    m = re.search(rf'\b(\d{{1,2}})\s+({nama})\.?\s*(\d{{4}})?\b', t)
    if m:
        return int(m.group(1)), BULAN_ID[m.group(2)], int(m.group(3)) if m.group(3) else None
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', t)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def hijri_dalam(t: str):
    """Cari 'nama bulan Hijriah' (+ tanggal, tahun). t sudah bersih (aksen/ejaan baku, spasi dirapatkan untuk nama majemuk)."""
    tt = re.sub(r'\b(rabiul|jumadil)\s+(awal|akhir|akir)\b', lambda m: m.group(1) + m.group(2), t)
    tt = re.sub(r'\bzul\s+(kaidah|hijah)\b', lambda m: 'zul' + m.group(1), tt)
    for kata in re.findall(r"[a-z']+", tt):
        k = kata
        if k in HIJRI:
            bulan = HIJRI[k]
            m = re.search(rf'(\d{{1,2}})\s+{k}\b', tt)
            tgl = int(m.group(1)) if m else None
            m2 = re.search(rf'{k}\s+(\d{{4}})\b', tt)
            thn = int(m2.group(1)) if m2 else None
            return bulan, tgl, thn
    return None


def kriteria_dalam(t: str):
    for kata, kunci in KRIT_KATA.items():
        if re.search(rf'\b{kata}\b', t):
            return kunci
    return None


def jdn_dari(d: date) -> int:
    return ac.to_jdn(d.year, d.month, d.day)


def cari_masehi(tgl: int, bln: int, thn: int, krit: str) -> date | None:
    """Tanggal Masehi untuk tanggal Hijriah menurut kriteria (pindai ±4 hari dari perkiraan aritmetis)."""
    from app.persis import kalender
    perk = kalender.hijri_ke_cjdn(tgl, bln, thn, 2, 2)
    if krit == 'aritmetis':
        y, m, dd = ac.from_jdn(perk)[:3]
        return date(y, m, dd)
    for off in (0, -1, 1, -2, 2, -3, 3, -4, 4):
        try:
            h = hisab.hijri_kriteria(perk + off, krit)
        except Exception:
            return None
        if h and (h['thn'], h['bln'], h['tgl']) == (thn, bln, tgl):
            y, m, dd = ac.from_jdn(perk + off)[:3]
            return date(y, m, dd)
    return None


def format_tanggal(d: date) -> str:
    return f"{HARI_ID[d.weekday()]}, {d.day} {BULAN_ID_NAMA[d.month]} {d.year}"


def balas(reply, intent, slots=None, cards=None, links=None, sources=None, suggestions=None, status='success'):
    return {'status': status, 'reply': reply, 'intent': intent, 'slots': slots or {}, 'cards': cards or [], 'links': links or [],
            'sources': sources or [], 'suggestions': suggestions or [], 'dikenal': intent != 'tidak_paham'}


SARAN_UMUM = ['Jadwal salat hari ini', 'Arah kiblat dari lokasi saya', 'Kapan 1 Ramadan 1448?', 'Puasa sunah minggu ini',
              'Tanggal hari ini', 'Apa itu rasydulqiblat?', 'Bedanya MABIMS dan Ummul Qura']


def lokasi_dari_teks(t_asli, ctx, slots):
    """Lokasi untuk pertanyaan: kota/koordinat yang disebut > slot sebelumnya > Pengaturan.
    Kembalian (lok, nama, galat, rujukan); galat berisi balasan siap kirim bila kota ambigu/tidak dikenal (tidak diam-diam memakai Pengaturan)."""
    r = cari_lokasi(t_asli)
    if r and r['status'] == 'ambigu':
        pil = ', '.join(r['pilihan'])
        return None, None, balas(f"Ada beberapa **{r['nama']}**: {pil}. Sebutkan provinsinya, misalnya “{r['nama']} {r['pilihan'][0]}”.", 'lokasi_ambigu',
                                 suggestions=[f"{r['nama']} {p}" for p in r['pilihan']][:4]), None
    if r and r['status'] == 'tak_dikenal':
        return None, None, balas(f"Saya belum mengenal lokasi **{r['nama']}**. Coba tulis nama kota/kabupaten lain, tulis koordinat (mis. “-3.2954, 102.8655”), "
                                 "atau atur lokasi lewat menu **Pengaturan** lalu tanyakan tanpa menyebut kota.", 'lokasi_tak_dikenal',
                                 suggestions=['Jadwal salat hari ini', 'Arah kiblat dari lokasi saya']), None
    if r:
        tz = r['tz']
        lok = {'lat': r['lat'], 'lon': r['lon'], 'elev': r['elev'], 'tz': tz, 'tz_label': tz_label(tz)}
        rujuk = None
        if r['sumber'] == 'csv':
            rujuk = f"Titik acuan: {r['pusat'] or 'pusat kota'}, {r['provinsi']} ({r['lat']:.4f}, {r['lon']:.4f}; elevasi {r['elev']:.0f} m)."
        elif r['sumber'] == 'koordinat':
            rujuk = f"Koordinat: {r['lat']:.4f}, {r['lon']:.4f} (zona waktu {lok['tz_label']} diperkirakan dari bujur, elevasi 0 m)."
        return lok, r['nama'], None, rujuk
    if slots.get('kota') and slots.get('lat') is not None:
        lon = slots['lon']
        tz = slots.get('tz') if slots.get('tz') is not None else tz_from_lon(lon)
        return {'lat': slots['lat'], 'lon': lon, 'elev': slots.get('elev') or 0.0, 'tz': tz, 'tz_label': tz_label(tz)}, slots['kota'], None, slots.get('rujuk')
    return ctx['lok'], ctx['nama'], None, None


def slot_lokasi(lok, nama, rujuk):
    return {'kota': nama, 'lat': lok['lat'], 'lon': lok['lon'], 'elev': lok['elev'], 'tz': lok['tz'], 'rujuk': rujuk}
