"""
Label kelangkaan event. Berbasis ATURAN yang terdokumentasi (bukan statistik hasil hitung), dengan frekuensi
berupa perkiraan kualitatif. Lima tingkat: common < uncommon < rare < epic < legendary.

Dasar: seberapa sering kejadian sejenis berlangsung dan, untuk gerhana Matahari, seberapa jarang pengamat di SATU
lokasi mengalami fase sentral. Angka frekuensi adalah perkiraan umum astronomi, bukan hasil pemindaian katalog ini.
"""
TIERS = ['common', 'uncommon', 'rare', 'epic', 'legendary']
TIER_LABEL = {'common': 'Umum', 'uncommon': 'Tidak Umum', 'rare': 'Langka', 'epic': 'Epik', 'legendary': 'Legendaris'}
BRIGHT_STARS = {'regulus', 'antares', 'spica', 'aldebaran'}
PLANETS_BRIGHT = {'venus', 'mars', 'jupiter', 'saturn'}


def _r(tier: str, freq: str, why: str) -> dict:
    return {'tier': tier, 'label': TIER_LABEL[tier], 'frekuensi': freq, 'alasan': why}


def rarity(ev: dict, vis: dict = None) -> dict:
    cat, kind, bodies = ev['category'], ev['kind'], ev['bodies']
    d = ev.get('details', {})
    sep = ev.get('separation_deg')
    planets = [b for b in bodies if b not in ('moon', 'sun')]

    if cat == 'fase_bulan':
        return _r('common', 'setiap ~29,5 hari', 'Siklus fase Bulan berulang tiap bulan.')

    if cat == 'konjungsi':
        if 'moon' in bodies:
            return _r('common', 'hampir setiap bulan', 'Bulan melintasi tiap planet dan bintang terang dekat ekliptika setiap bulan.')
        if set(bodies) == {'jupiter', 'saturn'}:
            if sep is not None and sep < 0.5:
                return _r('legendary', 'sekitar sekali per 20 tahun, sangat dekat hanya beberapa kali per abad',
                          'Konjungsi Besar Jupiter-Saturnus dengan jarak < 0,5 derajat.')
            return _r('rare', 'sekitar sekali per 20 tahun', 'Konjungsi Besar Jupiter-Saturnus.')
        if sep is not None and sep < 1.0:
            return _r('rare', 'beberapa kali per dekade', f'Dua planet berjarak hanya {sep:.1f} derajat.')
        return _r('uncommon', 'sekitar sekali-dua kali setahun', 'Konjungsi dua planet terlihat jarang terjadi dalam jarak dekat.')

    if cat == 'okultasi':
        other = planets[0] if planets else ''
        lo = (vis or {}).get('local_occultation') or {}
        if lo.get('terjadi') and other not in BRIGHT_STARS and other not in ('', ):
            if other in PLANETS_BRIGHT | {'mercury', 'uranus', 'neptune'}:
                return _r('rare', 'di satu lokasi: sekali per beberapa tahun atau lebih jarang',
                          'Okultasi planet oleh Bulan yang benar-benar terjadi di lokasi Anda.')
        if other in BRIGHT_STARS:
            return _r('uncommon', 'beberapa kali dalam deret tahunan tertentu', 'Okultasi bintang terang oleh Bulan terjadi berseri, lalu terhenti bertahun-tahun.')
        if other in PLANETS_BRIGHT:
            return _r('uncommon', 'beberapa kali per tahun secara global', 'Okultasi planet terang oleh Bulan; terlihat dari wilayah sempit.')
        if other in ('mercury', 'uranus', 'neptune'):
            return _r('rare', 'sekitar sekali per beberapa tahun', 'Okultasi planet redup/dekat Matahari oleh Bulan.')
        return _r('common', 'beberapa kali per tahun', 'Okultasi bintang oleh Bulan.')

    if cat == 'gerhana_bulan':
        if kind == 'total':
            return _r('rare', 'sekitar 1 kali per 1-2 tahun secara global', 'Gerhana Bulan total; pada lokasi tertentu bisa lebih jarang.')
        if kind == 'sebagian':
            return _r('uncommon', 'sekitar sekali setahun secara global', 'Gerhana Bulan sebagian.')
        return _r('common', '1-2 kali setahun secara global', 'Gerhana penumbra: perubahan sangat halus, sering tak terlihat mata.')

    if cat == 'gerhana_matahari':
        loc = (vis or {}).get('local_eclipse') or {}
        if loc.get('terlihat') and loc.get('jenis_lokal') == 'total/cincin':
            if kind == 'total':
                return _r('legendary', 'rata-rata sekali per ratusan tahun di satu lokasi', 'Lokasi Anda berada pada jalur totalitas.')
            return _r('epic', 'rata-rata sekali per beberapa ratus tahun di satu lokasi', 'Lokasi Anda berada pada jalur gerhana cincin.')
        if kind == 'total':
            return _r('epic', 'sekitar 1 kali per 1,5 tahun secara global; sekali per ratusan tahun di satu lokasi', 'Gerhana Matahari total.')
        if kind == 'cincin':
            return _r('rare', 'sekitar 1 kali per 1-2 tahun secara global', 'Gerhana Matahari cincin.')
        return _r('uncommon', 'sekitar 1-2 kali setahun secara global', 'Gerhana Matahari sebagian.')

    if cat == 'elongasi':
        return _r('uncommon', 'Merkurius ~3 kali/tahun per sisi, Venus ~sekali per 8 bulan',
                  'Elongasi maksimum menandai waktu terbaik melihat planet dalam.')
    if cat == 'oposisi':
        if 'mars' in bodies:
            return _r('rare', 'sekali per ~26 bulan', 'Oposisi Mars; jarak dan kecerahan berubah besar dari satu oposisi ke berikutnya.')
        return _r('uncommon', 'sekali per ~1 tahun', 'Oposisi planet luar (sekitar sekali setahun).')
    if cat == 'fase_planet':
        if kind == 'greatest_brightness' and 'venus' in bodies:
            return _r('rare', 'sekali per ~19 bulan', 'Venus mencapai kecerahan maksimum pada satu sisi tiap siklus sinodis.')
        return _r('common', 'beberapa kali setahun', 'Peristiwa fase planet dalam yang berulang tiap siklus sinodis.')
    if cat == 'hujan_meteor':
        zhr = d.get('zhr', 0)
        if zhr >= 100:
            return _r('uncommon', 'tahunan', f'Hujan meteor besar (ZHR ~{zhr}) yang berulang tiap tahun.')
        return _r('common', 'tahunan', f'Hujan meteor tahunan (ZHR ~{zhr}).')
    return _r('common', '-', 'Kategori belum memiliki aturan khusus.')
