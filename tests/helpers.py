"""Pembantu tes: respons Open-Meteo TIRUAN (agar tes tidak butuh internet). Menguji LOGIKA, bukan akurasi cuaca."""
from datetime import datetime, timedelta
from unittest import mock

from app.services import weather_service as ws


def payload(cloud, rain=5, off=25200, start=datetime(2026, 11, 15), days=17):
    """Respons prakiraan per jam. cloud = angka tetap atau fungsi(datetime)->persen; off = utc_offset_seconds lokasi."""
    cols = {k: [] for k in ['temperature_2m', 'relative_humidity_2m', 'precipitation_probability', 'precipitation',
                            'cloud_cover', 'cloud_cover_low', 'cloud_cover_mid', 'cloud_cover_high', 'visibility']}
    times = []
    for i in range(days * 24):
        t = start + timedelta(hours=i)
        c = cloud(t) if callable(cloud) else cloud
        times.append(t.strftime('%Y-%m-%dT%H:00'))
        for k, v in zip(cols, [26, 75, rain, 0.0, c, c * .5, c * .3, c * .2, 24000]):
            cols[k].append(v)
    return {'utc_offset_seconds': off, 'hourly': {'time': times, **cols}}


class Resp:
    def __init__(self, p):
        self.p = p

    def raise_for_status(self):
        pass

    def json(self):
        return self.p


def net(forecast=None, archive=None, down=False):
    """Patch requests.get pada weather_service. down=True mensimulasikan tanpa internet."""
    ws._cache.clear()

    def fake(url, params=None, timeout=None):
        if down:
            raise ConnectionError('offline')
        if 'archive' in url:
            if archive is None:
                raise ConnectionError('archive down')
            return Resp(archive(params))
        return Resp(forecast)
    return mock.patch.object(ws.requests, 'get', side_effect=fake)


def archive_payload(params):
    n = 15 * 24
    t0 = datetime.strptime(params['start_date'], '%Y-%m-%d')
    return {'utc_offset_seconds': 25200, 'hourly': {
        'time': [(t0 + timedelta(hours=i)).strftime('%Y-%m-%dT%H:00') for i in range(n)],
        'cloud_cover': [60] * n, 'relative_humidity_2m': [80] * n,
        'precipitation': [0.2 if i % 48 == 0 else 0 for i in range(n)], 'temperature_2m': [25] * n}}


def fake_now(now):
    """Kelas pengganti `datetime` yang membekukan utcnow() (untuk mock.patch.object(modul, 'datetime', ...))."""
    class _DT(datetime):
        @classmethod
        def utcnow(cls):
            return now
    return _DT
