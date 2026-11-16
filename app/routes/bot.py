from flask import Blueprint, render_template, request, jsonify

bot_bp = Blueprint('bot', __name__)

@bot_bp.route('/')
def index():
    """AstroBot chat interface and knowledge center."""
    return render_template('bot/index.html')

@bot_bp.route('/api/chat', methods=['POST'])
def chat():
    """Chatbot query endpoint."""
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'status': 'error', 'reply': 'Mohon masukkan pertanyaan Anda.'}), 400

    # Fallback initial response / rule-based trigger
    reply = (
        f"Halo! Saya AstroBot. Saya menerima pertanyaan Anda: '{message}'. "
        "Knowledge base dan modul retrieval sedang diinisialisasi."
    )
    
    return jsonify({
        'status': 'success',
        'reply': reply
    })
