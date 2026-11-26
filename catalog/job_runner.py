"""
Titik masuk proses pembuatan katalog yang diluncurkan aplikasi (catalog.jobs.start):

    python -m catalog.job_runner 2026 2027 --dir data/catalog [--force]

Menulis status.json (tahap, progres, galat) agar halaman web dapat menampilkan progres.
Mesin posisi ditentukan variabel lingkungan ASTROLIFE_ENGINE (diatur oleh aplikasi).
"""
import argparse
import os
import sys
import time
import traceback
from pathlib import Path

from catalog import jobs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('dari', type=int)
    ap.add_argument('sampai', type=int)
    ap.add_argument('--dir', required=True)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args(argv)
    d = Path(a.dir)
    t0 = time.time()
    engine = os.environ.get('ASTROLIFE_ENGINE', 'lite')
    jobs.write_status(d, state='running', pid=os.getpid(), engine_key=engine, year_from=a.dari, year_to=a.sampai,
                      message='Menyiapkan mesin posisi' + (' (unduhan efemeris JPL ~32 MB pada pemakaian pertama)…' if engine == 'skyfield' else '…'))
    try:
        from catalog import generate as G                  # impor mesin (Skyfield mengunduh DE440s di sini bila belum ada)

        def progress(done, total, message):
            el = time.time() - t0
            eta = (el / done) * (total - done) if done else None
            jobs.write_status(d, state='running', done=done, total=total, message=message, eta_seconds=round(eta) if eta else None)

        jobs.write_status(d, message='Mesin siap, mulai menghitung…', engine=G.E.NAME)
        G.generate(a.dari, a.sampai, out=d / 'events.json', force=a.force, log=print, progress=progress, catalog_dir=d)
        jobs.write_status(d, state='done', message='Katalog selesai dibuat.', finished_at=jobs.now_iso(), done=jobs.read_raw(d).get('total'),
                          error=None, eta_seconds=0, elapsed_seconds=round(time.time() - t0))
        return 0
    except BaseException as e:                              # noqa: BLE001  (semua galat harus tampil di UI)
        traceback.print_exc()
        jobs.write_status(d, state='error', error=f'{type(e).__name__}: {e}', finished_at=jobs.now_iso(), log_tail=jobs.log_tail(d))
        return 1


if __name__ == '__main__':
    sys.exit(main())
