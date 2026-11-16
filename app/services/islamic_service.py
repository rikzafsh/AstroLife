"""
Islamic Astronomy & Timekeeping Service Module
Ready to integrate ported JS calculations for:
- Waktu salat (Subuh, Terbit, Dhuha, Dzuhur, Ashar, Maghrib, Isya)
- Kalender puasa sunah (Senin-Kamis, Ayyamul Bidh, dll.)
- Rasydulqiblat tahunan (27-28 Mei & 15-16 Juli)
- Rasydulqiblat harian (berdasarkan azimuth matahari & koordinat lokal)
"""

def get_annual_rasydulqiblat(year: int = 2026) -> list:
    """Returns the two annual global Rasydulqiblat (Istiwa A'zham) occurrences."""
    return [
        {
            'event': "Rasydulqiblat Tahunan I",
            'date': f"{year}-05-27/28",
            'time_utc': "09:18 UTC",
            'time_wib': "16:18 WIB",
            'description': "Matahari melintas tepat di atas Ka'bah (deklinasi ~21° 25' LU). Bayangan benda tegak lurus mengarah ke kiblat."
        },
        {
            'event': "Rasydulqiblat Tahunan II",
            'date': f"{year}-07-15/16",
            'time_utc': "09:27 UTC",
            'time_wib': "16:27 WIB",
            'description': "Peristiwa kedua Matahari tepat di zenit Ka'bah saat bergerak ke selatan."
        }
    ]

def calculate_daily_rasydulqiblat(lat: float, lon: float, date_str: str) -> dict:
    """
    Placeholder for daily rashdulqiblah calculation (azimuth matahari = azimuth kiblat).
    To be populated from the ported JS falak module.
    """
    return {
        'coords': {'lat': lat, 'lon': lon},
        'date': date_str,
        'status': 'awaiting_js_port'
    }
