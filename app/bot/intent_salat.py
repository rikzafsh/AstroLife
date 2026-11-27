"""Intent waktu salat & kiblat AstroBot: jadwal salat, arah kiblat/rasydulqiblat, dan perbandingan waktu salat antar-kota."""
from __future__ import annotations

import re
from datetime import date

from app.persis import salat
from app.services import falak_service as F
from app.services.timezones import tz_label

from .dasar import (
    WAKTU_SALAT,
    balas,
    format_tanggal,
    lokasi_dari_teks,
    slot_lokasi,
    tanggal_masehi,
    tanggal_relatif,
)
from .kota import cari_semua_lokasi


def intent_salat(t, t_asli, ctx, slots, hari_ini, lanjut):
    kata_salat = re.search(r'\b(salat|jadwal|imsak|subuh|zuhur|asar|magrib|isya|duha|terbit|waktu)\b', t)
    if not kata_salat and not (lanjut and slots.get('intent') == 'salat'):
        return None
    if re.search(r'\b(kiblat|rasydul|puasa|hijriah|kalender|konversi|fase|bulan)\b', t) and not re.search(r'\b(salat|jadwal)\b', t):
        return None
    if re.search(r'\bwaktu (yang )?(terbaik|tepat)\b|\bwaktu\b.*\b(pengamatan|observasi)\b', t):
        return None
    d, label = tanggal_relatif(t, hari_ini)
    tm = tanggal_masehi(t)
    if isinstance(tm, date):
        d = tm
    elif tm and tm[2] or (tm and tm[1]):
        try:
            d = date(tm[2] or hari_ini.year, tm[1], tm[0])
        except ValueError:
            return balas('Tanggal itu tidak valid. Coba tulis seperti "17 Agustus 2026".', 'salat', status='error')
    d = d or (date.fromisoformat(slots['tanggal']) if slots.get('tanggal') and lanjut else hari_ini)
    lok, nama, galat, rujuk = lokasi_dari_teks(t_asli, ctx, slots if lanjut else {})
    if galat:
        galat['slots'] = {'intent': 'salat', 'tanggal': d.isoformat()}
        return galat
    m = salat.METODE[ctx['metode']]
    try:
        j = F.jadwal_salat(d, lok, m, ctx['ihtiyat'], ctx['imsak'])
    except F.InputError as e:
        return balas(str(e), 'salat', status='error')
    rows = {x['kunci']: x for x in j['waktu']}
    minta = [WAKTU_SALAT[k] for k in re.findall(r'\b(imsak|subuh|terbit|duha|zuhur|asar|magrib|isya)\b', t)]
    slot = {'intent': 'salat', 'tanggal': d.isoformat(), **slot_lokasi(lok, nama, rujuk)}
    judul = f"{nama}, {format_tanggal(d)}"
    if len(minta) == 1:
        x = rows[minta[0]]['jadwal']
        isi = x['jam'] or '—'
        ket = f" ({x['keterangan']})" if x['keterangan'] else ''
        txt = f"**{rows[minta[0]]['nama']}** di {nama}, {format_tanggal(d)}: **{isi} {lok['tz_label']}**{ket}.\nMetode {m.name}, ihtiyat {ctx['ihtiyat']} menit."
        kartu = []
    else:
        txt = f"Jadwal salat **{nama}**, {format_tanggal(d)} ({lok['tz_label']}), metode **{m.name}**, ihtiyat {ctx['ihtiyat']} menit:"
        kartu = [{'tipe': 'tabel', 'judul': judul, 'kolom': ['Waktu', 'Jam'],
                  'baris': [[x['nama'], x['jadwal']['jam'] or '—'] for x in j['waktu'] if x['kunci'] != 'nisfuLail']}]
    if rujuk:
        txt += '\n\n' + rujuk
    if j.get('ramadan'):
        txt += '\n\nTanggal ini terdeteksi masuk **Ramadan** menurut Ummul Qura untuk penyesuaian Isya.'
    return balas(txt, 'salat', slot, kartu, [{'teks': 'Buka Salat & Kiblat', 'url': '/islamic/'}], ['Perhitungan: app/persis (port persis-times-js)'],
                 ['Besok?', 'Kalau di Surabaya?', 'Arah kiblat dari sini', 'Apa itu ihtiyat?'])


def intent_kiblat(t, t_asli, ctx, slots, hari_ini, lanjut):
    if not re.search(r'\b(kiblat|rasydulkiblat)\b', t):
        return None
    lok, nama, galat, rujuk = lokasi_dari_teks(t_asli, ctx, slots if lanjut else {})
    if galat:
        galat['slots'] = {'intent': 'kiblat'}
        return galat
    if re.search(r'\brasydulkiblat\b', t) or re.search(r'\bbayangan\b', t):
        try:
            r = F.rasydulqiblat(hari_ini, lok, 'vincenty', 7, hari_ini.year, 1)
        except Exception as e:
            return balas(f'Maaf, gagal menghitung rasydulqiblat: {e}', 'rasydulqiblat', status='error')
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
            return balas('Data rasydulqiblat tidak tersedia untuk lokasi ini. Buka halaman Salat & Kiblat untuk detailnya.', 'rasydulqiblat',
                         links=[{'teks': 'Buka Salat & Kiblat', 'url': '/islamic/'}])
        return balas(f'Rasydulqiblat **tahunan** untuk **{nama}** tahun {hari_ini.year} (saat bayangan benda tegak menunjuk arah kiblat):',
                     'rasydulqiblat', {'intent': 'kiblat', **slot_lokasi(lok, nama, rujuk)},
                     [{'tipe': 'tabel', 'judul': f'Rasydulqiblat {nama}', 'kolom': ['Peristiwa', 'Tanggal', 'Jam'], 'baris': baris}],
                     [{'teks': 'Rasydulqiblat & kompas', 'url': '/islamic/'}], ['app/persis/kiblat'], ['Apa itu rasydulqiblat?', 'Arah kiblat di Medan'])
    k = F.info_kiblat(lok)
    v = k['vincenty']
    jarak = f"{k['jarak_km']:,.0f}".replace(',', '.')
    txt = (f"Arah kiblat dari **{nama}**: **{v['dms']}** dari utara searah jarum jam (**{v['derajat']:.2f}°**, arah **{k['mata_angin']}**).\n"
           f"Jarak ke Ka'bah ±{jarak} km.\nModel bola: {k['bola']['dms']}; elipsoid: {k['elipsoid']['dms']}." + (f"\n\n{rujuk}" if rujuk else ''))
    return balas(txt, 'kiblat', {'intent': 'kiblat', **slot_lokasi(lok, nama, rujuk)}, [],
                 [{'teks': 'Kompas kiblat & peta', 'url': '/islamic/'}], ['app/persis/kiblat (Vincenty)'],
                 ['Rasydulqiblat tahun ini', 'Kalau di Medan?', 'Cara menghitung arah kiblat'])


def intent_banding_salat(t, t_asli, ctx, hari_ini):
    if not re.search(r'\b(selisih|beda|perbedaan|bedanya|lebih awal|lebih cepat|lebih lambat|lebih akhir)\b', t):
        return None
    lokasi = cari_semua_lokasi(t_asli)
    if len(lokasi) < 2 or not re.search(r'\b(salat|imsak|subuh|zuhur|asar|magrib|isya|duha|terbit|waktu|jadwal)\b', t):
        return None
    for l in lokasi:
        if l['status'] == 'ambigu':
            return balas(f"Ada beberapa **{l['nama']}**: {', '.join(l['pilihan'])}. Sebutkan provinsinya.", 'lokasi_ambigu', suggestions=[f"{l['nama']} {p}" for p in l['pilihan']][:4])
    a, b = lokasi[0], lokasi[1]
    d, _ = tanggal_relatif(t, hari_ini)
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
        txt = f"Selisih **{ja[minta[0]]['nama']}** di **{a['nama']}** dan **{b['nama']}** pada {format_tanggal(d)}: **{baris[0][3].split(',')[0]}**; {baris[0][3].split(', ')[1]} dibanding {a['nama']}."
    else:
        txt = f"Perbandingan waktu salat **{a['nama']}** dan **{b['nama']}**, {format_tanggal(d)} (metode {m.name}; jam hisab sebelum ihtiyat):"
    if a['tz'] != b['tz']:
        txt += f"\n\nZona waktu berbeda ({tz_label(a['tz'])} dan {tz_label(b['tz'])}); selisih dihitung pada saat sebenarnya, sedangkan jam yang tertulis mengikuti zona masing-masing."
    return balas(txt, 'banding_salat', {'intent': 'banding_salat'},
                 [{'tipe': 'tabel', 'judul': 'Perbandingan', 'kolom': ['Waktu', a['nama'], b['nama'], 'Selisih'], 'baris': baris}],
                 [{'teks': 'Salat & Kiblat', 'url': '/islamic/'}], ['app/persis (hisab, tanpa ihtiyat)'], [f"Jadwal salat di {a['nama']}", f"Arah kiblat di {b['nama']}"])
