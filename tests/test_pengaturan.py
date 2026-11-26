"""Menu Pengaturan: kriteria Hijriah pada jadwal puasa (server) dan logika penyimpanan prefs.js (Node, dilewati bila tidak ada)."""
import shutil
import subprocess
import unittest
from pathlib import Path

from app import create_app

ROOT = Path(__file__).resolve().parent.parent


class PuasaKriteria(unittest.TestCase):
    def setUp(self):
        self.c = create_app().test_client()

    def get(self, k=None, date='2026-11-26'):
        q = f'/islamic/api/puasa?date={date}&days=45' + (f'&kriteria={k}' if k else '')
        return self.c.get(q)

    def test_bawaan_aritmetis(self):
        j = self.get().get_json()
        self.assertEqual(j['kriteria'], 'aritmetis')
        self.assertEqual(j['jadwal'][0]['hijriah'], '15 Jumadilakhir 1448 H')

    def test_kriteria_mengubah_tanggal_hijriah_dan_ayyamulbid(self):
        ar, mb, uq, tk = (self.get(k).get_json() for k in ('aritmetis', 'mabims', 'ummulqura', 'turki'))
        self.assertEqual(mb['jadwal'][0]['hijriah'], '16 Jumadilakhir 1448 H')      # 26 Nov 2026: MABIMS = 16
        self.assertEqual(uq['jadwal'][0]['hijriah'], '16 Jumadilakhir 1448 H')
        self.assertEqual(tk['jadwal'][0]['hijriah'], '17 Jumadilakhir 1448 H')      # KHGT lebih awal
        self.assertEqual(ar['jadwal'][0]['hijriah'], '15 Jumadilakhir 1448 H')
        # 26 Nov adalah Ayyamulbid (13–15) hanya menurut aritmetis
        self.assertIn('Ayyamul Bidh', ar['jadwal'][0]['jenis'])
        self.assertNotIn('Ayyamul Bidh', mb['jadwal'][0]['jenis'])
        self.assertIn('MABIMS', mb['catatan'])
        self.assertEqual(tk['kriteria_nama'], 'KHGT (Turki)')

    def test_kriteria_tidak_dikenal_dan_di_luar_jangkauan(self):
        self.assertEqual(self.get('xx').status_code, 400)
        self.assertEqual(self.get('mabims', date='1200-01-01').status_code, 400)

    def test_halaman_memuat_pengaturan(self):
        h = self.c.get('/islamic/').get_data(as_text=True)
        for kunci in ('dlg-pengaturan', 'pref-hijriah', 'name="pref-hijriah" value="ummulqura"', 'pref-metode', 'data-open-settings', 'prefs.js'):
            self.assertIn(kunci, h)


@unittest.skipUnless(shutil.which('node'), 'Node tidak tersedia')
class PrefsJs(unittest.TestCase):
    def run_js(self, kode, awal=''):
        pre = r'''
        const store = {}; const ev = []; const winL = {};
        global.window = global; global.ASTRO_DEFAULTS = {nama:'Yogyakarta', lat:-7.7956, lon:110.3695};
        global.localStorage = {getItem:k=>k in store?store[k]:null, setItem:(k,v)=>{store[k]=String(v)}, removeItem:k=>{delete store[k]}};
        global.addEventListener = (n,f)=>{winL[n]=f};
        global.CustomEvent = class { constructor(n,o){this.type=n;this.detail=o.detail} };
        global.document = {readyState:'complete', querySelectorAll:()=>[], dispatchEvent:e=>ev.push(e), addEventListener(){}};
        '''+awal+'''
        require(process.argv[1]);
        '''
        r = subprocess.run(['node', '-e', pre + kode, str(ROOT / 'app/static/js/prefs.js')], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_bawaan_dan_simpan(self):
        out = self.run_js("const P=AstroPrefs; console.log(JSON.stringify([P.get().lokasi.nama, P.get().hijriah.kriteria, P.get().salat.metode]));"
                          "P.set({hijriah:{kriteria:'turki'}, lokasi:{nama:'Medan', lat:3.5952, lon:98.6722}});"
                          "console.log(JSON.stringify([JSON.parse(store['astrolife.prefs.v1']).hijriah.kriteria, ev.length, ev[0].detail.berubah]));")
        l1, l2 = out.splitlines()
        self.assertEqual(l1, '["Yogyakarta","aritmetis","persatuanIslam"]')
        self.assertEqual(l2, '["turki",1,["lokasi","hijriah"]]')

    def test_data_rusak_dibersihkan(self):
        out = self.run_js("const g=AstroPrefs.get(); console.log(JSON.stringify([g.lokasi.lat,g.lokasi.lon,g.salat.ihtiyat,g.salat.imsak,g.salat.metode,g.hijriah.kriteria]));",
                          awal="store['astrolife.prefs.v1']=JSON.stringify({lokasi:{lat:999,lon:'x'},salat:{ihtiyat:99,imsak:-5,metode:''},hijriah:{kriteria:'abc'}});")
        self.assertEqual(out, '[-7.7956,110.3695,2,10,"persatuanIslam","aritmetis"]')

    def test_migrasi_lokasi_katalog_lama_dan_query(self):
        out = self.run_js("const l=AstroPrefs.get().lokasi; console.log(l.lat,l.lon,AstroPrefs.nama(),AstroPrefs.qsLokasi().toString());",
                          awal="store['astrolife.catalog.v3']=JSON.stringify({lat:'-6.2088',lon:'106.8456'});")
        self.assertEqual(out, '-6.2088 106.8456 Jakarta lat=-6.2088&lon=106.8456&elev=0')

    def test_tidak_siarkan_bila_tidak_berubah(self):
        out = self.run_js("AstroPrefs.set({hijriah:{kriteria:'aritmetis'}}); console.log(ev.length);"
                          "AstroPrefs.set({hijriah:{kriteria:'mabims'}}); console.log(ev.length);")
        self.assertEqual(out.splitlines(), ['0', '1'])


if __name__ == '__main__':
    unittest.main()
