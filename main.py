import os
import asyncio
import time
import re
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import edge_tts

app = Flask(__name__)
CORS(app)
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

def tiri_soomaali(n):
    n = int(n)
    if n == 0: return "eber"
    unugyada = ["", "kow", "laba", "saddex", "afar", "shan", "lix", "toddoba", "siddeed", "sagaal"]
    tobaneeyada = ["", "toban", "labaatan", "soddon", "afartan", "konton", "lixdan", "todobaatan", "sideetan", "sagaashan"]

    def badal(n, is_leading=False):
        if n < 10:
            if n == 1 and is_leading: return "hal"
            return unugyada[n]
        elif n < 20:
            if n == 10: return "toban"
            return f"{unugyada[n%10]} iyo toban"
        elif n < 100:
            harre = n % 10
            return f"{tobaneeyada[n//10]}" + (f" iyo {unugyada[harre]}" if harre > 0 else "")
        elif n < 1000:
            boqol = n // 100
            harre = n % 100
            bilow = "boqol" if boqol == 1 else f"{unugyada[boqol]} boqol"
            return bilow + (f" iyo {badal(harre)}" if harre > 0 else "")
        elif n < 1000000:
            kun = n // 1000
            harre = n % 1000
            bilow = "kun" if kun == 1 else f"{badal(kun, True)} kun"
            return bilow + (f" iyo {badal(harre)}" if harre > 0 else "")
        elif n < 1000000000:
            milyan = n // 1000000
            harre = n % 1000000
            bilow = "hal milyan" if milyan == 1 else f"{badal(milyan, True)} milyan"
            return bilow + (f" iyo {badal(milyan, True)} milyan" if harre > 0 else "")
        else:
            bilyan = n // 1000000000
            harre = n % 1000000000
            bilow = "hal bilyan" if bilyan == 1 else f"{badal(bilyan, True)} bilyan"
            return bilow + (f" iyo {badal(harre)}" if harre > 0 else "")

    return badal(n, True)

def hagaaji_qoraalka(text):
    text = text.lower()
    text = text.replace(",", "")

    def process_float_or_int(val):
        if '.' in val:
            bidix, midig = val.split('.')
            return f"{tiri_soomaali(bidix)} dhibic {tiri_soomaali(midig)}"
        return tiri_soomaali(val)

    def convert_dollars(match):
        num_str = match.group(1)
        return f"{process_float_or_int(num_str)} doolar"

    text = re.sub(r'\$(\d+\.?\d*)', convert_dollars, text)
    text = re.sub(r'(\d+\.?\d*)\$', convert_dollars, text)

    def convert_kmb(match):
        num = float(match.group(1))
        unit = match.group(2)
        if unit == 'k': return str(int(num * 1000))
        if unit == 'm': return str(int(num * 1000000))
        if unit == 'b': return str(int(num * 1000000000))
        return match.group(0)

    text = re.sub(r'(\d+\.?\d*)(k|m|b)\b', convert_kmb, text)

    def process_percent(match):
        val = match.group(1)
        return "boqolkiiba " + process_float_or_int(val)

    text = re.sub(r'(\d+\.?\d*)%', process_percent, text)
    text = re.sub(r'%(\d+\.?\d*)', process_percent, text)

    def final_number_fix(match):
        val = match.group(0)
        return process_float_or_int(val)

    text = re.sub(r'\b\d+\.?\d*\b', final_number_fix, text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

@app.route('/')
def home():
    return jsonify({"status": "SomTTS API is running"})

@app.route('/static/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json
    raw_text = data.get('text', '')
    voice_choice = data.get('voice', 'Muuse')
    rate_val = int(data.get('rate', 0))
    pitch_val = int(data.get('pitch', 0))

    text = hagaaji_qoraalka(raw_text.replace("!", ","))

    if voice_choice == 'Ubax':
        voice_name = "so-SO-UbaxNeural"
    else:
        voice_name = "so-SO-MuuseNeural"

    if voice_choice == 'Wiil':
        rate_val = 15
        pitch_val = 30

    r = f"+{rate_val}%" if rate_val >= 0 else f"{rate_val}%"
    p = f"+{pitch_val}Hz" if pitch_val >= 0 else f"{pitch_val}Hz"

    filename = f"Codka_{uuid.uuid4().hex[:8]}_{int(time.time())}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    async def make_tts():
        tts = edge_tts.Communicate(text, voice_name, rate=r, pitch=p)
        await tts.save(filepath)

    asyncio.run(make_tts())

    full_url = f"{request.host_url}static/audio/{filename}"
    return jsonify({"audioUrl": full_url})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, threaded=True)
