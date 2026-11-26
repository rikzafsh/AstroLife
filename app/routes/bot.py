from flask import Blueprint, jsonify, render_template, request

from app.bot import ambil_artikel, daftar_artikel, jawab, saran_awal

bot_bp = Blueprint('bot', __name__)


@bot_bp.route('/')
def index():
    """Antarmuka AstroBot dan pusat artikel."""
    return render_template('bot/index.html')


@bot_bp.route('/api/chat', methods=['POST'])
@bot_bp.route('/api/bot', methods=['POST'])
def chat():
    """Tanya AstroBot. Masukan: {message, context:{lokasi,salat,hijriah}, slots}. Keluaran: lihat app/bot/mesin.py."""
    data = request.get_json(silent=True) or {}
    pesan = str(data.get('message') or '').strip()
    if not pesan:
        return jsonify({'status': 'error', 'reply': 'Mohon tuliskan pertanyaan Anda.', 'intent': 'kosong', 'slots': {}, 'cards': [],
                        'links': [], 'sources': [], 'suggestions': saran_awal()[:4]}), 400
    return jsonify(jawab(pesan, data.get('context'), data.get('slots')))


@bot_bp.route('/api/saran')
def saran():
    return jsonify({'status': 'success', 'saran': saran_awal()})


@bot_bp.route('/api/artikel')
def artikel_daftar():
    return jsonify({'status': 'success', 'artikel': daftar_artikel()})


@bot_bp.route('/api/artikel/<aid>')
def artikel_satu(aid):
    a = ambil_artikel(aid)
    if not a:
        return jsonify({'status': 'error', 'message': 'Artikel tidak ditemukan.'}), 404
    return jsonify({'status': 'success', 'artikel': a})
