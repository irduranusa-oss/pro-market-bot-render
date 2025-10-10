import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)

# Configuración
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8371038763:AAEtYlJKqR1lD07dB7tdCmR4iR9NfTUTnxU")
CHAT_ID = os.getenv("CHAT_ID", "5424722852")

# Lista simple de tickers
TICKERS = ["AAPL", "MSFT", "TSLA", "BTC-USD", "GC=F", "MXN=X"]

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": CHAT_ID, "text": message})
        return response.status_code == 200
    except:
        return False

def check_ticker(ticker):
    try:
        # Descargar datos
        df = yf.download(ticker, period="1mo", progress=False)
        if df.empty:
            return None
        
        # Calcular tendencia simple
        current = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        change = ((current - prev) / prev) * 100
        
        if abs(change) > 1.0:  # Cambio mayor al 1%
            return f"{ticker}: {change:+.2f}% - Precio: {current:.2f}"
        return None
    except:
        return None

@app.route('/')
def home():
    return """
    <html>
        <head><title>🤖 Trading Bot</title></head>
        <body>
            <h1>✅ Bot de Trading Activo</h1>
            <p>Monitoreando: AAPL, MSFT, TSLA, BTC, Oro, USD/MXN</p>
            <p><a href="/check">🔍 Verificar Mercados</a></p>
            <p><a href="/test">📱 Test Telegram</a></p>
        </body>
    </html>
    """

@app.route('/check')
def check_markets():
    signals = []
    for ticker in TICKERS:
        signal = check_ticker(ticker)
        if signal:
            signals.append(signal)
    
    if signals:
        message = "🚨 SEÑALES:\n" + "\n".join(signals)
        send_telegram(message)
        return f"<h3>📈 Señales Enviadas:</h3><pre>{message}</pre>"
    else:
        return "<h3>⚡ No hay señales fuertes</h3>"

@app.route('/test')
def test_telegram():
    success = send_telegram(f"✅ Bot activo - {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
    return f"📱 Telegram: {'✅ ENVIADO' if success else '❌ ERROR'}"

@app.route('/health')
def health():
    return "🟢 OK"

if __name__ == "__main__":
    print("🚀 Bot iniciado - Web Service Gratuito")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
