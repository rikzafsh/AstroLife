"""Zona waktu pengamat: dari bujur (Indonesia: WIB/WITA/WIT; di luar itu dibulatkan bujur/15)."""


def tz_from_lon(lon: float) -> float:
    if 95 <= lon < 115:
        return 7.0
    if 115 <= lon < 130:
        return 8.0
    if 130 <= lon <= 141.5:
        return 9.0
    return float(round(lon / 15.0))


def tz_label(tz: float) -> str:
    names = {7.0: 'WIB', 8.0: 'WITA', 9.0: 'WIT'}
    if float(tz) in names:
        return names[float(tz)]
    h = f"{abs(tz):g}"
    return f"UTC{'+' if tz >= 0 else '-'}{h}"
