import os
import time
import threading
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8371038763:AAEtYlJKqR1lD07dB7tdCmR4iR9NfTUTnxU")
CHAT_ID = os.getenv("CHAT_ID", "5424722852")

# Estado del bot
bot_active = False
last_check = None

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": CHAT_ID, "text": message})
        return response.status_code == 200
    except:
        return False

def bot_loop():
    global bot_active, last_check
    
    TICKERS = ["AAPL", "MSFT", "TSLA", "BTC-USD", "GC=F", "MXN=X"]
    
    while bot_active:
        try:
            signals = []
            for ticker in TICKERS:
                try:
                    df = yf.download(ticker, period="1mo", progress=False)
                    if len(df) > 1:
                        current = df['Close'].iloc[-1]
                        prev = df['Close'].iloc[-2]
                        change = ((current - prev) / prev) * 100
                        
                        if abs(change) > 1.5:
                            signals.append(f"{ticker}: {change:+.2f}%")
                except:
                    continue
            
            if signals:
                message = f"📈 {datetime.now().strftime('%H:%M')}\n" + "\n".join(signals)
                send_telegram(message)
            
            last_check = datetime.now()
            time.sleep(300)  # 5 minutos
        
        except Exception as e:
            print(f"Bot error: {e}")
            time.sleep(60)

@app.route('/')
def home():
    status = "🟢 ACTIVO" if bot_active else "🔴 INACTIVO"
    last = f"Última verificación: {last_check}" if last_check else "Nunca"
    return f"""
    <html>
        <head><title>🤖 Trading Bot</title></head>
        <body>
            <h1>Bot de Trading</h1>
            <p>Estado: <strong>{status}</strong></p>
            <p>{last}</p>
            <p>
                <a href="/start">▶️ Iniciar Bot</a> | 
                <a href="/stop">⏹️ Detener Bot</a> |
                <a href="/check">🔍 Verificar Ahora</a>
            </p>
        </body>
    </html>
    """

@app.route('/start')
def start_bot():
    global bot_active
    if not bot_active:
        bot_active = True
        thread = threading.Thread(target=bot_loop)
        thread.daemon = True
        thread.start()
        send_telegram("✅ Bot iniciado - Monitoreo activo")
    return "🟢 Bot iniciado"

@app.route('/stop')
def stop_bot():
    global bot_active
    bot_active = False
    send_telegram("⏹️ Bot detenido")
    return "🔴 Bot detenido"

@app.route('/check')
def check_now():
    # Verificación inmediata
    TICKERS = ["AAPL", "MSFT", "TSLA", "BTC-USD", "GC=F", "MXN=X"]
    signals = []
    
    for ticker in TICKERS:
        try:
            df = yf.download(ticker, period="1mo", progress=False)
            if len(df) > 1:
                current = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                change = ((current - prev) / prev) * 100
                
                if abs(change) > 1.0:
                    signals.append(f"{ticker}: {change:+.2f}%")
        except:
            continue
    
    if signals:
        message = "🔔 VERIFICACIÓN:\n" + "\n".join(signals)
        send_telegram(message)
        return f"<h3>Señales enviadas</h3><pre>{message}</pre>"
    else:
        return "<h3>Sin señales fuertes</h3>"

if __name__ == "__main__":
    print("🚀 Web Service Gratuito - Listo")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
