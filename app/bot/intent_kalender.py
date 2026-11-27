"""Intent kalender AstroBot: tanggal hari ini, konversi Masehi↔Hijriah↔Jawa, awal bulan Hijriah, jumlah hari bulan, weton, tahun Jawa/Saka/Hijriah, puasa."""
from __future__ import annotations

import re
from datetime import date

from app.services import calendar_service as cs
from app.services import falak_service as F
from app.services import islamic_service as isl

from .dasar import (
    BULAN_ID_NAMA,
    HIJRI_NAMA,
    KRIT_NAMA,
    awalan_relatif,
    balas,
    cari_masehi,
    format_tanggal,
    hijri_dalam,
    jdn_dari,
    kriteria_dalam,
    tanggal_masehi,
    tanggal_relatif,
)


def intent_puasa(t, ctx, hari_ini):
    if not re.search(r'\b(puasa|ayyamulbid|tasua|asyura|arafah|hari penting|tanggal penting)\b', t):
        return None
    hari = 45 if re.search(r'\b(45|bulan|sebulan)\b', t) else 14 if re.search(r'\b(minggu|pekan|seminggu)\b', t) else 30
    try:
        rows = isl.fasting_schedule(hari_ini, hari, ctx['krit'])
    except Exception as e:
        return balas(f'Maaf, jadwal puasa tidak dapat dihitung: {e}', 'puasa', status='error')
    if not rows:
        return balas(f'Tidak ada puasa sunah atau hari penting dalam {hari} hari ke depan menurut kriteria {KRIT_NAMA[ctx["krit"]]}.', 'puasa')
    baris = [[f"{r['hari']}, {r['tanggal'][8:]}/{r['tanggal'][5:7]}", r['hijriah'], r['peristiwa'] or r['keterangan']] for r in rows[:14]]
    return balas(f"Puasa sunah dan hari penting **{hari} hari ke depan** (kalender Hijriah **{KRIT_NAMA[ctx['krit']]}**):", 'puasa',
                 {'intent': 'puasa'}, [{'tipe': 'tabel', 'judul': 'Puasa & hari penting', 'kolom': ['Hari', 'Hijriah', 'Keterangan'], 'baris': baris}],
                 [{'teks': 'Selengkapnya', 'url': '/islamic/'}], ['islamic_service.fasting_schedule'], ['Apa saja puasa sunah?', 'Kapan 1 Ramadan 1448?'])


def intent_awal_bulan(t, ctx, hari_ini, sl):
    h = hijri_dalam(t)
    if not h or not re.search(r'\b(kapan|tanggal berapa|jatuh|awal|masehi|berapa|mulai|1|satu)\b', t):
        return None
    bln, tgl, thn = h
    krit = kriteria_dalam(t) or ctx['krit']
    if thn is None:
        # tahun Hijriah berikutnya dari hari ini
        jdn = jdn_dari(hari_ini)
        try:
            thn_now = isl.hijri_menurut(jdn, krit)['tahun']
            b_now = isl.hijri_menurut(jdn, krit)['bulan']
        except Exception:
            thn_now, b_now = cs.hijri_info(jdn)['tahun'], cs.hijri_info(jdn)['bulan']
        thn = thn_now if bln >= b_now else thn_now + 1
    tg = tgl or 1
    if not 1 <= tg <= 30 or not 1300 <= thn <= 1800:
        return balas('Tahun Hijriah di luar rentang yang saya dukung (1300–1800 H) atau tanggal tidak valid.', 'hijri_ke_masehi', status='error')
    d = cari_masehi(tg, bln, thn, krit)
    if not d:
        return balas(f'Tanggal {tg} {HIJRI_NAMA[bln]} {thn} H tidak ditemukan menurut kriteria {KRIT_NAMA[krit]} (kriteria hisab hanya berlaku 1700–2300 M atau tanggal itu tidak ada).', 'hijri_ke_masehi', status='error')
    txt = f"**{tg} {HIJRI_NAMA[bln]} {thn} H** jatuh pada **{format_tanggal(d)}** menurut kriteria **{KRIT_NAMA[krit]}**."
    # tabel pembanding: tanggal yang sama menurut kelima kriteria
    baris = []
    for kk in ('aritmetis', 'mabims', 'ummulqura', 'wujudulhilal', 'turki'):
        dd = cari_masehi(tg, bln, thn, kk)
        baris.append([KRIT_NAMA[kk], format_tanggal(dd) if dd else '—'])
    kartu = [{'tipe': 'tabel', 'judul': f'{tg} {HIJRI_NAMA[bln]} {thn} H menurut kriteria', 'kolom': ['Kriteria', 'Tanggal Masehi'], 'baris': baris}]
    txt += '\n\nIni hasil hisab, **bukan penetapan resmi** (sidang isbat). Dapat berbeda 1–2 hari.'
    return balas(txt, 'hijri_ke_masehi', {'intent': 'hijri_ke_masehi', 'bulan': bln, 'tgl': tg, 'tahun': thn}, kartu,
                 [{'teks': 'Bandingkan kalender', 'url': '/calendar/'}], ['app/persis/hisab'], ['Apa beda kriteria MABIMS dan Ummul Qura?', 'Kapan 1 Syawal ' + str(thn) + '?'])


def intent_konversi(t, ctx, hari_ini):
    tm = tanggal_masehi(t)
    if tm is None or isinstance(tm, date) is False and tm[2] is None and not re.search(r'\b(hijriah|jawa|weton|konversi|tanggal)\b', t):
        return None
    if isinstance(tm, date):
        d = tm
    else:
        try:
            d = date(tm[2] or hari_ini.year, tm[1], tm[0])
        except ValueError:
            return balas('Tanggal itu tidak valid. Coba tulis seperti "17 Agustus 2026".', 'konversi', status='error')
    return ringkas_tanggal(d, ctx, 'konversi')


def ringkas_tanggal(d: date, ctx, intent, awalan=''):
    jdn = jdn_dari(d)
    try:
        j = cs.javanese_info(jdn)
        hij = isl.hijri_menurut(jdn, ctx['krit'])
    except Exception as e:
        return balas(f'Maaf, gagal menghitung tanggal itu: {e}', intent, status='error')
    baris = [['Masehi', format_tanggal(d)], [f"Hijriah ({KRIT_NAMA[ctx['krit']]})", hij['teks']],
             ['Jawa Mataraman', f"{j['tanggal']} {j['bulan']} {j['tahun_windu']} {j['tahun']} AJ"], ['Weton', j['weton']], ['Wuku', j['wuku']]]
    return balas(f"{awalan}Tanggal **{format_tanggal(d)}** dalam berbagai kalender:", intent, {'intent': 'konversi', 'tanggal': d.isoformat()},
                 [{'tipe': 'tabel', 'judul': 'Padanan tanggal', 'kolom': ['Kalender', 'Tanggal'], 'baris': baris}],
                 [{'teks': 'Lab Kalender', 'url': '/calendar/'}], ['calendar_service, hisab'], ['Besok?', 'Kapan 1 Ramadan 1448?'])


def intent_hari_ini(t, ctx, hari_ini, now):
    if not re.search(r'\b(tanggal|hari apa|weton|wuku|pasaran|kalender|hijriah|jawa)\b', t) or re.search(r'\b(salat|jadwal|puasa|cuaca)\b', t):
        return None
    d, label = tanggal_relatif(t, hari_ini)
    if d is None and re.search(r'\b(hari ini|tanggal|weton|hari apa|pasaran)\b', t):
        d = hari_ini
    return ringkas_tanggal(d, ctx, 'tanggal', awalan_relatif(label, d, hari_ini)) if d else None


def intent_weton(t, ctx, hari_ini):
    if not re.search(r'\b(weton|neptu|pasaran|wuku|pawukon)\b', t):
        return None
    d, _ = tanggal_relatif(t, hari_ini)
    tm = tanggal_masehi(t)
    if isinstance(tm, date):
        d = tm
    elif tm:
        try:
            d = date(tm[2] or hari_ini.year, tm[1], tm[0])
        except ValueError:
            return balas('Tanggal itu tidak valid. Coba tulis seperti "17 Agustus 2026".', 'weton', status='error')
    d = d or hari_ini
    j = cs.javanese_info(jdn_dari(d))
    txt = (f"Weton **{format_tanggal(d)}** adalah **{j['weton']}**, neptu **{j['neptu']}** ({j['neptu_rincian']}).\n"
           f"Pawukon: {j['hari']} {j['pasaran']} {j['sadwara']} {j['wuku']} (wuku ke-{j['wuku_no']}, hari ke-{j['hari_pawukon']} dari 210).\n"
           f"Tanggal Jawa Mataraman: {j['tanggal']} {j['bulan']} {j['tahun_windu']} {j['tahun']} AJ.")
    return balas(txt, 'weton', {'intent': 'konversi', 'tanggal': d.isoformat()}, [], [{'teks': 'Lab Kalender', 'url': '/calendar/'}],
                 ['calendar_service (neptu, pawukon)'], ['Besok?', 'Apa itu weton?', 'Apa itu pawukon?'])


def intent_jumlah_hari(t, ctx, hari_ini):
    h = hijri_dalam(t)
    if not h or not re.search(r'\b(jumlah hari|berapa hari|panjang|umur bulan|lama bulan|berapa lama)\b', t):
        return None
    bln, _, thn = h
    if thn is None:
        jdn = jdn_dari(hari_ini)
        try:
            now_h = isl.hijri_menurut(jdn, ctx['krit'])
        except Exception:
            now_h = cs.hijri_info(jdn)
        thn = now_h['tahun'] if bln >= now_h['bulan'] else now_h['tahun'] + 1
    if not 1300 <= thn <= 1800:
        return balas('Tahun Hijriah di luar rentang yang saya dukung (1300–1800 H).', 'jumlah_hari', status='error')
    nb, nt = (bln + 1, thn) if bln < 12 else (1, thn + 1)
    baris, hasil = [], {}
    for kk in ('aritmetis', 'mabims', 'ummulqura', 'wujudulhilal', 'turki'):
        a, b = cari_masehi(1, bln, thn, kk), cari_masehi(1, nb, nt, kk)
        n = (b - a).days if a and b else None
        hasil[kk] = n
        baris.append([KRIT_NAMA[kk], f"{a.day} {BULAN_ID_NAMA[a.month]} {a.year}" if a else '—', f"{b.day} {BULAN_ID_NAMA[b.month]} {b.year}" if b else '—',
                      f'{n} hari' if n else '—'])
    krit = kriteria_dalam(t) or ctx['krit']
    n0 = hasil.get(krit)
    asal = '' if kriteria_dalam(t) else ' (pilihan di Pengaturan)'
    awal = f"**{HIJRI_NAMA[bln]} {thn} H** berumur **{n0} hari** menurut kriteria **{KRIT_NAMA[krit]}**{asal}." if n0 else \
        f"Umur **{HIJRI_NAMA[bln]} {thn} H** menurut kriteria {KRIT_NAMA[krit]} tidak dapat dihitung (di luar jangkauan hisab)."
    nilai = {v for v in hasil.values() if v}
    ket = '\n\nUmur bulan Hijriah selalu 29 atau 30 hari.'
    if len(nilai) > 1:
        ket += ' Umurnya berbeda antarkriteria karena awal bulan berikutnya berbeda (lihat tabel).'
    ket += ' Ini hasil hisab, **bukan penetapan resmi** (sidang isbat).'
    return balas(awal + ket, 'jumlah_hari', {'intent': 'jumlah_hari'},
                 [{'tipe': 'tabel', 'judul': f'Umur {HIJRI_NAMA[bln]} {thn} H per kriteria', 'kolom': ['Kriteria', f'1 {HIJRI_NAMA[bln]}', f'1 {HIJRI_NAMA[nb]}', 'Umur'], 'baris': baris}],
                 [{'teks': 'Bandingkan kalender', 'url': '/calendar/'}], ['app/persis/hisab'], [f'Kapan 1 {HIJRI_NAMA[bln]} {thn}?', 'Apa beda MABIMS dan Ummul Qura?'])


def intent_tahun(t, ctx, hari_ini):
    if not re.search(r'\btahun\b', t) or not re.search(r'\b(sekarang|ini|saat ini|berapa)\b', t) or re.search(r'\b(kabisat|depan|lalu|kemarin|besok|kiblat|rasydulkiblat|salat|puasa|jadwal|gerhana|meteor|cuaca|ramadan|syawal)\b', t):
        return None
    if not re.search(r'\b(saka|jyotisa|hindu|jawa|aj|mataram|hijriah|hijri|islam|masehi)\b|tahun berapa', t):
        return None
    d, _ = tanggal_relatif(t, hari_ini)
    d = d or hari_ini
    jdn = jdn_dari(d)
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
        txt = f"Tahun {nm} sekarang (**{format_tanggal(d)}**): **{nilai[f]}**.{ket}"
    else:
        txt = f"Tahun pada **{format_tanggal(d)}** dalam berbagai penanggalan:"
    baris = [['Masehi', nilai['masehi']], ['Hijriah', nilai['hijriah']], ['Jawa', nilai['jawa']], ['Saka', nilai['saka']]]
    return balas(txt, 'tahun', {'intent': 'tahun'}, [{'tipe': 'tabel', 'judul': 'Penanggalan', 'kolom': ['Kalender', 'Tahun'], 'baris': baris}],
                 [{'teks': 'Lab Kalender', 'url': '/calendar/'}], ['calendar_service, hisab'], ['Weton hari ini berapa?', 'Tanggal hari ini'])
