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
                raise F.InputError(f'{nama} harus berupa bilangan bulat.') from None
        hasil = F.konversi(data.get('source', 'masehi'), angka('year', 'Tahun'), angka('month', 'Bulan'), angka('day', 'Tanggal'),
                           int(data.get('epoch', 2) or 2), int(data.get('kabisat', 2) or 2))
        return jsonify({'status': 'success', **hasil})
    except F.InputError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@calendar_bp.route('/api/compare')
def compare():
    """Perbandingan kalender Hijriah (4 kriteria hisab + 4 aritmetis) & Jawa untuk satu bulan penuh di sekitar `date`.
    Opsi: sk=0|1 (puasa Senin-Kamis), ab=0|1 (Ayyamulbid)."""
    from datetime import date
    try:
        d = F.parse_tanggal(request.args.get('date'), date.today())
        flag = lambda k: request.args.get(k, '1') not in ('0', 'false', 'off')
        return jsonify({'status': 'success', **F.perbandingan_kalender(d, flag('sk'), flag('ab'))})
    except F.InputError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
