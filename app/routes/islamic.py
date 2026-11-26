"""Astronomi Islam: jadwal salat, arah kiblat, rasydulqiblat (dihitung app/persis), dan puasa sunah (Hijriah aritmetis)."""
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, render_template, request

from app.persis import salat
from app.services import falak_service as F
from app.services import islamic_service as I

islamic_bp = Blueprint('islamic', __name__)


def _lokasi():
    return F.parse_lokasi(request.args, current_app.config['DEFAULT_LOCATION'])


def _hari_ini(lok):
    return (datetime.now(timezone.utc) + timedelta(hours=lok['tz'])).date()


def _error(e, code=400):
    return jsonify({'status': 'error', 'message': str(e)}), code


@islamic_bp.route('/')
def index():
    metode = [{'kunci': k, 'nama': m.name} for k, m in salat.METODE.items()]
    return render_template('islamic/index.html', metode=metode)


@islamic_bp.route('/api/prayer-times')
def prayer_times():
    try:
        lok = _lokasi()
        d = F.parse_tanggal(request.args.get('date'), _hari_ini(lok))
        ihtiyat = int(F._float(request.args.get('ihtiyat'), 'Ihtiyat', 0, 10, 2))
        imsak = int(F._float(request.args.get('imsak'), 'Imsak', 0, 60, 10))
        return jsonify({'status': 'success', **F.jadwal_salat(d, lok, F.parse_metode(request.args.get('method')), ihtiyat, imsak)})
    except F.InputError as e:
        return _error(e)


@islamic_bp.route('/api/qibla')
def qibla():
    try:
        return jsonify({'status': 'success', **F.info_kiblat(_lokasi())})
    except F.InputError as e:
        return _error(e)


@islamic_bp.route('/api/rasydulqiblat')
def rasydulqiblat():
    try:
        lok = _lokasi()
        d = F.parse_tanggal(request.args.get('date'), _hari_ini(lok))
        hari = int(F._float(request.args.get('days'), 'Jumlah hari', 1, 31, 7))
        tahun = request.args.get('year')
        tahun = int(F._float(tahun, 'Tahun', 1, 3000)) if tahun else None
        n = int(F._float(request.args.get('years'), 'Jumlah tahun', 1, 10, 1))
        return jsonify({'status': 'success', **F.rasydulqiblat(d, lok, request.args.get('qibla', 'vincenty'), hari, tahun, n)})
    except F.InputError as e:
        return _error(e)


@islamic_bp.route('/api/puasa')
def puasa():
    try:
        lok = _lokasi()
        d = F.parse_tanggal(request.args.get('date'), _hari_ini(lok))
        n = int(F._float(request.args.get('days'), 'Jumlah hari', 1, 120, 45))
        k = request.args.get('kriteria') or 'aritmetis'
        if k not in I.KRITERIA_PUASA:
            raise F.InputError('Kriteria Hijriah tidak dikenal.')
        if k != 'aritmetis' and not 1700 <= d.year <= 2300:
            raise F.InputError('Hisab kriteria tersedia untuk tahun 1700–2300 M.')
        nama = F.nama_kriteria(k)
        catatan = ('Hijriah aritmetis (hisab urfi); awal Ramadan/Syawal/Zulhijah resmi dapat berbeda 1–2 hari.' if k == 'aritmetis' else
                   f'Tanggal Hijriah menurut kriteria {nama} (hisab ijtimak, tinggi hilal, dan Bulan terbenam di lokasi acuan kriteria itu); '
                   'penetapan resmi dapat berbeda 1–2 hari.')
        return jsonify({'status': 'success', 'dari': d.isoformat(), 'hari': n, 'kriteria': k, 'kriteria_nama': nama,
                        'jadwal': I.fasting_schedule(d, n, k), 'catatan': catatan})
    except F.InputError as e:
        return _error(e)
