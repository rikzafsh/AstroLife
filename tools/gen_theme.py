"""Membuat app/static/css/theme-palette.css: skala warna (50–950) dari palet utama AstroLife untuk mode gelap dan terang.
Jalankan: python tools/gen_theme.py   (hasilnya sudah ikut di repo; hanya perlu dijalankan lagi bila palet diubah)

Palet utama: 001f8e (biru tua), 2a35e2 (biru), 29aafe (biru langit), ed2124 (merah), 009339 (hijau).
Nama keluarga di sini dipetakan ke nama kelas Tailwind lama di app/static/js/tailwind-config.js."""
from pathlib import Path

BASE = {'pri': '2a35e2', 'deep': '001f8e', 'sky': '29aafe', 'red': 'ed2124', 'grn': '009339', 'amb': 'f59e0b'}
SHADES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)
T_WHITE = {50: .94, 100: .88, 200: .76, 300: .58, 400: .34}
T_BLACK = {600: .14, 700: .30, 800: .46, 900: .62, 950: .78}
# mode terang: teks berwarna harus lebih gelap agar kontras di atas latar putih
TERANG = {200: 900, 300: 800, 400: 700}


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def skala(hex_):
    r = rgb(hex_)
    out = {}
    for s in SHADES:
        if s == 500:
            c = r
        elif s in T_WHITE:
            c = tuple(round(v + (255 - v) * T_WHITE[s]) for v in r)
        else:
            c = tuple(round(v * (1 - T_BLACK[s])) for v in r)
        out[s] = c
    return out


def main():
    gelap, terang = [], []
    for nama, hx in BASE.items():
        sk = skala(hx)
        for s in SHADES:
            gelap.append(f"--{nama}-{s}:{' '.join(map(str, sk[s]))};")
            terang.append(f"--{nama}-{s}:{' '.join(map(str, sk[TERANG.get(s, s)]))};")
    css = ('/* DIHASILKAN oleh tools/gen_theme.py — jangan disunting tangan. */\n'
           ':root, html.dark {\n  ' + '\n  '.join(gelap) + '\n}\n'
           'html:not(.dark) {\n  ' + '\n  '.join(terang) + '\n}\n')
    out = Path(__file__).resolve().parent.parent / 'app' / 'static' / 'css' / 'theme-palette.css'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(css, encoding='utf8')
    print('ditulis', out, len(css), 'byte')


if __name__ == '__main__':
    main()
