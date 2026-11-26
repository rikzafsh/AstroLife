"""Tema terang/gelap & palet: berkas statis tersedia, rangka halaman memuatnya, dan palet cocok dengan generator."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

from app import create_app

ROOT = Path(__file__).resolve().parent.parent
HALAMAN = ['/', '/about', '/observation/', '/catalog/', '/calendar/', '/islamic/', '/bot/']


class Tema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = create_app().test_client()

    def test_berkas_statis(self):
        for u in ('/static/css/theme.css', '/static/css/theme-palette.css', '/static/js/tailwind-config.js'):
            self.assertEqual(self.c.get(u).status_code, 200, u)

    def test_semua_halaman_punya_pemilih_tema(self):
        for u in HALAMAN:
            h = self.c.get(u).get_data(as_text=True)
            for kunci in ('data-theme-set="light"', 'data-theme-set="dark"', 'data-theme-set="auto"', 'astrolife.theme', 'theme-palette.css', 'id="konten"'):
                self.assertIn(kunci, h, (u, kunci))

    def test_palet_utama(self):
        cfg = (ROOT / 'app/static/js/tailwind-config.js').read_text(encoding='utf8')
        for hx in ('001f8e', '2a35e2', '29aafe', 'ed2124', '009339'):
            self.assertIn(hx, cfg.lower())
            self.assertIn(hx, (ROOT / 'tools/gen_theme.py').read_text(encoding='utf8').lower())

    def test_palet_cocok_dengan_generator(self):
        asli = (ROOT / 'app/static/css/theme-palette.css').read_text(encoding='utf8')
        subprocess.run([sys.executable, str(ROOT / 'tools/gen_theme.py')], check=True, capture_output=True)
        self.assertEqual((ROOT / 'app/static/css/theme-palette.css').read_text(encoding='utf8'), asli)

    def test_mode_terang_punya_variabel_lengkap(self):
        css = (ROOT / 'app/static/css/theme.css').read_text(encoding='utf8')
        gelap = set(re.findall(r'(--[\w-]+):', css.split('html:not(.dark)')[0]))
        terang = set(re.findall(r'(--[\w-]+):', css.split('html:not(.dark) {')[1].split('}')[0]))
        for v in ('--page', '--surface', '--line', '--text', '--muted', '--ink', '--sl-500', '--field-bg', '--header-bg'):
            self.assertIn(v, gelap, v)
            self.assertIn(v, terang, v)

    def test_tidak_ada_kelas_gelap_saja_yang_tertinggal(self):
        # warna latar tetap (hex gelap) tidak boleh dipakai langsung di templat; harus lewat variabel tema
        for f in (ROOT / 'app/templates').rglob('*.html'):
            s = f.read_text(encoding='utf8')
            self.assertNotIn('#060814', s, f)
            self.assertNotIn('bg-space-950/90', s, f)


if __name__ == '__main__':
    unittest.main()
