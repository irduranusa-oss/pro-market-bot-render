# app.py - VERSIÓN SIMPLIFICADA PARA DEBUG
import os
import time
import requests
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)

# Configuración
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

def send_telegram(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        return True
    except:
        return False

def bot_loop():
    print("🤖 INICIANDO BOT...")
    send_telegram("✅ Bot iniciado en Render")
    
    count = 0
    while True:
        try:
            count += 1
            msg = f"🔔 Señal de prueba #{count} - {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
            print(msg)
            send_telegram(msg)
            time.sleep(60)  # 1 minuto para prueba
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(30)

@app.route('/')
def home():
    return "🤖 Bot ACTIVO - Enviando señales cada 1 minuto"

@app.route('/health')
def health():
    return "🟢 OK"

if __name__ == "__main__":
    # Iniciar bot en segundo plano
    import threading
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Iniciar web
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Iniciando en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
