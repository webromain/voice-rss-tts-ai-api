from flask import Flask, request, jsonify, send_file
import requests
import os
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import io

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration VoiceRSS - Lecture depuis le fichier .env
VOICERSS_API_KEY = os.getenv('rss_api_key', 'rss_key')
VOICERSS_API_URL = "http://api.voicerss.org/"
API_KEY = os.getenv('api_key', 'api_key')  # Clé API pour ton API

# Crée une instance de l'application Flask
app = Flask(__name__)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Décorateur pour vérifier la clé API
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key')
        if key != API_KEY:
            return jsonify({'error': 'Clé API invalide'}), 401
        return f(*args, **kwargs)
    return decorated

def text_to_speech(text, lang='en-us'):
    """
    Convertit du texte en audio en utilisant l'API VoiceRSS
    """
    try:
        params = {
            'key': VOICERSS_API_KEY,
            'src': text,
            'hl': lang,
            'r': 0,  # Vitesse de lecture (0 = normal)
            'c': 'mp3',  # Format de sortie
            'f': '44khz_16bit_mono'  # Qualité audio
        }
        
        response = requests.get(VOICERSS_API_URL, params=params)
        response.raise_for_status()
        
        return response.content  # Retourner le fichier audio brut
    except requests.RequestException as e:
        raise requests.RequestException(f"Erreur VoiceRSS: {str(e)}")

@app.route('/', methods=['GET'])
def home():
    return "API Flask pour text-to-speech avec VoiceRSS"

@app.route('/tts', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")  # Max 10 requêtes par minute
def tts():
    try:
        # Récupérer les données envoyées en POST
        data = request.get_json()
        text = data.get('text', '').strip()
        lang = data.get('lang', 'en-us')
        
        # Validation : limiter à 500 caractères
        if not text:
            return jsonify({'error': 'Le texte est vide'}), 400
        if len(text) > 500:
            return jsonify({'error': 'Le texte dépasse 500 caractères'}), 400
        
        # Récupérer l'audio
        audio_content = text_to_speech(text, lang)
        
        # Retourner le fichier audio directement en téléchargement
        return send_file(
            io.BytesIO(audio_content),
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='audio.mp3'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download/<int:request_id>', methods=['GET'])
@require_api_key
@limiter.limit("30 per minute")
def download_audio(request_id):
    """
    Route sécurisée pour télécharger l'audio sans exposer la clé API VoiceRSS
    """
    try:
        text = request.args.get('text', '')
        lang = request.args.get('lang', 'en-us')
        
        # Vérifier que le request_id correspond
        if hash(text + lang) % 100000 != request_id:
            return jsonify({'error': 'Requête invalide'}), 400
        
        # Récupérer l'audio
        audio_content = text_to_speech(text, lang)
        
        # Retourner le fichier audio directement
        return send_file(
            io.BytesIO(audio_content),
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='audio.mp3'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
if __name__ == '__main__':
 app.run(debug=False, port=5000) # Démarre le serveur sur le port 5000