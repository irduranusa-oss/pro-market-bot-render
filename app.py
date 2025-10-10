import os
import time
import requests
from datetime import datetime, timezone
from threading import Thread
from flask import Flask

app = Flask(__name__)

# === CONFIG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
PORT = int(os.environ.get("PORT", 10000))

# === FUNCIONES ===
def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def send_telegram(message):
    """Envía mensaje a Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Falta configurar TELEGRAM_TOKEN o CHAT_ID")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print(f"[{utc_now()}] Telegram: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"[{utc_now()}] ❌ Error Telegram: {e}")
        return False

# === FUNCIONES DE BOT (POST-ARRANQUE) ===
def check_market(ticker):
    """Consulta lenta de yfinance (se ejecuta en segundo plano)"""
    import yfinance as yf
    import pandas as pd
    try:
        print(f"📊 Verificando {ticker}...")
        df = yf.download(ticker, period="1mo", progress=False)
        if len(df) < 2:
            return None
        current = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        change = ((current - prev) / prev) * 100
        if abs(change) > 2:
            return f"📈 {ticker}: {change:+.2f}% (${current:.2f})"
        return None
    except Exception as e:
        print(f"❌ Error en {ticker}: {e}")
        return None

def bot_loop():
    """Bucle del bot (NO bloquea el arranque)"""
    while True:
        try:
            tickers = ["AAPL", "MSFT", "TSLA", "BTC-USD", "GC=F", "MXN=X"]
            signals = [check_market(t) for t in tickers if check_market(t)]
            if signals:
                send_telegram("🚨 SEÑALES AUTOMÁTICAS:\n" + "\n".join(signals))
            else:
                print(f"[{utc_now()}] ✅ Sin señales fuertes.")
            time.sleep(3600)
        except Exception as e:
            print(f"[{utc_now()}] ⚠️ Error en loop: {e}")
            time.sleep(60)

# === RUTAS FLASK ===
@app.route('/')
def home():
    return f"""
    <h1>🤖 Bot de Trading Activo</h1>
    <p>Hora UTC: {utc_now()}</p>
    <p>Estado: 🟢 ONLINE</p>
    <p><a href='/health'>Health Check</a></p>
    """

@app.route('/health')
def health():
    return "🟢 HEALTHY"

# === MAIN ===
if __name__ == "__main__":
    print(f"[{utc_now()}] 🚀 Iniciando servidor Flask en puerto {PORT}")
    Thread(target=bot_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False)
