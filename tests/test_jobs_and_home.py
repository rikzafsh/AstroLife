"""Pembuatan katalog dari aplikasi (proses terpisah + status), beranda, dan jaminan referensi lama tidak kembali."""
import os
os.environ['ASTROLIFE_ENGINE'] = 'lite'

import contextlib
import io
import re
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from app import create_app
from app.services.home_service import today_summary
from catalog import jobs

ROOT = Path(__file__).resolve().parent.parent


class JobValidation(unittest.TestCase):
    def test_year_rules(self):
        with mock.patch.object(jobs, 'options', return_value={'skyfield_installed': True, 'ephemeris_present': False, 'default_engine': 'skyfield'}):
            self.assertEqual(jobs.validate('2026', '2027', 'lite'), (2026, 2027))
            for bad in [(1999, 2000), (2026, 2025), (2026, 2101), (2026, 2031), ('x', 2026), (None, None)]:
                with self.assertRaises(ValueError, msg=str(bad)):
                    jobs.validate(*bad, 'lite')
            with self.assertRaises(ValueError):
                jobs.validate(2026, 2026, 'mesin-lain')

    def test_skyfield_requires_installation(self):
        with mock.patch.object(jobs, 'options', return_value={'skyfield_installed': False, 'ephemeris_present': False, 'default_engine': 'lite'}):
            with self.assertRaises(ValueError):
                jobs.validate(2026, 2026, 'skyfield')


class JobStatus(unittest.TestCase):
    def test_idle_and_percent(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(jobs.read_status(d), {'state': 'idle'})
            jobs.write_status(d, state='running', done=13, total=26, message='x')
            self.assertEqual(jobs.read_status(d)['percent'], 50.0)

    def test_stale_running_job_is_reported_as_error(self):
        with tempfile.TemporaryDirectory() as d:
            jobs.write_status(d, state='running', done=1, total=26)
            old = (datetime.now() - timedelta(seconds=jobs.STALE_SECONDS + 60)).isoformat(timespec='seconds')
            p = jobs.status_path(d)
            p.write_text(p.read_text(encoding='utf-8').replace(jobs.read_raw(d)['updated_at'], old), encoding='utf-8')
            st = jobs.read_status(d)
            self.assertEqual(st['state'], 'error')
            self.assertIn('berhenti', st['error'])

    def test_runner_reports_exceptions_in_status(self):
        from catalog import job_runner
        with tempfile.TemporaryDirectory() as d, mock.patch('catalog.generate.generate', side_effect=RuntimeError('boom')):
            with contextlib.redirect_stderr(io.StringIO()):                                  # jejak tumpukan disengaja; jangan tampil
                code = job_runner.main(['2026', '2026', '--dir', d])
            st = jobs.read_status(d)
        self.assertEqual(code, 1)
        self.assertEqual(st['state'], 'error')
        self.assertIn('RuntimeError: boom', st['error'])


class InAppGeneration(unittest.TestCase):
    """Satu proses nyata (mesin cepat, 1 tahun): validasi -> mulai -> menolak ganda -> progres -> selesai -> dipakai API."""

    def test_full_cycle_without_terminal(self):
        with tempfile.TemporaryDirectory() as d:
            app = create_app()
            app.config['CATALOG_DIR'] = Path(d)
            c = app.test_client()
            self.assertEqual(c.get('/catalog/api/events').status_code, 404)                       # belum ada katalog
            self.assertEqual(c.post('/catalog/api/generate', json={'dari': 2026, 'sampai': 2040, 'mesin': 'lite'}).status_code, 400)
            r = c.post('/catalog/api/generate', json={'dari': 2026, 'sampai': 2026, 'mesin': 'lite'})
            self.assertEqual((r.status_code, r.get_json()['status']), (202, 'started'))
            self.assertEqual(c.post('/catalog/api/generate', json={'dari': 2026, 'sampai': 2026, 'mesin': 'lite'}).status_code, 409)

            seen, deadline = [], time.time() + 120
            st = {}
            while time.time() < deadline:
                st = c.get('/catalog/api/generate/status').get_json()['job']
                seen.append(st.get('percent', 0))
                if st['state'] in ('done', 'error'):
                    break
                time.sleep(0.3)
            self.assertEqual(st['state'], 'done', st)
            self.assertEqual(seen, sorted(seen))                                                  # progres tidak mundur
            self.assertEqual(st['percent'], 100.0)
            self.assertTrue((Path(d) / 'events.json').exists())

            j = c.get('/catalog/api/events?year=2026&month=11').get_json()                         # langsung dipakai
            self.assertEqual(j['status'], 'success')
            self.assertGreater(j['summary']['total'], 20)
            self.assertEqual(j['meta']['engine_key'], 'lite')
            up = c.get('/catalog/api/upcoming?days=60&limit=5').get_json()
            self.assertEqual(up['status'], 'success')
            opts = c.get('/catalog/api/generate/options').get_json()
            self.assertEqual(opts['catalog']['dari_tahun'], 2026)
            # setelah selesai, pembuatan baru diizinkan lagi
            self.assertEqual(c.post('/catalog/api/generate', json={'dari': 2026, 'sampai': 2026, 'mesin': 'lite'}).status_code, 202)
            deadline = time.time() + 120
            while time.time() < deadline and c.get('/catalog/api/generate/status').get_json()['job']['state'] == 'running':
                time.sleep(0.3)


class Home(unittest.TestCase):
    def test_today_summary_is_computed(self):
        s = today_summary(datetime(2026, 11, 21, 3, 45), 7.0)
        self.assertEqual((s['tanggal_teks'], s['weton']), ('Sabtu, 21 November 2026', 'Sabtu Pahing'))
        self.assertEqual((s['bulan']['fase'], s['bulan']['arah']), ('Cembung Awal', 'menuju purnama'))
        self.assertTrue(75 <= s['bulan']['terang_pct'] <= 92)                                    # purnama 24 Nov

    def test_local_date_follows_timezone(self):
        s = today_summary(datetime(2026, 11, 20, 18, 0), 7.0)                                     # 01:00 WIB tanggal 21
        self.assertEqual(s['tanggal_teks'], 'Sabtu, 21 November 2026')
        self.assertEqual(today_summary(datetime(2026, 11, 20, 18, 0), 0.0)['tanggal_teks'], 'Jumat, 20 November 2026')

    def test_phase_cycle(self):
        phases = {today_summary(datetime(2026, 11, 1) + timedelta(days=i), 7.0)['bulan']['fase'] for i in range(0, 30, 3)}
        self.assertGreaterEqual(len(phases), 6)

    def test_page_is_real_not_mock(self):
        c = create_app().test_client()
        html = c.get('/').get_data(as_text=True)
        self.assertEqual(c.get('/').status_code, 200)
        for gone in ('Pembaruan realtime', '84/100', 'Hujan Meteor Leonid', 'Skor Langit'):
            self.assertNotIn(gone, html)
        for need in ('Langit hari ini', 'Event mendatang', 'catalog', 'observation', 'Dalam pengembangan'):
            self.assertIn(need, html)
        self.assertIn('Yogyakarta', html)                                                          # lokasi bawaan dari konfigurasi

    def test_all_pages_render(self):
        c = create_app().test_client()
        for u in ('/', '/about', '/catalog/', '/observation/', '/calendar/', '/islamic/', '/bot/'):
            self.assertEqual(c.get(u).status_code, 200, u)


class RemovedThingsStayRemoved(unittest.TestCase):
    BANNED = re.compile(r'in-the-sky|inthesky|scraper|scraping|playwright|beautifulsoup|bs4|analytics|analitik|scikit|pandas|machine learning', re.I)

    def test_routes_are_gone(self):
        c = create_app().test_client()
        for u in ('/analytics/', '/observation/api/events', '/observation/api/sync', '/observation/api/sync-status', '/observation/api/event-forecast'):
            self.assertIn(c.get(u).status_code, (404, 405), u)

    def test_no_references_in_product_files(self):
        files = [p for pat in ('app/**/*.py', 'app/**/*.html', 'app/**/*.css', 'catalog/**/*.py', 'catalog/**/*.md', 'prototype/**/*.py',
                               'prototype/**/*.md', '*.py', '*.md', '*.txt', '.env.example') for p in ROOT.glob(pat)
                 if p.name not in ('knowledge.md',) and '__pycache__' not in p.parts]
        bad = []
        for p in files:
            for n, line in enumerate(p.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
                if self.BANNED.search(line):
                    bad.append(f'{p.relative_to(ROOT)}:{n}: {line.strip()[:80]}')
        self.assertEqual(bad, [])

    def test_dependencies_trimmed(self):
        req = (ROOT / 'requirements.txt').read_text(encoding='utf-8').lower()
        for gone in ('beautifulsoup', 'pandas', 'scikit', 'plotly', 'lxml', 'playwright'):
            self.assertNotIn(gone, req)
        self.assertIn('skyfield', req)


if __name__ == '__main__':
    unittest.main()
