"""
Pembuatan katalog dari dalam aplikasi: meluncurkan `python -m catalog.job_runner` sebagai PROSES TERPISAH dan membaca
berkas status.json yang ditulis proses itu. Proses terpisah dipakai karena mesin posisi dipilih saat impor modul
(aplikasi dapat tetap memakai mesin cepat untuk keterlihatan, sementara pembuatan katalog memakai Skyfield).
"""
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS_NAME = 'status.json'
LOG_NAME = 'generate.log'
STALE_SECONDS = 600            # tanpa detak status selama ini = dianggap terhenti
MIN_YEAR, MAX_YEAR, MAX_SPAN = 2000, 2100, 5


class JobBusy(Exception):
    pass


def status_path(catalog_dir) -> Path:
    return Path(catalog_dir) / STATUS_NAME


def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


def write_status(catalog_dir, **fields) -> dict:
    """Tulis status secara atomik (menggabungkan dengan isi sebelumnya)."""
    path = status_path(catalog_dir)
    cur = read_raw(catalog_dir)
    cur.update(fields)
    cur['updated_at'] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(cur, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)
    return cur


def read_raw(catalog_dir) -> dict:
    path = status_path(catalog_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return {}


def read_status(catalog_dir) -> dict:
    """Status untuk antarmuka; pekerjaan yang tak lagi berdetak ditandai error (terhenti)."""
    st = read_raw(catalog_dir)
    if not st:
        return {'state': 'idle'}
    if st.get('state') in ('starting', 'running'):
        try:
            age = (datetime.now() - datetime.fromisoformat(st['updated_at'])).total_seconds()
        except (KeyError, ValueError):
            age = STALE_SECONDS + 1
        if age > STALE_SECONDS:
            st = {**st, 'state': 'error', 'error': 'Proses pembuatan katalog berhenti tanpa kabar (mungkin aplikasi ditutup). Coba mulai lagi.'}
    total = st.get('total') or 0
    st['percent'] = round(100.0 * (st.get('done') or 0) / total, 1) if total else 0.0
    return st


def options() -> dict:
    sky = importlib.util.find_spec('skyfield') is not None
    eph = (ROOT / 'data' / 'ephemeris' / 'de440s.bsp').exists()
    return {'skyfield_installed': sky, 'ephemeris_present': eph, 'default_engine': 'skyfield' if sky else 'lite'}


def validate(y0, y1, engine) -> tuple:
    try:
        y0, y1 = int(y0), int(y1)
    except (TypeError, ValueError):
        raise ValueError('Tahun harus berupa angka.')
    if not (MIN_YEAR <= y0 <= y1 <= MAX_YEAR):
        raise ValueError(f'Rentang tahun harus {MIN_YEAR}..{MAX_YEAR} dan tahun akhir >= tahun awal.')
    if y1 - y0 + 1 > MAX_SPAN:
        raise ValueError(f'Paling banyak {MAX_SPAN} tahun sekali buat.')
    if engine not in ('skyfield', 'lite'):
        raise ValueError("Mesin harus 'skyfield' atau 'lite'.")
    if engine == 'skyfield' and not options()['skyfield_installed']:
        raise ValueError('Skyfield belum terpasang (pip install skyfield). Pilih mesin cepat atau pasang Skyfield.')
    return y0, y1


def start(catalog_dir, y0, y1, engine=None, force=False) -> dict:
    catalog_dir = Path(catalog_dir)
    engine = engine or options()['default_engine']
    y0, y1 = validate(y0, y1, engine)
    cur = read_status(catalog_dir)
    if cur.get('state') in ('starting', 'running'):
        raise JobBusy('Pembuatan katalog sedang berjalan.')
    catalog_dir.mkdir(parents=True, exist_ok=True)
    st = {'state': 'starting', 'engine_key': engine, 'year_from': y0, 'year_to': y1, 'done': 0, 'total': 0,
          'message': 'Memulai proses…', 'started_at': now_iso(), 'finished_at': None, 'error': None, 'log_tail': ''}
    status_path(catalog_dir).write_text('{}', encoding='utf-8') if not status_path(catalog_dir).exists() else None
    write_status(catalog_dir, **st)
    cmd = [sys.executable, '-m', 'catalog.job_runner', str(y0), str(y1), '--dir', str(catalog_dir)] + (['--force'] if force else [])
    env = {**os.environ, 'ASTROLIFE_ENGINE': engine, 'PYTHONUNBUFFERED': '1', 'PYTHONPATH': str(ROOT)}
    log = open(catalog_dir / LOG_NAME, 'w', encoding='utf-8')
    kwargs = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)} if os.name == 'nt' else {'start_new_session': True}
    try:
        subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT, **kwargs)
    except OSError as e:
        write_status(catalog_dir, state='error', error=f'Tidak dapat menjalankan proses: {e}', finished_at=now_iso())
        raise
    finally:
        log.close()
    return read_status(catalog_dir)


def log_tail(catalog_dir, lines=12) -> str:
    p = Path(catalog_dir) / LOG_NAME
    if not p.exists():
        return ''
    try:
        return '\n'.join(p.read_text(encoding='utf-8', errors='replace').strip().splitlines()[-lines:])
    except OSError:
        return ''
