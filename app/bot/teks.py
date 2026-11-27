"""Normalisasi teks Indonesia untuk pencarian: huruf kecil, tanpa aksen/tanda baca, sinonim ejaan, stemming ringan."""
import re
import unicodedata

STOP = frozenset('''
yang dan di ke dari untuk pada dengan atau ini itu adalah ialah apa apakah bagaimana mengapa kenapa kapan berapa siapa dimana
mana saja sih dong deh ya kah lah nya akan sudah belum bisa dapat boleh mau ingin tolong mohon minta saya aku kamu anda kita
kami mereka tentang soal seputar mengenai ada tidak bukan juga lagi masih sangat lebih paling agar supaya karena sebab oleh
dalam atas bawah antara sebagai seperti jadi maka kalau jika bila apabila hanya cuma pun
'''.split())

# ejaan ragam -> bentuk baku (kata utuh)
SINONIM = {
    'shalat': 'salat', 'sholat': 'salat', 'solat': 'salat', 'shalah': 'salat', 'salah': 'salah',
    'qiblat': 'kiblat', 'kiblah': 'kiblat', 'qibla': 'kiblat',
    'hijriyah': 'hijriah', 'hijri': 'hijriah', 'hijrah': 'hijriah', 'islam': 'islam',
    'dzuhur': 'zuhur', 'dhuhur': 'zuhur', 'duhur': 'zuhur', 'zhuhur': 'zuhur',
    'ashar': 'asar', 'ashr': 'asar', 'maghrib': 'magrib', 'magrib': 'magrib', 'isyak': 'isya', 'isha': 'isya',
    'shubuh': 'subuh', 'fajr': 'subuh', 'dhuha': 'duha', 'syuruk': 'terbit',
    'ramadhan': 'ramadan', 'romadhon': 'ramadan', 'ramadlan': 'ramadan', 'puasa': 'puasa', 'shaum': 'puasa',
    'muharram': 'muharam', 'suro': 'sura', 'safar': 'safar', 'shafar': 'safar', 'syafar': 'safar',
    'rabiul': 'rabiul', 'rabi': 'rabiul', 'jumadil': 'jumadil', 'jumadal': 'jumadil', 'jumada': 'jumadil',
    'sya\'ban': 'syakban', 'syaban': 'syakban', 'shaban': 'syakban', 'syawwal': 'syawal', 'shawal': 'syawal',
    'dzulkaidah': 'zulkaidah', 'dzulqadah': 'zulkaidah', 'zulqadah': 'zulkaidah', 'dzulhijjah': 'zulhijah', 'zulhijjah': 'zulhijah', 'dzulhijah': 'zulhijah',
    'idul': 'idul', 'iedul': 'idul', 'lebaran': 'idulfitri', 'idulfitri': 'idulfitri', 'iduladha': 'iduladha', 'idhuladha': 'iduladha',
    'rukyah': 'rukyat', 'rukyatul': 'rukyat', 'hisab': 'hisab', 'hisap': 'hisab', 'ijtima': 'ijtimak', 'ijtimak': 'ijtimak', 'ijtimaak': 'ijtimak',
    'rashdul': 'rasydul', 'rasdul': 'rasydul', 'rasyidul': 'rasydul', 'rosydul': 'rasydul', 'rasydulqiblat': 'rasydulkiblat', 'rashdulqiblat': 'rasydulkiblat',
    'rasydulkiblat': 'rasydulkiblat', 'rasdulkiblat': 'rasydulkiblat',
    'kabah': 'kabah', 'kaabah': 'kabah', 'ka\'bah': 'kabah',
    'ummul': 'ummul', 'umm': 'ummul', 'umul': 'ummul', 'wujudul': 'wujudul', 'wujud': 'wujud',
    'purnama': 'purnama', 'fullmoon': 'purnama', 'meteor': 'meteor', 'astronomi': 'astronomi',
    'sholatnya': 'salat', 'jawa': 'jawa', 'jawi': 'jawa',
}
_AKSEN = str.maketrans({'é': 'e', 'è': 'e', 'ê': 'e', 'ā': 'a', 'ī': 'i', 'ū': 'u', 'ṣ': 's', 'ṭ': 't', 'ḥ': 'h', 'ṅ': 'n', 'ṇ': 'n', 'ś': 's', 'ṛ': 'r', 'ʼ': "'", '’': "'", '′': "'"})


def bersih(s: str) -> str:
    s = unicodedata.normalize('NFKD', (s or '').lower()).translate(_AKSEN)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s


def _stem(w: str) -> str:
    """Stemming sangat ringan agar 'menghitung'≈'hitung', 'perhitungan'≈'hitung'. Aman untuk kata pendek."""
    if len(w) <= 4 or w.isdigit():
        return w
    for suf in ('nya', 'lah', 'kah', 'kan', 'an', 'i'):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[:-len(suf)]
            break
    for pre in ('meng', 'meny', 'mem', 'men', 'me', 'peng', 'peny', 'pem', 'pen', 'per', 'ber', 'ter', 'di', 'ke', 'se', 'pe'):
        if w.startswith(pre) and len(w) - len(pre) >= 4:
            w = w[len(pre):]
            break
    return w


def token(s: str, stem: bool = True, buang_stop: bool = True) -> list[str]:
    out = []
    for t in re.findall(r"[a-z0-9']+", bersih(s)):
        t = t.strip("'")
        if not t:
            continue
        t = SINONIM.get(t, t)
        if buang_stop and t in STOP:
            continue
        out.append(_stem(t) if stem else t)
    return out
