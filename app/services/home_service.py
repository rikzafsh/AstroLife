"""Ringkasan 'hari ini' untuk Beranda: tanggal berbagai kalender + fase Bulan (dihitung, bukan statis)."""
import math
from datetime import datetime, timedelta

from app.services import astro_core as ac
from app.services import calendar_service as cs

SYNODIC_MONTH = 29.530588
PHASE_EMOJI = ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘']      # indeks sama dengan astro_core.moon_phase_name


def today_summary(now_utc: datetime, tz: float) -> dict:
    """Tanggal lokal (zona tz) dan keadaan Bulan pada now_utc."""
    local = now_utc + timedelta(hours=tz)
    jdn = ac.to_jdn(local.year, local.month, local.day)
    greg, hij, jaw = cs.gregorian_info(jdn), cs.hijri_info(jdn), cs.javanese_info(jdn)
    jd = ac.jd_from_jdn(ac.to_jdn(now_utc.year, now_utc.month, now_utc.day), now_utc.hour + now_utc.minute / 60.0)
    elong = ac.elongation(jd)
    illum = (1 - math.cos(math.radians(elong))) / 2.0
    idx = int(((elong + 22.5) % 360) // 45)
    return {
        'tanggal_teks': greg['teks'], 'weton': jaw['weton'], 'wuku': jaw['wuku'], 'tahun_jawa': f"{jaw['tanggal']} {jaw['bulan']} {jaw['tahun_windu']} {jaw['tahun']} AJ",
        'hijriah': hij['teks'], 'jam_lokal': local.strftime('%H:%M'),
        'bulan': {'fase': ac.moon_phase_name(elong), 'emoji': PHASE_EMOJI[idx], 'terang_pct': round(illum * 100),
                  'umur_hari': round(elong / 360.0 * SYNODIC_MONTH, 1), 'arah': 'menuju purnama' if elong < 180 else 'menuju bulan baru'},
    }
