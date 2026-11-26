"""Lab Kalender: konversi Masehi, Hijriah (aritmetis), Jawa, dan Jyotiṣa."""
from flask import Blueprint, jsonify, render_template, request

from app.services import falak_service as F

calendar_bp = Blueprint('calendar', __name__)


@calendar_bp.route('/')
def index():
    return render_template('calendar/index.html')


@calendar_bp.route('/api/convert', methods=['GET', 'POST'])
def convert():
    """Masukan: sumber (masehi|hijriah|jawa), year, month, day; opsional epoch (1|2) dan kabisat (1..4) untuk Hijriah."""
    data = request.get_json(silent=True) if request.method == 'POST' else request.args
    data = data or {}
    try:
        def angka(k, nama):
            try:
                return int(data[k])
            except (KeyError, TypeError, ValueError):
                raise F.InputError(f'{nama} harus berupa bilangan bulat.')
        hasil = F.konversi(data.get('source', 'masehi'), angka('year', 'Tahun'), angka('month', 'Bulan'), angka('day', 'Tanggal'),
                           int(data.get('epoch', 2) or 2), int(data.get('kabisat', 2) or 2))
        return jsonify({'status': 'success', **hasil})
    except F.InputError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
