"""Pembantu cuaca & rekomendasi pengamatan untuk AstroBot (membungkus weather_service dan planner_service; tidak memalsukan data)."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.services import astro_core as ac
from app.services import planner_service as planner
from app.services import weather_service as W

BLOK = (('Pagi', 6, 11), ('Siang', 12, 15), ('Sore', 16, 18), ('Malam', 19, 23))


def _rata(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def cuaca_hari_ini(lat: float, lon: float, now_utc: datetime) -> dict | None:
    """Ringkasan per blok waktu untuk tanggal lokal hari ini. None bila layanan cuaca tidak dapat dihubungi."""
    fc = W.fetch_hourly_forecast(lat, lon)
    if not fc:
        return None
    local = now_utc + timedelta(seconds=fc['offset'])
    tgl = local.strftime('%Y-%m-%d')
    blok = []
    for nama, a, b in BLOK:
        jam = [fc['hours'].get(f'{tgl}T{h:02d}:00') for h in range(a, b + 1)]
        jam = [x for x in jam if x]
        if not jam:
            continue
        awan, hujan = _rata([x['cloud_cover_pct'] for x in jam]), max([x['precipitation_prob'] for x in jam if x['precipitation_prob'] is not None] or [None])
        mm = sum(x['precipitation_mm'] or 0 for x in jam)
        blok.append({'nama': nama, 'rentang': f'{a:02d}–{b:02d}', 'kondisi': W._condition_label(awan, hujan), 'awan': awan, 'hujan': hujan,
                     'mm': mm, 'suhu': _rata([x['temp_c'] for x in jam]), 'lembap': _rata([x['humidity_pct'] for x in jam])})
    kini = fc['hours'].get(local.strftime('%Y-%m-%dT%H:00'))
    return {'tanggal': tgl, 'jam_lokal': local.strftime('%H:%M'), 'blok': blok, 'sekarang': kini}


def malam_minggu(lat: float, lon: float, tz: float, now_utc: datetime, n: int = 7, jam: int = 20) -> dict:
    """n malam ke depan pada pukul `jam` waktu lokal: fase/penerangan/tinggi Bulan dan (bila prakiraan tersedia) skor kelayakan mata telanjang."""
    ada = W.fetch_hourly_forecast(lat, lon) is not None            # cek sekali agar tidak menunggu timeout berkali-kali
    lokal0 = now_utc + timedelta(hours=tz)
    baris = []
    for i in range(n):
        d = (lokal0 + timedelta(days=i)).date()
        when = datetime(d.year, d.month, d.day, jam) - timedelta(hours=tz)
        if when < now_utc - timedelta(hours=1):                    # malam ini sudah lewat pukul `jam`: pakai sekarang
            when = now_utc + timedelta(minutes=5)
        jd = ac.jd_from_jdn(ac.to_jdn(when.year, when.month, when.day), when.hour + when.minute / 60.0)
        elong = ac.elongation(jd)
        illum = planner.moon_illumination(when)
        alt = planner.moon_altitude_at(when, lat, lon)
        row = {'tanggal': d, 'fase': ac.moon_phase_name(elong), 'terang': illum, 'tinggi_bulan': alt, 'skor': None, 'kondisi': None, 'awan': None, 'hujan': None}
        if ada:
            w = W.get_weather_at(lat, lon, when, now_utc)
            if w.get('available'):
                f = planner.calculate_observation_feasibility(w, 'naked_eye', 'General', illum, False, alt)
                row.update(skor=f['score'], kondisi=w.get('condition'), awan=w.get('cloud_cover_pct'), hujan=w.get('precipitation_prob'),
                           jenis=w.get('kind'))
        baris.append(row)
    return {'prakiraan': ada, 'malam': baris}


def event_katalog(lat, lon, tz, now_utc, days=7, limit=5):
    """Event katalog yang dapat diamati (diberi skor). None bila katalog belum dibuat atau gagal."""
    try:
        from flask import current_app

        from catalog import service as S
        doc = S.load(current_app.config['CATALOG_DIR'])
        if doc is None:
            return None
        return planner.plan(doc, lat, lon, 'pinggiran', tz, 'all', now_utc, days, limit)
    except Exception:
        return None
