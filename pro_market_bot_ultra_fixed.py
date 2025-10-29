import os
import time
import requests
import yfinance as yf
import pandas as pd
import traceback
from datetime import datetime, timezone
from threading import Thread
from flask import Flask

app = Flask(__name__)

# === CONFIGURACIÓN ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8371038763:AAEtYlJKqR1lD07dB7tdCmR4iR9NfTUTnxU")
CHAT_ID = os.getenv("CHAT_ID", "5424722852")
PORT = int(os.environ.get("PORT", 10000))

# === FUNCIONES BASE ===
def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def send_telegram(message):
    """Envía un mensaje a Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print(f"[{utc_now()}] Telegram: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"[{utc_now()}] ❌ Telegram error: {e}")
        return False

def check_market(ticker):
    """Verifica variaciones mayores al 2%"""
    try:
        print(f"📊 Verificando {ticker}...")
        df = yf.download(ticker, period="1mo", progress=False)
        if len(df) < 2:
            return None

        current = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        change = ((current - prev) / prev) * 100

        if abs(change) > 2.0:  # Señal importante
            return f"📈 {ticker}: {change:+.2f}% (${current:.2f})"
        return None
    except Exception as e:
        print(f"❌ Error con {ticker}: {e}")
        return None

# === WEB FLASK ===
@app.route('/')
def home():
    return f"""
    <html>
        <head><title>🤖 Trading Bot</title></head>
        <body style="font-family: Arial, sans-serif; margin: 40px;">
            <h1>✅ Bot de Trading ACTIVO</h1>
            <div style="background: #f0f8ff; padding: 20px; border-radius: 10px;">
                <h3>🚀 Sistema Funcionando</h3>
                <p><strong>Hora UTC:</strong> {utc_now()}</p>
                <p><strong>Estado:</strong> <span style="color: green;">🟢 ONLINE</span></p>
            </div>
            <h3>⚡ Acciones Rápidas:</h3>
            <p>
                <a href="/check" style="background: #4CAF50; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">🔍 Verificar Mercados</a>
                <a href="/test" style="background: #2196F3; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; margin-left: 10px;">📱 Test Telegram</a>
                <a href="/health" style="background: #FF9800; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; margin-left: 10px;">❤️ Health Check</a>
            </p>
            <p>Monitoreando: <strong>AAPL","DLR", "BLK", "MSFT","VNET","CMCSA", "AI", "EQIX", "SIRI", "T", "TSLA","NVDA", "GDS", "VZ", "BTC-USD", "GC=F", "MXN=X</strong></p>
        </body>
    </html>
    """

@app.route('/check')
def check_all_markets():
    tickers = ["AAPL","DLR", "BLK", "MSFT","VNET","CMCSA", "AI", "EQIX", "SIRI", "T", "TSLA","NVDA", "GDS", "VZ", "BTC-USD", "GC=F", "MXN=X"]
    signals = []

    for ticker in tickers:
        signal = check_market(ticker)
        if signal:
            signals.append(signal)

    if signals:
        message = "🚨 SEÑALES DETECTADAS:\n" + "\n".join(signals)
        telegram_sent = send_telegram(message)
        result = f"""
        <h2>📈 Señales Enviadas a Telegram</h2>
        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px;">
            <pre>{message}</pre>
        </div>
        <p>Telegram: {'✅ ENVIADO' if telegram_sent else '❌ ERROR'}</p>
        """
    else:
        result = """
        <h2>⚡ Sin Señales Fuertes</h2>
        <p>No se detectaron movimientos significativos en los mercados.</p>
        """
    return result + '<br><a href="/">← Volver</a>'

@app.route('/test')
def test_telegram():
    message = f"🧪 Test desde Render - {utc_now()}"
    success = send_telegram(message)
    return f"""
    <h2>{'✅ Test Exitoso' if success else '❌ Error en Test'}</h2>
    <p>{'Mensaje enviado correctamente.' if success else 'No se pudo enviar el mensaje.'}</p>
    <p><strong>Mensaje:</strong> {message}</p>
    <a href="/">← Volver</a>
    """

@app.route('/health')
def health():
    return "🟢 HEALTHY - Servidor funcionando correctamente"

# === LOOP DEL BOT ===
def bot_loop():
    """Bucle principal del bot que revisa mercados cada hora"""
    while True:
        try:
            print(f"[{utc_now()}] Ejecutando verificación automática...")
            tickers = ["AAPL","DLR", "BLK", "MSFT","VNET","CMCSA", "AI", "EQIX", "SIRI", "T", "TSLA","NVDA", "GDS", "VZ", "BTC-USD", "GC=F", "MXN=X"]
            signals = [check_market(t) for t in tickers if check_market(t)]
            if signals:
                send_telegram("🚨 SEÑALES AUTOMÁTICAS:\n" + "\n".join(signals))
            time.sleep(3600)  # cada hora
        except Exception as e:
            err = traceback.format_exc()
            print(f"[{utc_now()}] ❌ Error en loop: {e}")
            send_telegram(f"⚠️ Error en loop:\n{err[:3000]}")
            time.sleep(60)

# === MAIN ===
if __name__ == "__main__":
    print(f"[{utc_now()}] Iniciando servidor Flask en puerto {PORT}")
    print(f"[{utc_now()}] Telegram configurado: {bool(TELEGRAM_TOKEN)}")

    # Iniciar el loop en un hilo separado
    Thread(target=bot_loop, daemon=True).start()

    # Ejecutar Flask (Render detecta este proceso)
    app.run(host="0.0.0.0", port=PORT, debug=False)

