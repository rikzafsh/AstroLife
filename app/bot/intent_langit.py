"""Intent langit AstroBot: fase Bulan, gerhana, event katalog, cuaca, dan rekomendasi observasi. Cuaca/gerhana memakai layanan aplikasi
(Open-Meteo bila tersedia; bila tidak, balasan menyatakannya, bukan mengarang)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.services.home_service import today_summary
from app.services.timezones import tz_label

from . import cuaca as cu
from .dasar import BULAN_ID_NAMA, HARI_ID, balas, lokasi_dari_teks, slot_lokasi


def intent_bulan(t, ctx, now_utc):
    if not re.search(r'\b(fase bulan|bulan purnama|purnama|bulan sabit|umur bulan|bulan malam ini|bulan hari ini|bentuk bulan)\b', t):
        return None
    if re.search(r'\b(kapan|jadwal)\b', t):
        return None
    s = today_summary(now_utc, ctx['lok']['tz'])
    b = s['bulan']
    return balas(f"Malam ini Bulan berada pada fase **{b['fase']}** {b['emoji']} dengan penerangan ±**{b['terang_pct']}%**, umur ±{b['umur_hari']} hari ({b['arah']}).",
                 'fase_bulan', {'intent': 'fase_bulan'}, [], [{'teks': 'Beranda', 'url': '/'}], ['home_service.today_summary'],
                 ['Apa itu fase bulan?', 'Tanggal hari ini'])


def intent_event(t):
    if re.search(r'\b(gerhana|meteor|konjungsi|oposisi|event|peristiwa langit|fenomena)\b', t) and re.search(r'\b(kapan|mendatang|bulan depan|minggu ini|terdekat|akan)\b', t):
        return balas('Daftar peristiwa langit mendatang (gerhana, konjungsi, hujan meteor, dan lainnya) dihitung per lokasi di **Katalog Event**. Bangun katalog sekali, lalu semua event dinilai keterlihatannya dari lokasi Anda.',
                     'event', links=[{'teks': 'Buka Katalog Event', 'url': '/catalog/'}], suggestions=['Apa itu hujan meteor?', 'Kenapa gerhana tidak terjadi tiap bulan?'])
    return None


def intent_cuaca(t, t_asli, ctx, slots, hari_ini, now_utc, lanjut):
    if not re.search(r'\b(cuaca|hujan|mendung|cerah|berawan|awan|suhu|panas|dingin|gerimis)\b', t) or re.search(r'\b(meteor|skor|kelayakan)\b', t):
        return None
    if not re.search(r'\b(hari ini|sekarang|nanti|malam ini|sore ini|pagi ini|siang ini|di|tempat|tempatku|sini|lokasi|besok)\b', t):
        return None
    lok, nama, galat, rujuk = lokasi_dari_teks(t_asli, ctx, slots if lanjut else {})
    if galat:
        galat['slots'] = {'intent': 'cuaca'}
        return galat
    if re.search(r'\bbesok\b', t):
        return balas('Untuk saat ini saya hanya meringkas cuaca **hari ini**. Prakiraan beberapa hari ke depan ada di halaman **Observasi**.', 'cuaca',
                     {'intent': 'cuaca', **slot_lokasi(lok, nama, rujuk)}, links=[{'teks': 'Buka Observasi', 'url': '/observation/'}])
    c = cu.cuaca_hari_ini(lok['lat'], lok['lon'], now_utc)
    slot = {'intent': 'cuaca', **slot_lokasi(lok, nama, rujuk)}
    if not c:
        return balas(f"Maaf, layanan prakiraan cuaca (Open-Meteo) tidak dapat dihubungi dari server saat ini, jadi saya tidak dapat menampilkan cuaca **{nama}**. "
                     "Saya tidak menebak. Coba lagi beberapa saat lagi.", 'cuaca', slot, links=[{'teks': 'Buka Observasi', 'url': '/observation/'}], sources=['Open-Meteo'])
    fmt = lambda x, d='': '—' if x is None else f'{x:.0f}{d}'
    baris = [[f"{b['nama']} ({b['rentang']})", b['kondisi'], fmt(b['awan'], '%'), fmt(b['hujan'], '%'), fmt(b['suhu'], '°C')] for b in c['blok']]
    k = c['sekarang']
    awal = f"Cuaca **{nama}** hari ini ({c['tanggal']}, pukul {c['jam_lokal']} waktu setempat)"
    if k:
        awal += f": sekarang **{W_label(k)}**, awan {fmt(k['cloud_cover_pct'], '%')}, suhu {fmt(k['temp_c'], '°C')}, kelembapan {fmt(k['humidity_pct'], '%')}."
    else:
        awal += ':'
    return balas(awal + ('\n\n' + rujuk if rujuk else ''), 'cuaca', slot,
                 [{'tipe': 'tabel', 'judul': 'Prakiraan per bagian hari', 'kolom': ['Waktu', 'Kondisi', 'Awan', 'Peluang hujan', 'Suhu'], 'baris': baris}],
                 [{'teks': 'Observasi & skor langit', 'url': '/observation/'}], ['Open-Meteo (prakiraan per jam)'],
                 ['Rekomendasi observasi langit minggu ini', 'Kalau di Surabaya?'])


def W_label(row):
    from app.services.weather_service import _condition_label
    return _condition_label(row.get('cloud_cover_pct'), row.get('precipitation_prob'))


def intent_observasi(t, t_asli, ctx, slots, hari_ini, now_utc, lanjut):
    if not (re.search(r'\b(rekomendasi|saran|sebaiknya|terbaik|bagus|cocok|layak)\b', t) and re.search(r'\b(observasi|amati|mengamati|pengamatan|langit|bintang|stargazing)\b', t)):
        return None
    lok, nama, galat, rujuk = lokasi_dari_teks(t_asli, ctx, slots if lanjut else {})
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
    kartu = [{'tipe': 'tabel', 'judul': "Malam-malam ke depan (pukul 20.00 waktu setempat)", 'kolom': ['Malam', 'Bulan', 'Cuaca', 'Skor'], 'baris': baris}]
    ev = cu.event_katalog(lok['lat'], lok['lon'], lok['tz'], now_utc, 7, 5) if n > 1 else None
    if ev and ev.get('items'):
        kartu.append({'tipe': 'tabel', 'judul': 'Event katalog yang dapat diamati', 'kolom': ['Event', 'Waktu terbaik', 'Skor'],
                      'baris': [[i['title'], i['best_local'], '—' if i['score'] is None else f"{i['score']:.0f}"] for i in ev['items']]})
    else:
        teks += '\n\nUntuk event spesifik (gerhana, konjungsi, hujan meteor) bangun dulu **Katalog Event**.'
    return balas(teks, 'observasi', {'intent': 'observasi', **slot_lokasi(lok, nama, rujuk)}, kartu,
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


def intent_fase_berikut(t, ctx, now_utc):
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
    return balas(txt, 'fase_berikut', {'intent': 'fase_berikut'}, [{'tipe': 'tabel', 'judul': 'Fase Bulan berikutnya', 'kolom': ['Fase', 'Waktu'], 'baris': baris}],
                 [{'teks': 'Beranda', 'url': '/'}], ['prototype.find_events (mesin Bulan katalog)'], ['Kapan gerhana matahari terdekat?', 'Kapan 1 Ramadan 1448?'])


def intent_gerhana(t, t_asli, ctx, slots, now_utc):
    if not re.search(r'\bgerhana\b', t) or not re.search(r'\b(kapan|terdekat|berikutnya|selanjutnya|mendatang|akan datang|nanti)\b', t):
        return None
    jenis = 'matahari' if re.search(r'\bmatahari\b', t) else 'bulan' if re.search(r'\bbulan\b', t) else 'semua'
    lok, nama, galat, rujuk = lokasi_dari_teks(t_asli, ctx, {})
    if galat:
        return galat
    from catalog import events as C
    from catalog import service as S
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
        return balas('Tidak ada gerhana yang ditemukan dalam 6 tahun ke depan.', 'gerhana')
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
    return balas(txt + (('\n\n' + rujuk) if rujuk else ''), 'gerhana', {'intent': 'gerhana', **slot_lokasi(lok, nama, rujuk)},
                 [{'tipe': 'tabel', 'judul': f'{label} 6 tahun ke depan (dari {nama})', 'kolom': ['Gerhana', f'Puncak ({tz_label(tz)})', 'Dari lokasi'], 'baris': baris}],
                 [{'teks': 'Katalog Event', 'url': '/catalog/'}], ['catalog.events (mesin Bulan/Matahari)'], ['Apakah gerhana berbahaya dilihat?', 'Kenapa gerhana tidak terjadi tiap bulan?'])
