"""Mesin AstroBot. Alur: sapaan/bantuan → pertanyaan konsep (retrieval) → intent operasional (hitungan nyata) → retrieval cadangan.
Balasan: {status, reply, intent, slots, cards, links, sources, suggestions}. 'slots' dikembalikan ke klien dan dikirim lagi
pada pesan berikutnya agar pertanyaan lanjutan ('kalau di Surabaya?', 'besok?') memahami konteks."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from app.persis import hisab, salat
from app.services import astro_core as ac
from app.services import calendar_service as cs
from app.services import falak_service as F
from app.services import islamic_service as isl
from app.services.home_service import today_summary
from app.services.timezones import tz_from_lon, tz_label

from . import cuaca as cu
from .kota import cari_lokasi, cari_semua_lokasi
from .pengetahuan import basis
from .teks import bersih, token

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


def _ctx(context: dict | None) -> dict:
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


# ── ekstraksi entitas ───────────────────────────────────────────────
# istilah hari relatif terhadap hari ini (H): (pola, selisih hari, nama baku, keterangan H)
REL = [(r'\bbesok lusa\b', 2, 'besok lusa'), (r'\bkemarin lusa\b', -2, 'kemarin lusa'), (r'\bkemarin dulu\b', -2, 'kemarin dulu'),
       (r'\bselumbari\b', -2, 'selumbari'), (r'\bbasarai\b', -2, 'basarai'), (r'\bkila mulai\b|\bkila\b', -3, 'kila mulai'),
       (r'\bsenantu\b', -4, 'senantu'), (r'\bhari h\b', 0, 'hari-H'),
       (r'\bkemarin\b', -1, 'kemarin'), (r'\bbesok\b|\besok\b', 1, 'besok'), (r'\blusa\b', 2, 'lusa'),
       (r'\btulat\b', 3, 'tulat'), (r'\blangkat\b', 3, 'langkat'), (r'\btubin\b', 4, 'tubin'), (r'\btungging\b', 4, 'tungging'),
       (r'\bcekelong\b', 5, 'cekelong'), (r'\bembute\b', 6, 'embute')]
REL_KET = {'senantu': 'H-4 dan sebelumnya', 'embute': 'H+6 dan seterusnya'}


def _tgl_relatif(t: str, hari_ini: date):
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


def _awalan_rel(label, d, hari_ini):
    if label in (None, 'hari ini'):
        return ''
    n = (d - hari_ini).days
    if label in REL_KET:                                     # istilah terbuka: tampilkan tanggal terdekat
        return f"**{label.capitalize()}** = {REL_KET[label]}; ini tanggal terdekatnya (H{n:+d}). "
    ket = f'H{n:+d}' if n else 'H'
    return f"**{label.capitalize()}** = {ket} ({'+' if n > 0 else ''}{n} hari dari hari ini). "


def _tgl_masehi(t: str):
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


def _hijri_dalam(t: str):
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


def _krit_dalam(t: str):
    for kata, kunci in KRIT_KATA.items():
        if re.search(rf'\b{kata}\b', t):
            return kunci
    return None


# ── pencarian tanggal hijriah menurut kriteria ───────────────────────
def _jdn(d: date) -> int:
    return ac.to_jdn(d.year, d.month, d.day)


def _cari_masehi(tgl: int, bln: int, thn: int, krit: str) -> date | None:
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


def _fmt_tgl(d: date) -> str:
    return f"{HARI_ID[d.weekday()]}, {d.day} {BULAN_ID_NAMA[d.month]} {d.year}"


# ── balasan ─────────────────────────────────────────────────────────
def _r(reply, intent, slots=None, cards=None, links=None, sources=None, suggestions=None, status='success'):
    return {'status': status, 'reply': reply, 'intent': intent, 'slots': slots or {}, 'cards': cards or [], 'links': links or [],
            'sources': sources or [], 'suggestions': suggestions or [], 'dikenal': intent != 'tidak_paham'}


SARAN_UMUM = ['Jadwal salat hari ini', 'Arah kiblat dari lokasi saya', 'Kapan 1 Ramadan 1448?', 'Puasa sunah minggu ini',
              'Tanggal hari ini', 'Apa itu rasydulqiblat?', 'Bedanya MABIMS dan Ummul Qura']


def saran_awal() -> list[str]:
    return list(SARAN_UMUM)


def daftar_artikel() -> list[dict]:
    return [{'id': a['id'], 'judul': a['judul'], 'kategori': a['kategori'], 'ringkas': a['ringkas']} for a in basis().artikel.values()]


def ambil_artikel(aid: str) -> dict | None:
    a = basis().artikel.get(aid)
    return None if not a else {k: a[k] for k in ('id', 'judul', 'kategori', 'ringkas', 'isi', 'tautan', 'kata_kunci')}


def _i_sapaan(t):
    if re.fullmatch(r'\s*(halo|hai|hi|hello|assalamualaikum|assalamu\'alaikum|selamat (pagi|siang|sore|malam)|p|test|tes)\W*(astrobot|bot)?\W*', t):
        return _r('Halo! Saya **AstroBot**. Saya bisa menghitung jadwal salat, arah kiblat, tanggal Hijriah/Jawa, dan menjelaskan konsep falak serta astronomi. Mau mulai dari mana?',
                  'sapaan', suggestions=SARAN_UMUM[:5])
    if re.search(r'\b(terima kasih|makasih|thanks|thx|matur nuwun|jazakallah)\b', t):
        return _r('Sama-sama! Kalau ada yang ingin dihitung atau dijelaskan lagi, tanyakan saja.', 'terima_kasih', suggestions=SARAN_UMUM[:3])
    return None


def _i_bantuan(t):
    if re.search(r'\b(bantuan|help|panduan|menu|fitur|bisa (apa|ngapain)|apa saja yang bisa|kamu bisa|anda bisa)\b', t):
        return _r('Yang bisa saya bantu:\n- **Jadwal salat** (juga untuk kota lain/tanggal lain)\n- **Arah kiblat** dan **rasydulqiblat**\n- **Tanggal hari ini** (Masehi, Hijriah, Jawa, weton, wuku) dan **konversi tanggal**\n- **Awal bulan Hijriah** menurut kriteria yang Anda pilih\n- **Puasa sunah** dan hari penting\n- **Fase Bulan** malam ini\n- **Penjelasan konsep**: kriteria hilal, kalender Jawa, gerhana, hujan meteor, dan lainnya\n\nHasil hitungan memakai lokasi, metode salat, dan kriteria Hijriah dari menu **Pengaturan**.',
                  'bantuan', suggestions=SARAN_UMUM)
    return None


def _lokasi_dari_teks(t_asli, ctx, slots):
    """Lokasi untuk pertanyaan: kota/koordinat yang disebut > slot sebelumnya > Pengaturan.
    Kembalian (lok, nama, galat, rujukan); galat berisi balasan siap kirim bila kota ambigu/tidak dikenal (tidak diam-diam memakai Pengaturan)."""
    r = cari_lokasi(t_asli)
    if r and r['status'] == 'ambigu':
        pil = ', '.join(r['pilihan'])
        return None, None, _r(f"Ada beberapa **{r['nama']}**: {pil}. Sebutkan provinsinya, misalnya “{r['nama']} {r['pilihan'][0]}”.", 'lokasi_ambigu',
                              suggestions=[f"{r['nama']} {p}" for p in r['pilihan']][:4]), None
    if r and r['status'] == 'tak_dikenal':
        return None, None, _r(f"Saya belum mengenal lokasi **{r['nama']}**. Coba tulis nama kota/kabupaten lain, tulis koordinat (mis. “-3.2954, 102.8655”), "
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


def _slot_lok(lok, nama, rujuk):
    return {'kota': nama, 'lat': lok['lat'], 'lon': lok['lon'], 'elev': lok['elev'], 'tz': lok['tz'], 'rujuk': rujuk}


def _i_salat(t, t_asli, ctx, slots, hari_ini, lanjut):
    kata_salat = re.search(r'\b(salat|jadwal|imsak|subuh|zuhur|asar|magrib|isya|duha|terbit|waktu)\b', t)
    if not kata_salat and not (lanjut and slots.get('intent') == 'salat'):
        return None
    if re.search(r'\b(kiblat|rasydul|puasa|hijriah|kalender|konversi|fase|bulan)\b', t) and not re.search(r'\b(salat|jadwal)\b', t):
        return None
    if re.search(r'\bwaktu (yang )?(terbaik|tepat)\b|\bwaktu\b.*\b(pengamatan|observasi)\b', t):
        return None
    d, label = _tgl_relatif(t, hari_ini)
    tm = _tgl_masehi(t)
    if isinstance(tm, date):
        d = tm
    elif tm and tm[2] or (tm and tm[1]):
        try:
            d = date(tm[2] or hari_ini.year, tm[1], tm[0])
        except ValueError:
            return _r('Tanggal itu tidak valid. Coba tulis seperti "17 Agustus 2026".', 'salat', status='error')
    d = d or (date.fromisoformat(slots['tanggal']) if slots.get('tanggal') and lanjut else hari_ini)
    lok, nama, galat, rujuk = _lokasi_dari_teks(t_asli, ctx, slots if lanjut else {})
    if galat:
        galat['slots'] = {'intent': 'salat', 'tanggal': d.isoformat()}
        return galat
    m = salat.METODE[ctx['metode']]
    try:
        j = F.jadwal_salat(d, lok, m, ctx['ihtiyat'], ctx['imsak'])
    except F.InputError as e:
        return _r(str(e), 'salat', status='error')
    rows = {x['kunci']: x for x in j['waktu']}
    minta = [WAKTU_SALAT[k] for k in re.findall(r'\b(imsak|subuh|terbit|duha|zuhur|asar|magrib|isya)\b', t)]
    slot = {'intent': 'salat', 'tanggal': d.isoformat(), **_slot_lok(lok, nama, rujuk)}
    judul = f"{nama}, {_fmt_tgl(d)}"
    if len(minta) == 1:
        x = rows[minta[0]]['jadwal']
        isi = x['jam'] or '—'
        ket = f" ({x['keterangan']})" if x['keterangan'] else ''
        txt = f"**{rows[minta[0]]['nama']}** di {nama}, {_fmt_tgl(d)}: **{isi} {lok['tz_label']}**{ket}.\nMetode {m.name}, ihtiyat {ctx['ihtiyat']} menit."
        kartu = []
    else:
        txt = f"Jadwal salat **{nama}**, {_fmt_tgl(d)} ({lok['tz_label']}), metode **{m.name}**, ihtiyat {ctx['ihtiyat']} menit:"
        kartu = [{'tipe': 'tabel', 'judul': judul, 'kolom': ['Waktu', 'Jam'],
                  'baris': [[x['nama'], x['jadwal']['jam'] or '—'] for x in j['waktu'] if x['kunci'] != 'nisfuLail']}]
    if rujuk:
        txt += '\n\n' + rujuk
    if j.get('ramadan'):
        txt += '\n\nTanggal ini terdeteksi masuk **Ramadan** menurut Ummul Qura untuk penyesuaian Isya.'
    return _r(txt, 'salat', slot, kartu, [{'teks': 'Buka Salat & Kiblat', 'url': '/islamic/'}], ['Perhitungan: app/persis (port persis-times-js)'],
              ['Besok?', 'Kalau di Surabaya?', 'Arah kiblat dari sini', 'Apa itu ihtiyat?'])


def _i_kiblat(t, t_asli, ctx, slots, hari_ini, lanjut):
    if not re.search(r'\b(kiblat|rasydulkiblat)\b', t):
        return None
    lok, nama, galat, rujuk = _lokasi_dari_teks(t_asli, ctx, slots if lanjut else {})
    if galat:
        galat['slots'] = {'intent': 'kiblat'}
        return galat
    if re.search(r'\brasydulkiblat\b', t) or re.search(r'\bbayangan\b', t):
        try:
            r = F.rasydulqiblat(hari_ini, lok, 'vincenty', 7, hari_ini.year, 1)
        except Exception as e:
            return _r(f'Maaf, gagal menghitung rasydulqiblat: {e}', 'rasydulqiblat', status='error')
        th = (r.get('tahunan') or [{}])[0]
        baris = []
        for k, nm in (('rasydul1', 'Rasydulqiblat 1'), ('rasydul2', 'Rasydulqiblat 2'), ('antipoda1', 'Antipoda 1 (bayangan berlawanan)'), ('antipoda2', 'Antipoda 2 (bayangan berlawanan)')):
            e = th.get(k)
            if e:
                tampak = '' if e['matahari_di_lokasi']['terlihat'] else ' (Matahari di bawah ufuk)'
                baris.append([nm, f"{e['hari']}, {e['tanggal']}", f"{e['jam']}{tampak}"])
        h = (r.get('harian') or [{}])[0]
        if h.get('bayangan_ke_kiblat'):
            baris.append(['Harian: ' + h['tanggal'], 'bayangan sejajar kiblat', h['bayangan_ke_kiblat'][0]['jam']])
        if not baris:
            return _r('Data rasydulqiblat tidak tersedia untuk lokasi ini. Buka halaman Salat & Kiblat untuk detailnya.', 'rasydulqiblat',
                      links=[{'teks': 'Buka Salat & Kiblat', 'url': '/islamic/'}])
        return _r(f'Rasydulqiblat **tahunan** untuk **{nama}** tahun {hari_ini.year} (saat bayangan benda tegak menunjuk arah kiblat):',
                  'rasydulqiblat', {'intent': 'kiblat', **_slot_lok(lok, nama, rujuk)},
                  [{'tipe': 'tabel', 'judul': f'Rasydulqiblat {nama}', 'kolom': ['Peristiwa', 'Tanggal', 'Jam'], 'baris': baris}],
                  [{'teks': 'Rasydulqiblat & kompas', 'url': '/islamic/'}], ['app/persis/kiblat'], ['Apa itu rasydulqiblat?', 'Arah kiblat di Medan'])
    k = F.info_kiblat(lok)
    v = k['vincenty']
    jarak = f"{k['jarak_km']:,.0f}".replace(',', '.')
    txt = (f"Arah kiblat dari **{nama}**: **{v['dms']}** dari utara searah jarum jam (**{v['derajat']:.2f}°**, arah **{k['mata_angin']}**).\n"
           f"Jarak ke Ka'bah ±{jarak} km.\nModel bola: {k['bola']['dms']}; elipsoid: {k['elipsoid']['dms']}." + (f"\n\n{rujuk}" if rujuk else ''))
    return _r(txt, 'kiblat', {'intent': 'kiblat', **_slot_lok(lok, nama, rujuk)}, [],
              [{'teks': 'Kompas kiblat & peta', 'url': '/islamic/'}], ['app/persis/kiblat (Vincenty)'],
              ['Rasydulqiblat tahun ini', 'Kalau di Medan?', 'Cara menghitung arah kiblat'])


def _i_puasa(t, ctx, hari_ini):
    if not re.search(r'\b(puasa|ayyamulbid|tasua|asyura|arafah|hari penting|tanggal penting)\b', t):
        return None
    hari = 45 if re.search(r'\b(45|bulan|sebulan)\b', t) else 14 if re.search(r'\b(minggu|pekan|seminggu)\b', t) else 30
    try:
        rows = isl.fasting_schedule(hari_ini, hari, ctx['krit'])
    except Exception as e:
        return _r(f'Maaf, jadwal puasa tidak dapat dihitung: {e}', 'puasa', status='error')
    if not rows:
        return _r(f'Tidak ada puasa sunah atau hari penting dalam {hari} hari ke depan menurut kriteria {KRIT_NAMA[ctx["krit"]]}.', 'puasa')
    baris = [[f"{r['hari']}, {r['tanggal'][8:]}/{r['tanggal'][5:7]}", r['hijriah'], r['peristiwa'] or r['keterangan']] for r in rows[:14]]
    return _r(f"Puasa sunah dan hari penting **{hari} hari ke depan** (kalender Hijriah **{KRIT_NAMA[ctx['krit']]}**):", 'puasa',
              {'intent': 'puasa'}, [{'tipe': 'tabel', 'judul': 'Puasa & hari penting', 'kolom': ['Hari', 'Hijriah', 'Keterangan'], 'baris': baris}],
              [{'teks': 'Selengkapnya', 'url': '/islamic/'}], ['islamic_service.fasting_schedule'], ['Apa saja puasa sunah?', 'Kapan 1 Ramadan 1448?'])


def _i_awal_bulan(t, ctx, hari_ini, sl):
    h = _hijri_dalam(t)
    if not h or not re.search(r'\b(kapan|tanggal berapa|jatuh|awal|masehi|berapa|mulai|1|satu)\b', t):
        return None
    bln, tgl, thn = h
    krit = _krit_dalam(t) or ctx['krit']
    if thn is None:
        # tahun Hijriah berikutnya dari hari ini
        jdn = _jdn(hari_ini)
        try:
            thn_now = isl.hijri_menurut(jdn, krit)['tahun']
            b_now = isl.hijri_menurut(jdn, krit)['bulan']
        except Exception:
            thn_now, b_now = cs.hijri_info(jdn)['tahun'], cs.hijri_info(jdn)['bulan']
        thn = thn_now if bln >= b_now else thn_now + 1
    tg = tgl or 1
    if not 1 <= tg <= 30 or not 1300 <= thn <= 1800:
        return _r('Tahun Hijriah di luar rentang yang saya dukung (1300–1800 H) atau tanggal tidak valid.', 'hijri_ke_masehi', status='error')
    d = _cari_masehi(tg, bln, thn, krit)
    if not d:
        return _r(f'Tanggal {tg} {HIJRI_NAMA[bln]} {thn} H tidak ditemukan menurut kriteria {KRIT_NAMA[krit]} (kriteria hisab hanya berlaku 1700–2300 M atau tanggal itu tidak ada).', 'hijri_ke_masehi', status='error')
    txt = f"**{tg} {HIJRI_NAMA[bln]} {thn} H** jatuh pada **{_fmt_tgl(d)}** menurut kriteria **{KRIT_NAMA[krit]}**."
    kartu = []
    if krit != 'aritmetis' or True:
        baris = []
        for kk in ('aritmetis', 'mabims', 'ummulqura', 'wujudulhilal', 'turki'):
            dd = _cari_masehi(tg, bln, thn, kk)
            baris.append([KRIT_NAMA[kk], _fmt_tgl(dd) if dd else '—'])
        kartu = [{'tipe': 'tabel', 'judul': f'{tg} {HIJRI_NAMA[bln]} {thn} H menurut kriteria', 'kolom': ['Kriteria', 'Tanggal Masehi'], 'baris': baris}]
    txt += '\n\nIni hasil hisab, **bukan penetapan resmi** (sidang isbat). Dapat berbeda 1–2 hari.'
    return _r(txt, 'hijri_ke_masehi', {'intent': 'hijri_ke_masehi', 'bulan': bln, 'tgl': tg, 'tahun': thn}, kartu,
              [{'teks': 'Bandingkan kalender', 'url': '/calendar/'}], ['app/persis/hisab'], ['Apa beda kriteria MABIMS dan Ummul Qura?', 'Kapan 1 Syawal ' + str(thn) + '?'])


def _i_konversi(t, ctx, hari_ini):
    tm = _tgl_masehi(t)
    if tm is None or isinstance(tm, date) is False and tm[2] is None and not re.search(r'\b(hijriah|jawa|weton|konversi|tanggal)\b', t):
        return None
    if isinstance(tm, date):
        d = tm
    else:
        try:
            d = date(tm[2] or hari_ini.year, tm[1], tm[0])
        except ValueError:
            return _r('Tanggal itu tidak valid. Coba tulis seperti "17 Agustus 2026".', 'konversi', status='error')
    return _ringkas_tanggal(d, ctx, 'konversi')


def _ringkas_tanggal(d: date, ctx, intent, awalan=''):
    jdn = _jdn(d)
    try:
        g, j = cs.gregorian_info(jdn), cs.javanese_info(jdn)
        hij = isl.hijri_menurut(jdn, ctx['krit'])
    except Exception as e:
        return _r(f'Maaf, gagal menghitung tanggal itu: {e}', intent, status='error')
    baris = [['Masehi', _fmt_tgl(d)], [f"Hijriah ({KRIT_NAMA[ctx['krit']]})", hij['teks']],
             ['Jawa Mataraman', f"{j['tanggal']} {j['bulan']} {j['tahun_windu']} {j['tahun']} AJ"], ['Weton', j['weton']], ['Wuku', j['wuku']]]
    return _r(f"{awalan}Tanggal **{_fmt_tgl(d)}** dalam berbagai kalender:", intent, {'intent': 'konversi', 'tanggal': d.isoformat()},
              [{'tipe': 'tabel', 'judul': 'Padanan tanggal', 'kolom': ['Kalender', 'Tanggal'], 'baris': baris}],
              [{'teks': 'Lab Kalender', 'url': '/calendar/'}], ['calendar_service, hisab'], ['Besok?', 'Kapan 1 Ramadan 1448?'])


def _i_hari_ini(t, ctx, hari_ini, now):
    if not re.search(r'\b(tanggal|hari apa|weton|wuku|pasaran|kalender|hijriah|jawa)\b', t) or re.search(r'\b(salat|jadwal|puasa|cuaca)\b', t):
        return None
    d, label = _tgl_relatif(t, hari_ini)
    if d is None and re.search(r'\b(hari ini|tanggal|weton|hari apa|pasaran)\b', t):
        d = hari_ini
    return _ringkas_tanggal(d, ctx, 'tanggal', _awalan_rel(label, d, hari_ini)) if d else None


def _i_bulan(t, ctx, now_utc):
    if not re.search(r'\b(fase bulan|bulan purnama|purnama|bulan sabit|umur bulan|bulan malam ini|bulan hari ini|bentuk bulan)\b', t):
        return None
    if re.search(r'\b(kapan|jadwal)\b', t):
        return None
    s = today_summary(now_utc, ctx['lok']['tz'])
    b = s['bulan']
    return _r(f"Malam ini Bulan berada pada fase **{b['fase']}** {b['emoji']} dengan penerangan ±**{b['terang_pct']}%**, umur ±{b['umur_hari']} hari ({b['arah']}).",
              'fase_bulan', {'intent': 'fase_bulan'}, [], [{'teks': 'Beranda', 'url': '/'}], ['home_service.today_summary'],
              ['Apa itu fase bulan?', 'Tanggal hari ini'])


def _i_event(t):
    if re.search(r'\b(gerhana|meteor|konjungsi|oposisi|event|peristiwa langit|fenomena)\b', t) and re.search(r'\b(kapan|mendatang|bulan depan|minggu ini|terdekat|akan)\b', t):
        return _r('Daftar peristiwa langit mendatang (gerhana, konjungsi, hujan meteor, dan lainnya) dihitung per lokasi di **Katalog Event**. Bangun katalog sekali, lalu semua event dinilai keterlihatannya dari lokasi Anda.',
                  'event', links=[{'teks': 'Buka Katalog Event', 'url': '/catalog/'}], suggestions=['Apa itu hujan meteor?', 'Kenapa gerhana tidak terjadi tiap bulan?'])
    return None



def _i_weton(t, ctx, hari_ini):
    if not re.search(r'\b(weton|neptu|pasaran|wuku|pawukon)\b', t):
        return None
    d, _ = _tgl_relatif(t, hari_ini)
    tm = _tgl_masehi(t)
    if isinstance(tm, date):
        d = tm
    elif tm:
        try:
            d = date(tm[2] or hari_ini.year, tm[1], tm[0])
        except ValueError:
            return _r('Tanggal itu tidak valid. Coba tulis seperti "17 Agustus 2026".', 'weton', status='error')
    d = d or hari_ini
    j = cs.javanese_info(_jdn(d))
    txt = (f"Weton **{_fmt_tgl(d)}** adalah **{j['weton']}**, neptu **{j['neptu']}** ({j['neptu_rincian']}).\n"
           f"Pawukon: {j['hari']} {j['pasaran']} {j['sadwara']} {j['wuku']} (wuku ke-{j['wuku_no']}, hari ke-{j['hari_pawukon']} dari 210).\n"
           f"Tanggal Jawa Mataraman: {j['tanggal']} {j['bulan']} {j['tahun_windu']} {j['tahun']} AJ.")
    return _r(txt, 'weton', {'intent': 'konversi', 'tanggal': d.isoformat()}, [], [{'teks': 'Lab Kalender', 'url': '/calendar/'}],
              ['calendar_service (neptu, pawukon)'], ['Besok?', 'Apa itu weton?', 'Apa itu pawukon?'])


def _i_jumlah_hari(t, ctx, hari_ini):
    h = _hijri_dalam(t)
    if not h or not re.search(r'\b(jumlah hari|berapa hari|panjang|umur bulan|lama bulan|berapa lama)\b', t):
        return None
    bln, _, thn = h
    if thn is None:
        jdn = _jdn(hari_ini)
        try:
            now_h = isl.hijri_menurut(jdn, ctx['krit'])
        except Exception:
            now_h = cs.hijri_info(jdn)
        thn = now_h['tahun'] if bln >= now_h['bulan'] else now_h['tahun'] + 1
    if not 1300 <= thn <= 1800:
        return _r('Tahun Hijriah di luar rentang yang saya dukung (1300–1800 H).', 'jumlah_hari', status='error')
    nb, nt = (bln + 1, thn) if bln < 12 else (1, thn + 1)
    baris, hasil = [], {}
    for kk in ('aritmetis', 'mabims', 'ummulqura', 'wujudulhilal', 'turki'):
        a, b = _cari_masehi(1, bln, thn, kk), _cari_masehi(1, nb, nt, kk)
        n = (b - a).days if a and b else None
        hasil[kk] = n
        baris.append([KRIT_NAMA[kk], f"{a.day} {BULAN_ID_NAMA[a.month]} {a.year}" if a else '—', f"{b.day} {BULAN_ID_NAMA[b.month]} {b.year}" if b else '—',
                      f'{n} hari' if n else '—'])
    krit = _krit_dalam(t) or ctx['krit']
    n0 = hasil.get(krit)
    asal = '' if _krit_dalam(t) else ' (pilihan di Pengaturan)'
    awal = f"**{HIJRI_NAMA[bln]} {thn} H** berumur **{n0} hari** menurut kriteria **{KRIT_NAMA[krit]}**{asal}." if n0 else \
        f"Umur **{HIJRI_NAMA[bln]} {thn} H** menurut kriteria {KRIT_NAMA[krit]} tidak dapat dihitung (di luar jangkauan hisab)."
    nilai = {v for v in hasil.values() if v}
    ket = '\n\nUmur bulan Hijriah selalu 29 atau 30 hari.'
    if len(nilai) > 1:
        ket += ' Umurnya berbeda antarkriteria karena awal bulan berikutnya berbeda (lihat tabel).'
    ket += ' Ini hasil hisab, **bukan penetapan resmi** (sidang isbat).'
    return _r(awal + ket, 'jumlah_hari', {'intent': 'jumlah_hari'},
              [{'tipe': 'tabel', 'judul': f'Umur {HIJRI_NAMA[bln]} {thn} H per kriteria', 'kolom': ['Kriteria', f'1 {HIJRI_NAMA[bln]}', f'1 {HIJRI_NAMA[nb]}', 'Umur'], 'baris': baris}],
              [{'teks': 'Bandingkan kalender', 'url': '/calendar/'}], ['app/persis/hisab'], [f'Kapan 1 {HIJRI_NAMA[bln]} {thn}?', 'Apa beda MABIMS dan Ummul Qura?'])


def _i_cuaca(t, t_asli, ctx, slots, hari_ini, now_utc, lanjut):
    if not re.search(r'\b(cuaca|hujan|mendung|cerah|berawan|awan|suhu|panas|dingin|gerimis)\b', t) or re.search(r'\b(meteor|skor|kelayakan)\b', t):
        return None
    if not re.search(r'\b(hari ini|sekarang|nanti|malam ini|sore ini|pagi ini|siang ini|di|tempat|tempatku|sini|lokasi|besok)\b', t):
        return None
    lok, nama, galat, rujuk = _lokasi_dari_teks(t_asli, ctx, slots if lanjut else {})
    if galat:
        galat['slots'] = {'intent': 'cuaca'}
        return galat
    if re.search(r'\bbesok\b', t):
        return _r('Untuk saat ini saya hanya meringkas cuaca **hari ini**. Prakiraan beberapa hari ke depan ada di halaman **Observasi**.', 'cuaca',
                  {'intent': 'cuaca', **_slot_lok(lok, nama, rujuk)}, links=[{'teks': 'Buka Observasi', 'url': '/observation/'}])
    c = cu.cuaca_hari_ini(lok['lat'], lok['lon'], now_utc)
    slot = {'intent': 'cuaca', **_slot_lok(lok, nama, rujuk)}
    if not c:
        return _r(f"Maaf, layanan prakiraan cuaca (Open-Meteo) tidak dapat dihubungi dari server saat ini, jadi saya tidak dapat menampilkan cuaca **{nama}**. "
                  "Saya tidak menebak. Coba lagi beberapa saat lagi.", 'cuaca', slot, links=[{'teks': 'Buka Observasi', 'url': '/observation/'}], sources=['Open-Meteo'])
    fmt = lambda x, d='': '—' if x is None else f'{x:.0f}{d}'
    baris = [[f"{b['nama']} ({b['rentang']})", b['kondisi'], fmt(b['awan'], '%'), fmt(b['hujan'], '%'), fmt(b['suhu'], '°C')] for b in c['blok']]
    k = c['sekarang']
    awal = f"Cuaca **{nama}** hari ini ({c['tanggal']}, pukul {c['jam_lokal']} waktu setempat)"
    if k:
        awal += f": sekarang **{W_label(k)}**, awan {fmt(k['cloud_cover_pct'], '%')}, suhu {fmt(k['temp_c'], '°C')}, kelembapan {fmt(k['humidity_pct'], '%')}."
    else:
        awal += ':'
    return _r(awal + ('\n\n' + rujuk if rujuk else ''), 'cuaca', slot,
              [{'tipe': 'tabel', 'judul': 'Prakiraan per bagian hari', 'kolom': ['Waktu', 'Kondisi', 'Awan', 'Peluang hujan', 'Suhu'], 'baris': baris}],
              [{'teks': 'Observasi & skor langit', 'url': '/observation/'}], ['Open-Meteo (prakiraan per jam)'],
              ['Rekomendasi observasi langit minggu ini', 'Kalau di Surabaya?'])


def W_label(row):
    from app.services.weather_service import _condition_label
    return _condition_label(row.get('cloud_cover_pct'), row.get('precipitation_prob'))


def _i_observasi(t, t_asli, ctx, slots, hari_ini, now_utc, lanjut):
    if not (re.search(r'\b(rekomendasi|saran|sebaiknya|terbaik|bagus|cocok|layak)\b', t) and re.search(r'\b(observasi|amati|mengamati|pengamatan|langit|bintang|stargazing)\b', t)):
        return None
    lok, nama, galat, rujuk = _lokasi_dari_teks(t_asli, ctx, slots if lanjut else {})
    if galat:
        galat['slots'] = {'intent': 'observasi'}
        return galat
    n = 1 if re.search(r'\bmalam ini\b|\bhari ini\b', t) else 7
    m = cu.malam_minggu(lok['lat'], lok['lon'], lok['tz'], now_utc, n)
    malam = m['malam']
    baris = []
    for x in malam:
        d = x['tanggal']
        cuaca_t = '—' if x['kondisi'] is None else f"{x['kondisi']} (awan {x['awan']:.0f}%)" if x['awan'] is not None else x['kondisi']
        baris.append([f"{HARI_ID[d.weekday()]}, {d.day} {BULAN_ID_NAMA[d.month][:3]}", f"{x['fase']} {x['terang'] * 100:.0f}%" + (', di bawah ufuk' if x['tinggi_bulan'] < 0 else f", tinggi {x['tinggi_bulan']:.0f}°"),
                      cuaca_t, '—' if x['skor'] is None else f"{x['skor']:.0f}"])
    skor = [x for x in malam if x['skor'] is not None]
    if skor:
        b = max(skor, key=lambda x: x['skor'])
        d = b['tanggal']
        rek = f"Malam terbaik untuk mata telanjang di **{nama}**: **{HARI_ID[d.weekday()]}, {d.day} {BULAN_ID_NAMA[d.month]}** (skor {b['skor']:.0f}/100; {b['fase']} {b['terang'] * 100:.0f}%)."
        if any(x.get('jenis') == 'climatology' for x in malam):
            rek += ' Sebagian malam memakai rata-rata historis, bukan prakiraan.'
    else:
        b = min(malam, key=lambda x: x['terang'])
        d = b['tanggal']
        rek = (f"Prakiraan cuaca tidak dapat dimuat, jadi rekomendasi ini hanya dari **cahaya Bulan**: Bulan paling redup di **{nama}** pada **{HARI_ID[d.weekday()]}, {d.day} {BULAN_ID_NAMA[d.month]}** "
               f"({b['fase']} {b['terang'] * 100:.0f}%). Cek awan sebelum berangkat.")
    teks = rek + '\n\nTips: pilih lokasi jauh dari lampu, tunggu ±20 menit agar mata beradaptasi, dan lihat awan sebelum berangkat.'
    kartu = [{'tipe': 'tabel', 'judul': f"Malam-malam ke depan (pukul 20.00 waktu setempat)", 'kolom': ['Malam', 'Bulan', 'Cuaca', 'Skor'], 'baris': baris}]
    ev = cu.event_katalog(lok['lat'], lok['lon'], lok['tz'], now_utc, 7, 5) if n > 1 else None
    if ev and ev.get('items'):
        kartu.append({'tipe': 'tabel', 'judul': 'Event katalog yang dapat diamati', 'kolom': ['Event', 'Waktu terbaik', 'Skor'],
                      'baris': [[i['title'], i['best_local'], '—' if i['score'] is None else f"{i['score']:.0f}"] for i in ev['items']]})
    else:
        teks += '\n\nUntuk event spesifik (gerhana, konjungsi, hujan meteor) bangun dulu **Katalog Event**.'
    return _r(teks, 'observasi', {'intent': 'observasi', **_slot_lok(lok, nama, rujuk)}, kartu,
              [{'teks': 'Observasi & skor langit', 'url': '/observation/'}, {'teks': 'Katalog Event', 'url': '/catalog/'}],
              ['planner_service (skor kelayakan)', 'Open-Meteo'] if skor else ['planner_service'], ['Bagaimana cuaca hari ini?', 'Apakah hujan meteor berbahaya?', 'Fase Bulan malam ini'])


def _utc_ke_lokal(jd_utc, tz):
    from catalog import events as C
    return C.jd_to_utc(jd_utc) + timedelta(hours=tz)


def _tgl_jam(teks_lokal):
    """'2027-02-06 23:00' -> 'Sabtu, 6 Februari 2027 pukul 23:00'."""
    dt = datetime.strptime(teks_lokal[:16], '%Y-%m-%d %H:%M')
    return f"{HARI_ID[dt.weekday()]}, {dt.day} {BULAN_ID_NAMA[dt.month]} {dt.year} pukul {dt:%H:%M}"


def _jam_lokal(dt, tz):
    return f"{HARI_ID[dt.weekday()]}, {dt.day} {BULAN_ID_NAMA[dt.month]} {dt.year}, pukul {dt:%H:%M} {tz_label(tz)}"


FASE_KATA = {'new_moon': ('bulan baru', 'Bulan baru (ijtimak)'), 'full_moon': ('purnama', 'Purnama'),
             'first_quarter': ('kuartal pertama', 'Kuartal pertama'), 'last_quarter': ('kuartal akhir', 'Kuartal akhir')}


def _i_fase_berikut(t, ctx, now_utc):
    if not re.search(r'\b(kapan|berikutnya|selanjutnya|terdekat|jadwal)\b', t):
        return None
    if re.search(r'\bbulan baru\b|\bijtimak\b|\bkonjungsi bulan\b', t):
        kind = 'new_moon'
    elif re.search(r'\bpurnama\b|\bbulan penuh\b', t):
        kind = 'full_moon'
    elif re.search(r'\bkuartal pertama\b|\bparuh pertama\b', t):
        kind = 'first_quarter'
    elif re.search(r'\bkuartal akhir\b|\bkuartal ketiga\b|\bparuh akhir\b', t):
        kind = 'last_quarter'
    else:
        return None
    from catalog import events as C
    from prototype import find_events as F
    jd0 = 2440587.5 + now_utc.timestamp() / 86400.0
    fase = sorted(F.moon_phases(jd0 - 1, jd0 + 45), key=lambda e: e['jd'])
    fase = [e for e in fase if e['jd'] > jd0]
    tz = ctx['lok']['tz']
    mau = next(e for e in fase if e['kind'] == kind)
    baris = [[FASE_KATA[e['kind']][1], _jam_lokal(_utc_ke_lokal(e['jd'], tz), tz)] for e in fase[:5]]
    dt = _utc_ke_lokal(mau['jd'], tz)
    sisa = (mau['jd'] - jd0)
    txt = (f"**{FASE_KATA[kind][1]}** berikutnya: **{_jam_lokal(dt, tz)}** ({sisa:.1f} hari lagi).\n"
           "Waktu dihitung dari bujur ekliptika Bulan dan Matahari; hari Hijriah baru ditentukan oleh kriteria hilal, bukan saat ijtimak.")
    return _r(txt, 'fase_berikut', {'intent': 'fase_berikut'}, [{'tipe': 'tabel', 'judul': 'Fase Bulan berikutnya', 'kolom': ['Fase', 'Waktu'], 'baris': baris}],
              [{'teks': 'Beranda', 'url': '/'}], ['prototype.find_events (mesin Bulan katalog)'], ['Kapan gerhana matahari terdekat?', 'Kapan 1 Ramadan 1448?'])


def _i_gerhana(t, t_asli, ctx, slots, now_utc):
    if not re.search(r'\bgerhana\b', t) or not re.search(r'\b(kapan|terdekat|berikutnya|selanjutnya|mendatang|akan datang|nanti)\b', t):
        return None
    jenis = 'matahari' if re.search(r'\bmatahari\b', t) else 'bulan' if re.search(r'\bbulan\b', t) else 'semua'
    lok, nama, galat, rujuk = _lokasi_dari_teks(t_asli, ctx, {})
    if galat:
        return galat
    from catalog import events as C
    from catalog import service as S
    from prototype import find_events as F
    jd0 = 2440587.5 + now_utc.timestamp() / 86400.0
    raw = []
    if jenis in ('matahari', 'semua'):
        raw += C.solar_eclipses(jd0, jd0 + 365.25 * 6)
    if jenis in ('bulan', 'semua'):
        raw += C.lunar_eclipses(jd0, jd0 + 365.25 * 6)
    ev = sorted(C.normalize(raw), key=lambda e: e['time_utc'])
    tz = lok['tz']
    kat = {'matahari': 'gerhana_matahari', 'bulan': 'gerhana_bulan'}
    baris, pertama_terlihat, pertama = [], None, None
    for e in ev:
        if jenis != 'semua' and e['category'] != kat[jenis]:
            continue
        d = S.decorate(e, lok['lat'], lok['lon'], 'pinggiran', tz)
        v = d['visibility']
        if pertama is None:
            pertama = d
        if v.get('observable') and pertama_terlihat is None:
            pertama_terlihat = d
        if len(baris) < 6:
            baris.append([d['title'], d['time_local'], 'Terlihat' if v.get('observable') else 'Tidak terlihat'])
    if not pertama:
        return _r('Tidak ada gerhana yang ditemukan dalam 6 tahun ke depan.', 'gerhana')
    label = {'matahari': 'Gerhana Matahari', 'bulan': 'Gerhana Bulan', 'semua': 'Gerhana'}[jenis]
    v = pertama['visibility']
    txt = f"**{label} terdekat (global)**: {pertama['title']} pada **{_tgl_jam(pertama['time_local'])} {tz_label(tz)}** (puncak). Dari **{nama}**: **{v['headline']}**."
    if pertama_terlihat and pertama_terlihat is not pertama:
        txt += f"\n\nYang **pertama terlihat dari {nama}**: {pertama_terlihat['title']} (global), {_tgl_jam(pertama_terlihat['time_local'])} {tz_label(tz)}; dari sini: {pertama_terlihat['visibility']['headline'].lower()}."
    elif not pertama_terlihat:
        txt += f"\n\nTidak ada {label.lower()} yang terlihat dari {nama} dalam 6 tahun ke depan."
    if jenis in ('matahari', 'semua'):
        txt += '\n\n⚠️ Jangan menatap Matahari tanpa filter surya bersertifikat, termasuk saat gerhana sebagian.'
    txt += '\nWaktu puncak perkiraan mesin katalog (belum divalidasi terhadap almanak resmi).'
    return _r(txt + (('\n\n' + rujuk) if rujuk else ''), 'gerhana', {'intent': 'gerhana', **_slot_lok(lok, nama, rujuk)},
              [{'tipe': 'tabel', 'judul': f'{label} 6 tahun ke depan (dari {nama})', 'kolom': ['Gerhana', f'Puncak ({tz_label(tz)})', 'Dari lokasi'], 'baris': baris}],
              [{'teks': 'Katalog Event', 'url': '/catalog/'}], ['catalog.events (mesin Bulan/Matahari)'], ['Apakah gerhana berbahaya dilihat?', 'Kenapa gerhana tidak terjadi tiap bulan?'])


def _i_tahun(t, ctx, hari_ini):
    if not re.search(r'\btahun\b', t) or not re.search(r'\b(sekarang|ini|saat ini|berapa)\b', t) or re.search(r'\b(kabisat|depan|lalu|kemarin|besok|kiblat|rasydulkiblat|salat|puasa|jadwal|gerhana|meteor|cuaca|ramadan|syawal)\b', t):
        return None
    if not re.search(r'\b(saka|jyotisa|hindu|jawa|aj|mataram|hijriah|hijri|islam|masehi)\b|tahun berapa', t):
        return None
    d, _ = _tgl_relatif(t, hari_ini)
    d = d or hari_ini
    jdn = _jdn(d)
    j, k = cs.javanese_info(jdn), F.konversi('masehi', d.year, d.month, d.day, None, None)
    hij = isl.hijri_menurut(jdn, ctx['krit'])
    sk = k['jyotisa']
    ada = {'saka': bool(re.search(r'\b(saka|jyotisa|hindu)\b', t)), 'jawa': bool(re.search(r'\b(jawa|aj|sultan agung|mataram)\b', t)),
           'hijriah': bool(re.search(r'\b(hijriah|islam|hijri)\b', t)), 'masehi': bool(re.search(r'\bmasehi\b', t))}
    nilai = {'masehi': f"{d.year} M", 'hijriah': f"{hij['tahun']} H ({KRIT_NAMA[ctx['krit']]})", 'jawa': f"{j['tahun_windu']} {j['tahun']} AJ (Anno Javanico)",
             'saka': f"{sk['tahun_saka']} Saka"}
    fokus = [k_ for k_, v in ada.items() if v]
    if len(fokus) == 1:
        f = fokus[0]
        nm = {'masehi': 'Masehi', 'hijriah': 'Hijriah', 'jawa': 'Jawa', 'saka': 'Saka'}[f]
        ket = {'jawa': ' Tahun Jawa berganti pada 1 Sura (1 Muharam).', 'hijriah': ' Tahun Hijriah berganti pada 1 Muharam.',
               'saka': ' Tahun Saka (pañcāṅga Jyotiṣa) mengikuti perhitungan lunisolar; pergantiannya di sekitar Maret–April.', 'masehi': ''}[f]
        txt = f"Tahun {nm} sekarang (**{_fmt_tgl(d)}**): **{nilai[f]}**.{ket}"
    else:
        txt = f"Tahun pada **{_fmt_tgl(d)}** dalam berbagai penanggalan:"
    baris = [['Masehi', nilai['masehi']], ['Hijriah', nilai['hijriah']], ['Jawa', nilai['jawa']], ['Saka', nilai['saka']]]
    return _r(txt, 'tahun', {'intent': 'tahun'}, [{'tipe': 'tabel', 'judul': 'Penanggalan', 'kolom': ['Kalender', 'Tahun'], 'baris': baris}],
              [{'teks': 'Lab Kalender', 'url': '/calendar/'}], ['calendar_service, hisab'], ['Weton hari ini berapa?', 'Tanggal hari ini'])


def _i_banding_salat(t, t_asli, ctx, hari_ini):
    if not re.search(r'\b(selisih|beda|perbedaan|bedanya|lebih awal|lebih cepat|lebih lambat|lebih akhir)\b', t):
        return None
    lokasi = cari_semua_lokasi(t_asli)
    if len(lokasi) < 2 or not re.search(r'\b(salat|imsak|subuh|zuhur|asar|magrib|isya|duha|terbit|waktu|jadwal)\b', t):
        return None
    for l in lokasi:
        if l['status'] == 'ambigu':
            return _r(f"Ada beberapa **{l['nama']}**: {', '.join(l['pilihan'])}. Sebutkan provinsinya.", 'lokasi_ambigu', suggestions=[f"{l['nama']} {p}" for p in l['pilihan']][:4])
    a, b = lokasi[0], lokasi[1]
    d, _ = _tgl_relatif(t, hari_ini)
    d = d or hari_ini
    minta = [WAKTU_SALAT[k] for k in dict.fromkeys(re.findall(r'\b(imsak|subuh|terbit|duha|zuhur|asar|magrib|isya)\b', t))]
    m = salat.METODE[ctx['metode']]
    def jad(e):
        lok = {'lat': e['lat'], 'lon': e['lon'], 'elev': e['elev'], 'tz': e['tz'], 'tz_label': tz_label(e['tz'])}
        return {x['kunci']: x for x in F.jadwal_salat(d, lok, m, ctx['ihtiyat'], ctx['imsak'])['waktu']}
    ja, jb = jad(a), jad(b)
    def detik(s):
        h, mi, *r = s.split(':')
        return int(h) * 3600 + int(mi) * 60 + (int(r[0]) if r else 0)
    kunci = minta or [k for k in ja if k != 'nisfuLail']
    baris = []
    for kk in kunci:
        ha, hb = ja[kk]['hisab']['jam'], jb[kk]['hisab']['jam']
        if not ha or not hb or ha == '-' or hb == '-':
            baris.append([ja[kk]['nama'], ha or '—', hb or '—', '—'])
            continue
        sel = (detik(hb) - detik(ha)) - int((b['tz'] - a['tz']) * 3600)         # selisih saat sebenarnya (UTC), bukan jam dinding
        baris.append([ja[kk]['nama'], ha, hb, f"{abs(sel) // 60:.0f} mnt {abs(sel) % 60:.0f} dtk, {b['nama']} {'lebih awal' if sel < 0 else 'lebih akhir'}" if sel else 'sama'])
    if len(minta) == 1 and baris[0][3] not in ('—', 'sama'):
        txt = f"Selisih **{ja[minta[0]]['nama']}** di **{a['nama']}** dan **{b['nama']}** pada {_fmt_tgl(d)}: **{baris[0][3].split(',')[0]}**; {baris[0][3].split(', ')[1]} dibanding {a['nama']}."
    else:
        txt = f"Perbandingan waktu salat **{a['nama']}** dan **{b['nama']}**, {_fmt_tgl(d)} (metode {m.name}; jam hisab sebelum ihtiyat):"
    if a['tz'] != b['tz']:
        txt += f"\n\nZona waktu berbeda ({tz_label(a['tz'])} dan {tz_label(b['tz'])}); selisih dihitung pada saat sebenarnya, sedangkan jam yang tertulis mengikuti zona masing-masing."
    return _r(txt, 'banding_salat', {'intent': 'banding_salat'},
              [{'tipe': 'tabel', 'judul': 'Perbandingan', 'kolom': ['Waktu', a['nama'], b['nama'], 'Selisih'], 'baris': baris}],
              [{'teks': 'Salat & Kiblat', 'url': '/islamic/'}], ['app/persis (hisab, tanpa ihtiyat)'], [f"Jadwal salat di {a['nama']}", f"Arah kiblat di {b['nama']}"])


KRIT_ART = {'mabims': 'kriteria-mabims', 'ummul': 'kriteria-ummul-qura', 'wujudul': 'wujudul-hilal', 'khgt': 'khgt'}


def _banding(t):
    ada = [k for k in KRIT_ART if re.search(rf'\b{k}\b', t)]
    if len(ada) >= 2 and re.search(r'\b(beda|bedanya|perbedaan|banding|dibanding|vs|versus)\b', t):
        b = basis()
        baris = [[KRIT_NAMA[KRIT_KATA[k]], b.artikel[KRIT_ART[k]]['ringkas']] for k in ada]
        return _r('Perbandingan singkat kriteria awal bulan Hijriah yang Anda tanyakan:', 'pengetahuan', {'intent': 'pengetahuan'},
                  [{'tipe': 'tabel', 'judul': 'Kriteria awal bulan', 'kolom': ['Kriteria', 'Prinsip'], 'baris': baris}],
                  [{'teks': 'Bandingkan kalender (tabel lengkap)', 'url': '/calendar/'}], ['Artikel kriteria awal bulan'],
                  ['Apa itu ' + KRIT_NAMA[KRIT_KATA[ada[0]]] + '?', 'Kapan 1 Ramadan 1448?'])
    return None


def _retrieval(q, ctx):
    hasil = basis().cari(q, 3)
    if not hasil or hasil[0][0] < 3.0:
        return _r('Maaf, saya belum menemukan jawaban yang pas untuk itu. Saya paling baik untuk **jadwal salat, kiblat, tanggal Hijriah/Jawa, puasa sunah**, dan konsep falak/astronomi. Coba rumuskan ulang, atau pilih salah satu di bawah.',
                  'tidak_paham', suggestions=SARAN_UMUM[:5])
    skor, a = hasil[0]
    b = basis()
    isi = b.potongan(a, q)
    txt = f"**{a['judul']}**\n\n{isi}"
    lain = [x for s, x in hasil[1:] if s >= max(3.0, skor * 0.55)]
    links = [{'teks': 'Baca artikel lengkap', 'url': f"/bot/?artikel={a['id']}"}]
    if a['tautan']:
        links.append({'teks': 'Buka fitur terkait', 'url': a['tautan']})
    return _r(txt, 'pengetahuan', {'intent': 'pengetahuan', 'artikel': a['id']}, [], links, [f"Artikel: {a['judul']}"],
              [f"{x['judul']}" for x in lain][:3] or SARAN_UMUM[:3])


def jawab(pesan: str, context: dict | None = None, slots: dict | None = None, sekarang_utc: datetime | None = None) -> dict:
    pesan = (pesan or '').strip()[:500]
    if not pesan:
        return _r('Mohon tuliskan pertanyaan Anda.', 'kosong', status='error')
    ctx = _ctx(context)
    slots = slots if isinstance(slots, dict) else {}
    now_utc = sekarang_utc or datetime.now(timezone.utc)
    now = now_utc + timedelta(hours=ctx['lok']['tz'])
    hari_ini = now.date()
    t = re.sub(r'\s+', ' ', ' '.join(re.findall(r"[a-z0-9'/\-]+", ' '.join(token(pesan, stem=False, buang_stop=False))))) if False else None
    toks = token(pesan, stem=False, buang_stop=False)
    t = ' '.join(toks)
    # pertahankan format tanggal ISO/angka-garis
    t = re.sub(r'\b(\d{4}) (\d{1,2}) (\d{1,2})\b', r'\1-\2-\3', t) if re.search(r'\d{4}-\d{1,2}-\d{1,2}', bersih(pesan)) else t
    if re.search(r'\d{4}-\d{1,2}-\d{1,2}', bersih(pesan)):
        t += ' ' + re.search(r'\d{4}-\d{1,2}-\d{1,2}', bersih(pesan)).group(0)
    kunci_lain = bool(re.search(r'\b(fase|cuaca|weton|neptu|observasi|rekomendasi|puasa|kiblat|rasydulkiblat|salat|jadwal|apa|kapan|hijriah|ramadan|syawal|bantuan|gerhana|meteor)\b', t))
    ada_lok = cari_lokasi(pesan) is not None
    pendek = (len(toks) <= 4 or (ada_lok and len(toks) <= 8)) and bool(slots.get('intent')) and not kunci_lain
    lanjut = pendek and bool(re.search(r'\b(besok|lusa|kemarin|kalau|bagaimana|gimana|di|untuk)\b', t) or cari_lokasi(pesan) or _tgl_relatif(t, hari_ini)[0])

    for fn in (_i_sapaan, _i_bantuan):
        r = fn(t)
        if r:
            return r
    konsep = bool(AWAL_KONSEP.search(t)) or (len(toks) >= 2 and toks[0] in ('apa', 'mengapa', 'kenapa', 'jelaskan') and not re.search(r'\bjam\b', t))
    if lanjut:
        asal = slots.get('intent')
        if asal == 'salat':
            r = _i_salat(t, pesan, ctx, slots, hari_ini, True)
            if r:
                return r
        if asal in ('cuaca', 'observasi'):
            f = _i_cuaca if asal == 'cuaca' else _i_observasi
            r = f(t + (' cuaca hari ini di' if asal == 'cuaca' else ' rekomendasi observasi langit'), pesan, ctx, slots, hari_ini, now_utc.replace(tzinfo=None), True)
            if r:
                return r
        if asal == 'kiblat':
            r = _i_kiblat(t + ' kiblat', pesan, ctx, slots, hari_ini, True)
            if r:
                return r
        if asal in ('konversi', 'hijri_ke_masehi'):
            d, label = _tgl_relatif(t, hari_ini)
            if d:
                return _ringkas_tanggal(d, ctx, 'tanggal', _awalan_rel(label, d, hari_ini))
    if not konsep:
        for fn in (lambda: _i_banding_salat(t, pesan, ctx, hari_ini), lambda: _i_gerhana(t, pesan, ctx, slots, now_utc),
                   lambda: _i_fase_berikut(t, ctx, now_utc), lambda: _i_tahun(t, ctx, hari_ini), lambda: _i_jumlah_hari(t, ctx, hari_ini), lambda: _i_cuaca(t, pesan, ctx, slots, hari_ini, now_utc.replace(tzinfo=None), False),
                   lambda: _i_observasi(t, pesan, ctx, slots, hari_ini, now_utc.replace(tzinfo=None), False), lambda: _i_weton(t, ctx, hari_ini),
                   lambda: _i_awal_bulan(t, ctx, hari_ini, slots), lambda: _i_kiblat(t, pesan, ctx, slots, hari_ini, False),
                   lambda: _i_salat(t, pesan, ctx, slots, hari_ini, False), lambda: _i_puasa(t, ctx, hari_ini),
                   lambda: _i_bulan(t, ctx, now_utc), lambda: _i_event(t), lambda: _i_konversi(t, ctx, hari_ini),
                   lambda: _i_hari_ini(t, ctx, hari_ini, now)):
            try:
                r = fn()
            except Exception as e:                      # satu intent gagal tidak boleh menjatuhkan seluruh bot
                r = _r(f'Maaf, terjadi kendala saat menghitung: {e}', 'galat', status='error')
            if r:
                return r
    return _banding(t) or _retrieval(pesan, ctx)
