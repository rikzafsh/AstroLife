"""
Keterlihatan sebuah event dari lokasi pengamat tertentu.

Masukan : event katalog + (lat, lon) + batas magnitudo mata telanjang (langit lokasi).
Keluaran: status (di atas/bawah ufuk, siang, senja), waktu terbaik, ketinggian, magnitudo, dan alat yang disarankan.

ATURAN (semuanya eksplisit agar dapat dijelaskan di laporan):
 1. Posisi benda dihitung dari mesin posisi (RA/Dec) -> ketinggian topocentris (Bulan dengan paralaks, refraksi dasar).
 2. Jendela penilaian: rentang event bila ada (gerhana, okultasi), selain itu +-10 jam (+-14 jam hujan meteor) dari puncak.
 3. Sampel waktu (30 menit) layak bila SEMUA benda penentu berada >= 5 derajat di atas ufuk dan Matahari <= -6 derajat
    (kecuali gerhana Matahari: Matahari harus di atas ufuk). Dipilih sampel dengan ketinggian terendah-benda terbesar,
    mengutamakan langit gelap (Matahari <= -12 derajat).
 4. Alat: magnitudo benda TERREDUP (selain Bulan/Matahari) dibandingkan batas magnitudo efektif:
        mata telanjang = batas langit - gangguan Bulan - kehilangan akibat senja
        binokular 9,0 | teleskop kecil 11,0 | teleskop 4-inci 12,5 | teleskop besar > 12,5   (dikurangi gangguan Bulan)
    Gangguan Bulan = 1,5 mag x fraksi terang Bulan x min(1, tinggi Bulan / 20 derajat), bila Bulan bukan objek event.
"""
import math
from datetime import datetime, timedelta

from prototype import find_events as F
from prototype.engine import E
from catalog.events import iso

INSTRUMENTS = ['naked_eye', 'binoculars', 'small_telescope', 'telescope_4inch', 'large_telescope']
INSTRUMENT_LABEL = {'naked_eye': 'Mata Telanjang', 'binoculars': 'Binokular', 'small_telescope': 'Teleskop Kecil',
                    'telescope_4inch': 'Teleskop 4-Inci', 'large_telescope': 'Teleskop Besar', None: 'Tidak teramati'}
OPTIC_LIMITS = {'binoculars': 9.0, 'small_telescope': 11.0, 'telescope_4inch': 12.5}
DEFAULT_NAKED_LIMIT = 5.0           # langit pinggiran kota; kota besar ~4,0; langit gelap ~6,0
MIN_ALT = 5.0                       # batas praktis (pohon/gedung/kabut ufuk)
PREF_MIN_ALT = 10.0                 # waktu peristiwa dipakai apa adanya hanya bila setinggi ini; kalau tidak cari waktu lebih baik

STATE_LABEL = {'visible': 'Terlihat jelas', 'twilight': 'Saat senja/fajar', 'low': 'Rendah di ufuk',
               'daylight': 'Siang hari', 'below_horizon': 'Di bawah ufuk', 'not_observable': 'Tidak teramati'}


def alt_az(ra: float, dec: float, jd: float, lat: float, lon: float):
    """(ketinggian geometris, azimuth dari utara searah jarum jam) dalam derajat."""
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360.0
    lha = math.radians(gmst + lon - ra)
    phi, d = math.radians(lat), math.radians(dec)
    alt = math.asin(max(-1.0, min(1.0, math.sin(phi) * math.sin(d) + math.cos(phi) * math.cos(d) * math.cos(lha))))
    az = math.degrees(math.atan2(-math.sin(lha) * math.cos(d), math.cos(phi) * math.sin(d) - math.sin(phi) * math.cos(d) * math.cos(lha)))
    return math.degrees(alt), az % 360.0


def _refraction_deg(alt: float) -> float:
    """Refraksi atmosfer (Saemundsson), derajat; 0 bila terlalu jauh di bawah ufuk."""
    if alt < -1.0:
        return 0.0
    return (1.02 / math.tan(math.radians(alt + 10.3 / (alt + 5.11)))) / 60.0


def body_alt(body: str, jd: float, lat: float, lon: float) -> float:
    """Ketinggian tampak (dengan refraksi) benda dari lokasi; Bulan topocentris."""
    ra, dec = E.topo_moon(jd, lat, lon) if body == 'moon' else E.eq(body, jd)
    alt, _ = alt_az(ra, dec, jd, lat, lon)
    return alt + _refraction_deg(alt)


def sun_alt(jd: float, lat: float, lon: float) -> float:
    ra, dec = E.eq('sun', jd)
    return alt_az(ra, dec, jd, lat, lon)[0]


def moon_illumination(jd: float) -> float:
    e = math.radians((E.ecl('moon', jd)[0] - E.ecl('sun', jd)[0]) % 360.0)
    return (1 - math.cos(e)) / 2.0


# ---------------------------------------------------------------------------
SLOW_CATEGORIES = {'elongasi', 'oposisi', 'fase_planet', 'hujan_meteor'}


def _window(ev: dict):
    """Jendela penilaian. Event cepat (Bulan, okultasi, gerhana): +-10 jam. Event lambat (planet, hujan meteor,
    konjungsi planet-planet) berlangsung berhari-hari, jadi dinilai pada malam terbaik dalam +-36 jam."""
    c = F_jd(ev['time_utc'])
    d = ev.get('details', {})
    if ev['category'] == 'gerhana_bulan' and d.get('umbra_mulai_utc'):          # fase penumbra nyaris tak terlihat mata
        return F_jd(d['umbra_mulai_utc']), F_jd(d['umbra_selesai_utc'])
    if ev.get('start_utc') and ev.get('end_utc'):
        return F_jd(ev['start_utc']), F_jd(ev['end_utc'])
    slow = ev['category'] in SLOW_CATEGORIES or (ev['category'] == 'konjungsi' and 'moon' not in ev['bodies'])
    half = 36 / 24 if slow else 10 / 24
    return c - half, c + half


def F_jd(iso_str: str) -> float:
    d = datetime.strptime(iso_str[:19], '%Y-%m-%dT%H:%M:%S')
    return 2451545.0 + (d - datetime(2000, 1, 1, 12)).total_seconds() / 86400.0


def _samples(t0: float, t1: float, step_min: int = 30):
    n = max(2, int((t1 - t0) * 1440 / step_min) + 1)
    return [t0 + i * (t1 - t0) / (n - 1) for i in range(n)]


def _wib(utc_iso: str, tz: float) -> str:
    return (datetime.strptime(utc_iso[:19], '%Y-%m-%dT%H:%M:%S') + timedelta(hours=tz)).strftime('%Y-%m-%d %H:%M')


def _instrument(faint_mag, naked_limit: float, glare: float, twilight_loss: float, min_level=None):
    """Alat minimum untuk magnitudo tertentu. Mengembalikan (kunci, batas efektif mata telanjang)."""
    eff_naked = naked_limit - glare - twilight_loss
    ladder = [('naked_eye', eff_naked)] + [(k, OPTIC_LIMITS[k] - glare) for k in ('binoculars', 'small_telescope', 'telescope_4inch')]
    chosen = 'large_telescope'
    for key, lim in ladder:
        if faint_mag is None or faint_mag <= lim:
            chosen = key
            break
    if min_level and INSTRUMENTS.index(min_level) > INSTRUMENTS.index(chosen):
        chosen = min_level
    return chosen, eff_naked


def evaluate(ev: dict, lat: float, lon: float, naked_limit: float = DEFAULT_NAKED_LIMIT, tz: float = 7.0) -> dict:
    """Keterlihatan event di (lat, lon). Waktu keluaran (waktu_terbaik) dalam zona tz (jam)."""
    cat, kind = ev['category'], ev['kind']
    t_peak = F_jd(ev['time_utc'])
    bodies = list(ev['bodies'])
    mags = {}
    for b in bodies:
        if b != 'sun':
            m = E.apparent_mag(b, t_peak)
            if m is not None:
                mags[b] = round(m, 2)

    out = {'bodies_mag': mags, 'naked_limit': naked_limit, 'notes': []}

    # --- kasus khusus: Bulan baru tidak terlihat -------------------------------------------------------------
    if kind == 'new_moon':
        out.update(state='not_observable', state_label=STATE_LABEL['not_observable'], instrument=None,
                   instrument_label=INSTRUMENT_LABEL[None], best_time=None, min_altitude=None, observable=False,
                   headline='Bulan tidak terlihat (sisi gelap menghadap Bumi)',
                   reason='Sisi Bulan yang terang menghadap menjauhi Bumi; Bulan tidak terlihat.')
        return out

    solar = cat == 'gerhana_matahari'
    # benda penentu posisi: seluruh benda event; hujan meteor: titik radian
    if cat == 'hujan_meteor':
        rr, rd = ev['details']['radian_ra'], ev['details']['radian_dec']
        alt_fn = lambda t: alt_az(rr, rd, t, lat, lon)[0]
    else:
        pos_bodies = bodies or ['moon']
        alt_fn = lambda t: min(body_alt(b, t, lat, lon) for b in pos_bodies)

    t0, t1 = _window(ev)
    if cat == 'okultasi':
        lo = _local_occultation(ev, lat, lon)
        out['local_occultation'] = lo
        if lo['terjadi']:
            t0, t1 = F_jd(lo['hilang_utc']), F_jd(lo['muncul_utc'])                           # nilai tepat saat okultasi terjadi
    slow = cat in SLOW_CATEGORIES or (cat == 'konjungsi' and 'moon' not in bodies)
    t_pref = t_peak                                              # waktu acuan: puncak event ...
    if cat == 'okultasi' and out['local_occultation']['terjadi']:
        t_pref = F_jd(out['local_occultation']['waktu_terdekat_utc'])    # ... atau titik terdekat di lokasi
    times = _samples(t0, t1)
    if not slow and t0 <= t_pref <= t1:
        times = sorted(times + [t_pref])
    rows = []
    for t in times:
        rows.append({'t': t, 'alt': alt_fn(t), 'sun': sun_alt(t, lat, lon)})
    pref = next((r for r in rows if r['t'] == t_pref), None) if not slow else None

    # --- pemilihan sampel terbaik ---------------------------------------------------------------------------
    if solar:
        usable = [r for r in rows if r['alt'] >= MIN_ALT and r['sun'] > 0]
        best = pref if (pref and pref in usable) else max(usable or rows, key=lambda r: r['alt'])
        state = 'daylight' if usable else ('below_horizon' if best['alt'] < 0 else 'low')
    elif pref is not None and pref['alt'] >= PREF_MIN_ALT and pref['sun'] <= -6:
        # Saat peristiwa itu sendiri dapat diamati: itulah waktu yang dinilai (bukan titik tertinggi di malam itu)
        best = pref
        state = 'twilight' if pref['sun'] > -12 else ('visible' if pref['alt'] >= 15 else 'low')
    else:
        dark = [r for r in rows if r['alt'] >= MIN_ALT and r['sun'] <= -12]
        dusk = [r for r in rows if r['alt'] >= MIN_ALT and -12 < r['sun'] <= -6]
        if dark:
            best = max(dark, key=lambda r: r['alt'])
            state = 'visible' if best['alt'] >= 15 else 'low'
        elif dusk:
            best = max(dusk, key=lambda r: r['alt'])
            state = 'twilight'
        else:
            up = [r for r in rows if r['alt'] >= MIN_ALT]
            if up:
                best, state = max(up, key=lambda r: r['alt']), 'daylight'
            else:
                best = max(rows, key=lambda r: r['alt'])
                state = 'low' if best['alt'] >= 0 and best['sun'] <= -6 else 'below_horizon'

    # --- gangguan Bulan & alat -------------------------------------------------------------------------------
    moon_is_object = 'moon' in bodies
    illum = moon_illumination(best['t'])
    m_alt = body_alt('moon', best['t'], lat, lon)
    glare = 0.0 if moon_is_object or solar else 1.5 * illum * max(0.0, min(1.0, m_alt / 20.0))
    twilight_loss = max(0.0, min(3.0, (best['sun'] + 18.0) / 12.0 * 3.0)) if best['sun'] > -18 and not solar else 0.0

    faint = [mags[b] for b in bodies if b not in ('moon', 'sun') and b in mags]
    faint_mag = max(faint) if faint else None
    min_level = 'small_telescope' if kind == 'dichotomy' else None
    instrument, eff_naked = _instrument(faint_mag, naked_limit, glare, twilight_loss if state != 'daylight' else 0.0, min_level)
    if cat in ('gerhana_bulan', 'hujan_meteor') or solar:
        instrument, eff_naked = 'naked_eye', naked_limit

    best_utc = iso(best['t'])
    out.update(state=state, state_label=STATE_LABEL[state], instrument=instrument, instrument_label=INSTRUMENT_LABEL[instrument],
               best_time_utc=best_utc, best_time_local=_wib(best_utc, tz), min_altitude=round(best['alt'], 1),
               sun_altitude=round(best['sun'], 1), moon_illumination_pct=round(illum * 100), moon_altitude=round(m_alt),
               moon_glare_mag=round(glare, 2), required_magnitude=faint_mag, effective_naked_limit=round(eff_naked, 2))

    # --- keterangan --------------------------------------------------------------------------------------------
    if state == 'below_horizon':
        out['reason'] = 'Benda berada di bawah ufuk sepanjang jendela pengamatan dari lokasi ini.'
    elif state == 'low':
        out['reason'] = f"Paling tinggi hanya {best['alt']:.0f}° di atas ufuk (batas praktis {MIN_ALT:.0f}°)."
    elif state == 'daylight':
        out['reason'] = 'Terjadi saat langit masih terang' + ('.' if solar else '; hanya benda sangat terang yang mungkin terlihat, perlu bantuan alat.')
    elif state == 'twilight':
        out['reason'] = 'Terlihat pada senja/fajar; langit belum sepenuhnya gelap, objek redup tersamarkan.'
    else:
        out['reason'] = f"Ketinggian terbaik {best['alt']:.0f}° dengan langit gelap (Matahari {best['sun']:.0f}°)."
    if cat == 'okultasi':
        lo = out['local_occultation']
        out['notes'].append(
            f"Okultasi TERJADI di lokasi ini (hilang {_wib(lo['hilang_utc'], tz)}, muncul {_wib(lo['muncul_utc'], tz)})." if lo['terjadi'] else
            f"Dari lokasi ini Bulan hanya lewat {lo['jarak_min_deg']:.2f}° dari objek tanpa menutupinya; okultasi terlihat di wilayah lain.")
    if glare >= 0.3:
        out['notes'].append(f"Cahaya Bulan ({illum * 100:.0f}% terang, tinggi {m_alt:.0f}°) mengurangi batas magnitudo ±{glare:.1f}.")
    if solar:
        out['notes'].append('WAJIB memakai filter surya bersertifikat; jangan menatap Matahari langsung.')

    # --- tambahan per kategori ---------------------------------------------------------------------------------
    if cat == 'hujan_meteor':
        h = max(0.0, best['alt'])
        zhr = ev['details']['zhr']
        lim = naked_limit - glare - twilight_loss
        rate = zhr * math.sin(math.radians(h)) * (2.5 ** -(max(0.0, 6.5 - lim)))
        out['expected_rate_per_hour'] = round(rate)
        out['notes'].append(f"Perkiraan {rate:.0f} meteor/jam di lokasi ini (ZHR {zhr} x sin tinggi radian x koreksi batas magnitudo; r=2,5).")
    if solar:
        out['local_eclipse'] = _local_solar(ev, lat, lon)
    _finalize(out, ev, tz)
    return out


def _finalize(out: dict, ev: dict, tz: float) -> None:
    """Menetapkan satu bendera `observable` yang jujur dan ringkasan `headline` untuk antarmuka."""
    state, cat = out['state'], ev['category']
    ok = state in ('visible', 'twilight') or (state == 'low' and (out.get('min_altitude') or -99) >= MIN_ALT)
    headline = None
    if cat == 'gerhana_matahari':
        le = out['local_eclipse']
        ok = bool(le['terlihat'])
        headline = (f"Gerhana {le['jenis_lokal']} terlihat dari lokasi (magnitudo {le['magnitudo_lokal']})" if ok
                    else 'Gerhana tidak terlihat dari lokasi ini (jalur/wilayah lain)')
    elif cat == 'okultasi' and not out['local_occultation']['terjadi']:
        ok = False
        headline = f"Bulan hanya lewat {out['local_occultation']['jarak_min_deg']:.2f}° dari objek; okultasi terlihat di wilayah lain"
    elif cat == 'okultasi':
        lo = out['local_occultation']
        headline = f"Terjadi di lokasi Anda: hilang {_wib(lo['hilang_utc'], tz)[11:]}, muncul {_wib(lo['muncul_utc'], tz)[11:]}"
    if headline is None:
        best = out.get('best_time_local') or ''
        same_day = best[:10] == _wib(ev['time_utc'], tz)[:10]
        best_txt = best[11:] if same_day else f"{best[8:10]}/{best[5:7]} {best[11:]}"
        headline = (f"Terbaik {best_txt} · tinggi {out['min_altitude']:.0f}° · {out['instrument_label']}" if ok
                    else out['state_label'] + (f" ({out['reason']})" if state in ('below_horizon', 'low') else ''))
    out['observable'], out['headline'] = bool(ok), headline


def _local_occultation(ev: dict, lat: float, lon: float) -> dict:
    """Apakah Bulan benar-benar menutupi objek DARI lokasi ini (topocentris)? Jam hilang/muncul bila ya."""
    other = [b for b in ev['bodies'] if b != 'moon'][0]
    t0, t1 = _window(ev)
    f = lambda t: E.separation(*E.topo_moon(t, lat, lon), *E.eq(other, t))
    found = F.find_minima(f, t0, t1, 1 / 720)
    if not found:                                   # minimum di tepi jendela: ambil sampel terkecil
        tm = min(_samples(t0, t1, 2), key=f)
        found = [(tm, f(tm))]
    tm, smin = min(found, key=lambda x: x[1])
    sd = E.moon_semidiameter_deg(tm)
    res = {'terjadi': bool(smin < sd), 'jarak_min_deg': round(smin, 3), 'waktu_terdekat_utc': iso(tm), 'semidiameter_bulan_deg': round(sd, 3)}
    if res['terjadi']:
        g = lambda t: f(t) - sd
        a = F.find_roots(g, tm - 0.1, tm, 1 / 1440, 5)
        b = F.find_roots(g, tm, tm + 0.1, 1 / 1440, 5)
        res['hilang_utc'] = iso(a[0]) if a else iso(tm - 0.02)
        res['muncul_utc'] = iso(b[0]) if b else iso(tm + 0.02)
    return res


def _local_solar(ev: dict, lat: float, lon: float) -> dict:
    """Keadaan lokal gerhana Matahari: pindai +-4 jam, jarak topocentris Bulan-Matahari terkecil."""
    t_peak = F_jd(ev['time_utc'])
    best = None
    for t in _samples(t_peak - 4 / 24, t_peak + 4 / 24, 2):
        ra, dec = E.topo_moon(t, lat, lon)
        s = E.separation(ra, dec, *E.eq('sun', t))
        if best is None or s < best[0]:
            best = (s, t)
    s, t = best
    ss, sm = E.sun_semidiameter_deg(t), E.moon_semidiameter_deg(t)
    alt = sun_alt(t, lat, lon)
    magnitude = max(0.0, (ss + sm - s) / (2 * ss))
    seen = magnitude > 0 and alt > 0
    return {'terlihat': bool(seen), 'magnitudo_lokal': round(magnitude, 3), 'waktu_maks_utc': iso(t), 'tinggi_matahari': round(alt, 1),
            'jenis_lokal': None if not seen else ('total/cincin' if s < abs(sm - ss) else 'sebagian')}
