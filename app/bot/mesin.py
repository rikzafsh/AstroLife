"""Mesin AstroBot. Alur: sapaan/bantuan → pertanyaan konsep (retrieval) → intent operasional (hitungan nyata) → retrieval cadangan.
Balasan: {status, reply, intent, slots, cards, links, sources, suggestions}. 'slots' dikembalikan ke klien dan dikirim lagi
pada pesan berikutnya agar pertanyaan lanjutan ('kalau di Surabaya?', 'besok?') memahami konteks."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .dasar import (
    AWAL_KONSEP,
    KRIT_KATA,
    KRIT_NAMA,
    SARAN_UMUM,
    awalan_relatif,
    baca_konteks,
    balas,
    tanggal_relatif,
)
from .intent_kalender import (
    intent_awal_bulan,
    intent_hari_ini,
    intent_jumlah_hari,
    intent_konversi,
    intent_puasa,
    intent_tahun,
    intent_weton,
    ringkas_tanggal,
)
from .intent_langit import (
    intent_bulan,
    intent_cuaca,
    intent_event,
    intent_fase_berikut,
    intent_gerhana,
    intent_observasi,
)
from .intent_salat import intent_banding_salat, intent_kiblat, intent_salat
from .kota import cari_lokasi
from .pengetahuan import basis
from .teks import bersih, token


def saran_awal() -> list[str]:
    return list(SARAN_UMUM)


def daftar_artikel() -> list[dict]:
    return [{'id': a['id'], 'judul': a['judul'], 'kategori': a['kategori'], 'ringkas': a['ringkas']} for a in basis().artikel.values()]


def ambil_artikel(aid: str) -> dict | None:
    a = basis().artikel.get(aid)
    return None if not a else {k: a[k] for k in ('id', 'judul', 'kategori', 'ringkas', 'isi', 'tautan', 'kata_kunci')}


def intent_sapaan(t):
    if re.fullmatch(r'\s*(halo|hai|hi|hello|assalamualaikum|assalamu\'alaikum|selamat (pagi|siang|sore|malam)|p|test|tes)\W*(astrobot|bot)?\W*', t):
        return balas('Halo! Saya **AstroBot**. Saya bisa menghitung jadwal salat, arah kiblat, tanggal Hijriah/Jawa, dan menjelaskan konsep falak serta astronomi. Mau mulai dari mana?',
                     'sapaan', suggestions=SARAN_UMUM[:5])
    if re.search(r'\b(terima kasih|makasih|thanks|thx|matur nuwun|jazakallah)\b', t):
        return balas('Sama-sama! Kalau ada yang ingin dihitung atau dijelaskan lagi, tanyakan saja.', 'terima_kasih', suggestions=SARAN_UMUM[:3])
    return None


def intent_bantuan(t):
    if re.search(r'\b(bantuan|help|panduan|menu|fitur|bisa (apa|ngapain)|apa saja yang bisa|kamu bisa|anda bisa)\b', t):
        return balas('Yang bisa saya bantu:\n- **Jadwal salat** (juga untuk kota lain/tanggal lain)\n- **Arah kiblat** dan **rasydulqiblat**\n- **Tanggal hari ini** (Masehi, Hijriah, Jawa, weton, wuku) dan **konversi tanggal**\n- **Awal bulan Hijriah** menurut kriteria yang Anda pilih\n- **Puasa sunah** dan hari penting\n- **Fase Bulan** malam ini\n- **Penjelasan konsep**: kriteria hilal, kalender Jawa, gerhana, hujan meteor, dan lainnya\n\nHasil hitungan memakai lokasi, metode salat, dan kriteria Hijriah dari menu **Pengaturan**.',
                     'bantuan', suggestions=SARAN_UMUM)
    return None


KRIT_ART = {'mabims': 'kriteria-mabims', 'ummul': 'kriteria-ummul-qura', 'wujudul': 'wujudul-hilal', 'khgt': 'khgt'}


def perbandingan_kriteria(t):
    ada = [k for k in KRIT_ART if re.search(rf'\b{k}\b', t)]
    if len(ada) >= 2 and re.search(r'\b(beda|bedanya|perbedaan|banding|dibanding|vs|versus)\b', t):
        b = basis()
        baris = [[KRIT_NAMA[KRIT_KATA[k]], b.artikel[KRIT_ART[k]]['ringkas']] for k in ada]
        return balas('Perbandingan singkat kriteria awal bulan Hijriah yang Anda tanyakan:', 'pengetahuan', {'intent': 'pengetahuan'},
                     [{'tipe': 'tabel', 'judul': 'Kriteria awal bulan', 'kolom': ['Kriteria', 'Prinsip'], 'baris': baris}],
                     [{'teks': 'Bandingkan kalender (tabel lengkap)', 'url': '/calendar/'}], ['Artikel kriteria awal bulan'],
                     ['Apa itu ' + KRIT_NAMA[KRIT_KATA[ada[0]]] + '?', 'Kapan 1 Ramadan 1448?'])
    return None


def jawab_retrieval(q, ctx):
    hasil = basis().cari(q, 3)
    if not hasil or hasil[0][0] < 3.0:
        return balas('Maaf, saya belum menemukan jawaban yang pas untuk itu. Saya paling baik untuk **jadwal salat, kiblat, tanggal Hijriah/Jawa, puasa sunah**, dan konsep falak/astronomi. Coba rumuskan ulang, atau pilih salah satu di bawah.',
                     'tidak_paham', suggestions=SARAN_UMUM[:5])
    skor, a = hasil[0]
    b = basis()
    isi = b.potongan(a, q)
    txt = f"**{a['judul']}**\n\n{isi}"
    lain = [x for s, x in hasil[1:] if s >= max(3.0, skor * 0.55)]
    links = [{'teks': 'Baca artikel lengkap', 'url': f"/bot/?artikel={a['id']}"}]
    if a['tautan']:
        links.append({'teks': 'Buka fitur terkait', 'url': a['tautan']})
    return balas(txt, 'pengetahuan', {'intent': 'pengetahuan', 'artikel': a['id']}, [], links, [f"Artikel: {a['judul']}"],
                 [f"{x['judul']}" for x in lain][:3] or SARAN_UMUM[:3])


_RE_TANGGAL_ISO = re.compile(r'\d{4}-\d{1,2}-\d{1,2}')
# kata kunci yang menandakan pertanyaan BARU (bukan lanjutan seperti "kalau di Surabaya?")
_KATA_TOPIK_BARU = re.compile(r'\b(fase|cuaca|weton|neptu|observasi|rekomendasi|puasa|kiblat|rasydulkiblat|salat|jadwal|apa|kapan|hijriah|'
                              r'ramadan|syawal|bantuan|gerhana|meteor)\b')
_KATA_LANJUTAN = re.compile(r'\b(besok|lusa|kemarin|kalau|bagaimana|gimana|di|untuk)\b')


def _normalisasi(pesan: str) -> tuple[list[str], str]:
    """Pesan -> (token, teks bersih). Tanggal ISO (2026-11-27) dipertahankan utuh karena tokenisasi memecahnya."""
    toks = token(pesan, stem=False, buang_stop=False)
    t = ' '.join(toks)
    iso = _RE_TANGGAL_ISO.search(bersih(pesan))
    if iso:
        t = re.sub(r'\b(\d{4}) (\d{1,2}) (\d{1,2})\b', r'\1-\2-\3', t) + ' ' + iso.group(0)
    return toks, t


def _apakah_lanjutan(toks, t, pesan, slots, hari_ini) -> bool:
    """Pesan pendek yang melanjutkan topik sebelumnya ('kalau di Surabaya?', 'besok?'). Syarat: ada topik di slots, pesan pendek,
    tidak memuat kata topik baru, dan memuat penanda lanjutan / lokasi / hari relatif."""
    if not slots.get('intent') or _KATA_TOPIK_BARU.search(t):
        return False
    lokasi = cari_lokasi(pesan)
    pendek = len(toks) <= 4 or (lokasi is not None and len(toks) <= 8)
    return pendek and bool(_KATA_LANJUTAN.search(t) or lokasi or tanggal_relatif(t, hari_ini)[0])


def _jawab_lanjutan(t, pesan, ctx, slots, hari_ini, now_utc):
    """Jawab pesan lanjutan dengan topik dari slots; None bila topik itu tidak bisa dilanjutkan (jatuh ke alur biasa)."""
    asal = slots.get('intent')
    naive_utc = now_utc.replace(tzinfo=None)
    if asal == 'salat':
        return intent_salat(t, pesan, ctx, slots, hari_ini, True)
    if asal == 'cuaca':
        return intent_cuaca(t + ' cuaca hari ini di', pesan, ctx, slots, hari_ini, naive_utc, True)
    if asal == 'observasi':
        return intent_observasi(t + ' rekomendasi observasi langit', pesan, ctx, slots, hari_ini, naive_utc, True)
    if asal == 'kiblat':
        return intent_kiblat(t + ' kiblat', pesan, ctx, slots, hari_ini, True)
    if asal in ('konversi', 'hijri_ke_masehi'):
        d, label = tanggal_relatif(t, hari_ini)
        if d:
            return ringkas_tanggal(d, ctx, 'tanggal', awalan_relatif(label, d, hari_ini))
    return None


def _urutan_intent(t, pesan, ctx, slots, hari_ini, now, now_utc):
    """Intent operasional dalam URUTAN PRIORITAS (yang lebih spesifik dulu). Tiap elemen dipanggil tanpa argumen;
    intent pertama yang menghasilkan balasan menang."""
    naive_utc = now_utc.replace(tzinfo=None)
    return [
        lambda: intent_banding_salat(t, pesan, ctx, hari_ini),
        lambda: intent_gerhana(t, pesan, ctx, slots, now_utc),
        lambda: intent_fase_berikut(t, ctx, now_utc),
        lambda: intent_tahun(t, ctx, hari_ini),
        lambda: intent_jumlah_hari(t, ctx, hari_ini),
        lambda: intent_cuaca(t, pesan, ctx, slots, hari_ini, naive_utc, False),
        lambda: intent_observasi(t, pesan, ctx, slots, hari_ini, naive_utc, False),
        lambda: intent_weton(t, ctx, hari_ini),
        lambda: intent_awal_bulan(t, ctx, hari_ini, slots),
        lambda: intent_kiblat(t, pesan, ctx, slots, hari_ini, False),
        lambda: intent_salat(t, pesan, ctx, slots, hari_ini, False),
        lambda: intent_puasa(t, ctx, hari_ini),
        lambda: intent_bulan(t, ctx, now_utc),
        lambda: intent_event(t),
        lambda: intent_konversi(t, ctx, hari_ini),
        lambda: intent_hari_ini(t, ctx, hari_ini, now),
    ]


def _pertanyaan_konsep(toks, t) -> bool:
    """'Apa itu ...', 'jelaskan ...': dijawab dari artikel (retrieval), bukan dari perhitungan."""
    return bool(AWAL_KONSEP.search(t)) or (len(toks) >= 2 and toks[0] in ('apa', 'mengapa', 'kenapa', 'jelaskan') and not re.search(r'\bjam\b', t))


def jawab(pesan: str, context: dict | None = None, slots: dict | None = None, sekarang_utc: datetime | None = None) -> dict:
    """Titik masuk AstroBot. Urutan: sapaan/bantuan -> pesan lanjutan -> (bila bukan konsep) intent operasional -> perbandingan kriteria
    -> retrieval artikel."""
    pesan = (pesan or '').strip()[:500]
    if not pesan:
        return balas('Mohon tuliskan pertanyaan Anda.', 'kosong', status='error')
    ctx = baca_konteks(context)
    slots = slots if isinstance(slots, dict) else {}
    now_utc = sekarang_utc or datetime.now(timezone.utc)
    now = now_utc + timedelta(hours=ctx['lok']['tz'])
    hari_ini = now.date()
    toks, t = _normalisasi(pesan)

    for sapa in (intent_sapaan, intent_bantuan):
        r = sapa(t)
        if r:
            return r
    if _apakah_lanjutan(toks, t, pesan, slots, hari_ini):
        r = _jawab_lanjutan(t, pesan, ctx, slots, hari_ini, now_utc)
        if r:
            return r
    if not _pertanyaan_konsep(toks, t):
        for coba in _urutan_intent(t, pesan, ctx, slots, hari_ini, now, now_utc):
            try:
                r = coba()
            except Exception as e:                      # satu intent gagal tidak boleh menjatuhkan seluruh bot
                r = balas(f'Maaf, terjadi kendala saat menghitung: {e}', 'galat', status='error')
            if r:
                return r
    return perbandingan_kriteria(t) or jawab_retrieval(pesan, ctx)
