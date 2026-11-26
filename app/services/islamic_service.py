"""
Kalender Islam praktis: tanggal penting dan rekomendasi puasa sunah (Hijriah aritmetis).

Waktu salat, arah kiblat, dan rasydulqiblat sekarang dihitung oleh app/persis (port persis-times-js) lewat
app/services/falak_service.py; fungsi lama di berkas ini yang menghitungnya sendiri sudah dihapus.
Hijriah di sini aritmetis (hisab urfi) dan dapat berbeda 1-2 hari dari penetapan resmi.
"""
from datetime import date, timedelta

from app.services import astro_core as ac
from app.services import calendar_service as cs


# ---------------------------------------------------------------------------
# Kalender Islam: tanggal penting dan puasa sunah
# ---------------------------------------------------------------------------
IMPORTANT_DATES = {
    (1, 1): 'Tahun Baru Islam 1 Muharram',
    (1, 10): "Hari Asyura (10 Muharram)",
    (3, 12): 'Maulid Nabi Muhammad SAW',
    (7, 27): "Isra Mi'raj",
    (8, 15): 'Nisfu Syaban',
    (9, 1): 'Awal Ramadan',
    (9, 17): 'Nuzulul Quran',
    (10, 1): 'Idulfitri 1 Syawal',
    (12, 9): 'Hari Arafah',
    (12, 10): 'Iduladha 10 Zulhijah',
}


def fasting_info(jdn: int) -> dict:
    """Status puasa untuk satu hari: wajib, haram, atau daftar puasa sunah yang berlaku."""
    y, m, d = cs.jdn_to_hijri(jdn)
    wd = ac.weekday_index(jdn)
    out = {'wajib': False, 'haram': None, 'sunah': []}
    if m == 9:
        out['wajib'] = True
        return out
    if (m, d) == (10, 1):
        out['haram'] = 'Hari Raya Idulfitri'
        return out
    if m == 12 and d in (10, 11, 12, 13):
        out['haram'] = 'Iduladha' if d == 10 else 'Hari Tasyrik'
        return out
    if wd == 1:
        out['sunah'].append('Senin')
    if wd == 4:
        out['sunah'].append('Kamis')
    if d in (13, 14, 15):
        out['sunah'].append('Ayyamul Bidh')
    if m == 12 and d == 9:
        out['sunah'].append('Arafah')
    if m == 1 and d in (9, 10):
        out['sunah'].append('Tasua' if d == 9 else 'Asyura')
    if m == 10 and 2 <= d <= 30:
        out['sunah'].append('Syawal (6 hari)')
    if m == 8 and d == 15:
        out['sunah'].append('Nisfu Syaban')
    return out


FASTING_NOTES = {
    'Senin': 'Puasa Senin: hari kelahiran dan awal wahyu Nabi SAW.',
    'Kamis': 'Puasa Kamis: hari diangkatnya amal.',
    'Ayyamul Bidh': 'Puasa 13, 14, 15 setiap bulan Hijriah (hari-hari Bulan purnama).',
    'Arafah': 'Puasa Arafah (9 Zulhijah) bagi yang tidak sedang berhaji.',
    'Tasua': 'Puasa Tasua (9 Muharram).',
    'Asyura': 'Puasa Asyura (10 Muharram).',
    'Syawal (6 hari)': 'Puasa enam hari di bulan Syawal setelah 1 Syawal (boleh berurutan/tidak).',
    'Nisfu Syaban': 'Sebagian ulama menganjurkan; termasuk Ayyamul Bidh bulan Syaban.',
}


def fasting_schedule(start: date, days: int = 30) -> list:
    rows = []
    for i in range(days):
        d = start + timedelta(days=i)
        jdn = ac.to_jdn(d.year, d.month, d.day)
        f = fasting_info(jdn)
        h = cs.hijri_info(jdn)
        evt = IMPORTANT_DATES.get((h['bulan'], h['tanggal']))
        if f['sunah'] or f['wajib'] or f['haram'] or evt:
            rows.append({
                'tanggal': d.isoformat(),
                'hari': cs.HARI[ac.weekday_index(jdn)],
                'hijriah': h['teks'],
                'status': 'wajib' if f['wajib'] else ('haram' if f['haram'] else 'sunah'),
                'jenis': f['sunah'],
                'keterangan': 'Puasa Ramadan (wajib)' if f['wajib'] else (f['haram'] and f"Dilarang berpuasa: {f['haram']}")
                              or '; '.join(FASTING_NOTES[x] for x in f['sunah']),
                'peristiwa': evt,
            })
    return rows


def hijri_calendar_month(year: int, month: int) -> dict:
    """Satu bulan Hijriah penuh (untuk tampilan kalender) dengan padanan Masehi."""
    if not 1 <= month <= 12:
        raise ValueError('Bulan Hijriah tidak valid.')
    n = cs.hijri_month_length(year, month)
    first = cs.hijri_to_jdn(year, month, 1)
    days = []
    for i in range(n):
        jdn = first + i
        gy, gm, gd, _ = ac.from_jdn(jdn)
        days.append({
            'hijri': i + 1,
            'masehi': date(gy, gm, gd).isoformat() if 1 <= gy <= 9999 else None,
            'hari': cs.HARI[ac.weekday_index(jdn)],
            'peristiwa': IMPORTANT_DATES.get((month, i + 1)),
            'puasa': fasting_info(jdn)['sunah'],
        })
    return {'tahun': year, 'bulan': month, 'nama_bulan': cs.BULAN_HIJRIAH[month - 1], 'panjang': n, 'hari': days}
