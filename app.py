import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)

# === CONFIGURACIÓN ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8371038763:AAEtYlJKqR1lD07dB7tdCmR4iR9NfTUTnxU")
CHAT_ID = os.getenv("CHAT_ID", "5424722852")

# === FUNCIONES ===
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print(f"✅ Telegram: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def check_market(ticker):
    try:
        print(f"📊 Verificando {ticker}...")
        df = yf.download(ticker, period="1mo", progress=False)
        if len(df) < 2:
            return None
            
        current = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2] 
        change = ((current - prev) / prev) * 100
        
        if abs(change) > 2.0:  # Señal con cambio > 2%
            return f"📈 {ticker}: {change:+.2f}% (${current:.2f})"
        return None
    except Exception as e:
        print(f"❌ Error con {ticker}: {e}")
        return None

# === RUTAS ===
@app.route('/')
def home():
    return """
    <html>
        <head><title>🤖 Trading Bot</title></head>
        <body style="font-family: Arial, sans-serif; margin: 40px;">
            <h1>✅ Bot de Trading ACTIVO</h1>
            <div style="background: #f0f8ff; padding: 20px; border-radius: 10px;">
                <h3>🚀 Sistema Funcionando</h3>
                <p><strong>Hora UTC:</strong> """ + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + """</p>
                <p><strong>Estado:</strong> <span style="color: green;">🟢 ONLINE</span></p>
            </div>
            <h3>⚡ Acciones Rápidas:</h3>
            <p>
                <a href="/check" style="background: #4CAF50; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">🔍 Verificar Mercados</a>
                <a href="/test" style="background: #2196F3; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; margin-left: 10px;">📱 Test Telegram</a>
                <a href="/health" style="background: #FF9800; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; margin-left: 10px;">❤️ Health Check</a>
            </p>
            <p>Monitoreando: <strong>AAPL, MSFT, TSLA, BTC-USD, GC=F, MXN=X</strong></p>
        </body>
    </html>
    """

@app.route('/check')
def check_all_markets():
    tickers = ["AAPL", "MSFT", "TSLA", "BTC-USD", "GC=F", "MXN=X"]
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
    message = f"🧪 Test desde Render - {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
    success = send_telegram(message)
    
    if success:
        return """
        <h2>✅ Test Exitoso</h2>
        <p>El mensaje de prueba fue enviado a Telegram correctamente.</p>
        <p><strong>Mensaje:</strong> """ + message + """</p>
        <a href="/">← Volver</a>
        """
    else:
        return """
        <h2>❌ Error en Test</h2>
        <p>No se pudo enviar el mensaje a Telegram. Revisa la configuración.</p>
        <a href="/">← Volver</a>
        """

@app.route('/health')
def health():
    return "🟢 HEALTHY - Servidor funcionando correctamente"

@app.route('/debug')
def debug():
    port = os.environ.get('PORT', 'NO DEFINIDO')
    return f"""
    <h2>🔧 Debug Info</h2>
    <ul>
        <li><strong>PORT:</strong> {port}</li>
        <li><strong>Hora UTC:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}</li>
        <li><strong>Telegram Config:</strong> {'✅' if TELEGRAM_TOKEN and CHAT_ID else '❌'}</li>
    </ul>
    <a href="/">← Volver</a>
    """

# === INICIO ===
if __name__ == "__main__":
    print("🚀 INICIANDO SERVICIO WEB...")
    print("🔧 Configuración:")
    print(f"   - PORT: {os.environ.get('PORT', 'No definido')}")
    print(f"   - Telegram: {'✅ CONFIGURADO' if TELEGRAM_TOKEN and CHAT_ID else '❌ NO CONFIGURADO'}")
    
    # Obtener puerto de Render (obligatorio)
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Iniciando en puerto: {port}")
    
    # Enviar mensaje de inicio
    send_telegram(f"✅ Bot iniciado en Render - Puerto {port}")
    
    # Iniciar servidor
    app.run(host="0.0.0.0", port=port, debug=False)
