# pro_market_bot_ultra_fixed.py
# Bot GLOBAL 24/7 – VERSIÓN RENDER

import os, time, io, warnings, traceback, requests
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf
from flask import Flask

warnings.filterwarnings("ignore")

# === CONFIGURACIÓN ===
TELEGRAM_BOT_TOKEN = os.getenv("8371038763:AAEtYlJKqR1lD07dB7tdCmR4iR9NfTUTnxU", "").strip()
TELEGRAM_CHAT_ID   = os.getenv("5424722852", "").strip()

MIN_SCORE   = 60
BULL_PROB   = 70
BEAR_PROB   = 30
MIN_ATR_PCT = 0.4
POLL_SECONDS = 300

# === LISTA DE TICKERS SEGUROS ===
TICKERS_ALL = {
    "AMERICA": [
        "SPY", "QQQ", "DIA", "IWM",
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA",
        "JPM", "V", "MA", "DIS", "NKE", "KO", "PEP", "WMT",
        "BTC-USD", "ETH-USD", "SOL-USD",
        "MXN=X", "BRL=X", "CAD=X",
        "GC=F", "CL=F"
    ],
    "MEXICO": [
        "EWW", "AMX", "CX", "MXN=X"
    ],
    "EUROPA": [
        "VGK", "IEV", "ASML", "SAP", "NSRGY",
        "EUR=X", "GBP=X"
    ],
    "ASIA": [
        "EWJ", "FXI", "EWY", "BABA", "JD",
        "JPY=X", "AUD=X"
    ]
}

# === FUNCIONES DE TIEMPO ===
def utc_now(): 
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def current_hour(): 
    return datetime.now(timezone.utc).hour

def get_region_by_time():
    h = current_hour()
    if 0 <= h < 7: return "ASIA"
    if 7 <= h < 14: return "EUROPA"
    if 14 <= h < 20: return "MEXICO"
    return "AMERICA"

# === TELEGRAM ===
def send_telegram_text(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram no configurado")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: 
        response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
        if response.status_code == 200:
            print("✅ Mensaje Telegram enviado")
            return True
        else:
            print(f"❌ Error Telegram: {response.status_code}")
            return False
    except Exception as e: 
        print(f"❌ Error enviando Telegram: {e}")
        return False

def send_telegram_photo(caption, img, filename="chart.png"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram no configurado")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try: 
        response = requests.post(url, files={"photo": (filename, img)}, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, timeout=20)
        if response.status_code == 200:
            print("✅ Foto Telegram enviada")
            return True
        else:
            print(f"❌ Error Telegram photo: {response.status_code}")
            send_telegram_text(caption)
            return False
    except Exception as e: 
        print(f"❌ Error enviando foto Telegram: {e}")
        send_telegram_text(caption)
        return False

# === INDICADORES ===
def ema(s, n): 
    return s.ewm(span=n, adjust=False).mean()

def rsi(s, n=14):
    d = s.diff()
    up, down = d.clip(lower=0), (-d).clip(lower=0)
    rs = up.ewm(alpha=1/n).mean() / (down.ewm(alpha=1/n).mean()+1e-12)
    return 100 - (100/(1+rs))

def macd(s):
    e12, e26 = ema(s,12), ema(s,26)
    line = e12 - e26
    sig = ema(line,9)
    return line, sig, line - sig

def atr(df, n=14):
    h,l,c = df["High"],df["Low"],df["Close"]
    prev = c.shift(1)
    tr = pd.concat([(h-l),(h-prev).abs(),(l-prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

# === DESCARGA DE DATOS ===
def fetch_history(tk):
    try:
        print(f"📥 Descargando {tk}...")
        
        if tk.endswith("-USD") or tk.endswith("=X") or tk.endswith("-EUR"):
            df = yf.download(tk, period="60d", interval="1h", auto_adjust=True, progress=False)
        else:
            df = yf.download(tk, period="6mo", interval="1d", auto_adjust=True, progress=False)
        
        if df.empty:
            print(f"⚠️  No hay datos para {tk}")
            return pd.DataFrame()
            
        print(f"✅ {tk} descargado - {len(df)} registros")
        return df.dropna()
        
    except Exception as e:
        print(f"❌ Error descargando {tk}: {e}")
        return pd.DataFrame()

# === CÁLCULO DE FEATURES ===
def compute_features(df):
    if len(df) < 50:
        return None, None, None, None, None
        
    c = df["Close"]
    e20, e50, e200 = ema(c,20), ema(c,50), ema(c,200)
    r = rsi(c,14)
    _,_,m_hist = macd(c)
    a = atr(df)

    last = float(c.iloc[-1]); prev = float(c.iloc[-2])
    e20v, e50v, e200v = float(e20.iloc[-1]), float(e50.iloc[-1]), float(e200.iloc[-1])
    rsi_v = float(r.iloc[-1]); macd_v = float(m_hist.iloc[-1])
    atr_abs = float(a.iloc[-1]) if np.isfinite(a.iloc[-1]) else 0.0
    atr_pct = 100*atr_abs/last if last else 0.0

    score = 0
    if e20v > e50v: score += 20
    if e50v > e200v: score += 20
    if e20v > e200v: score += 10
    if rsi_v > 65: score += 20
    elif rsi_v > 55: score += 10
    elif rsi_v < 35: score -= 20
    elif rsi_v < 45: score -= 10
    if macd_v > 0: score += 20
    ret_1 = (last - prev) / prev * 100 if prev else 0.0
    if ret_1 > 0.3: score += 10
    if ret_1 < -0.3: score -= 10

    score = int(max(0,min(100,score)))
    return {
        "last": last, "prev": prev,
        "score": score, "rsi": rsi_v, "macd_hist": macd_v,
        "atr_abs": atr_abs, "atr_pct": atr_pct,
        "prob_up": float(score)
    }, c, e20, e50, e200

def classify(f):
    if f["score"] >= MIN_SCORE and f["atr_pct"] >= MIN_ATR_PCT:
        if f["prob_up"] >= BULL_PROB: return "ALCISTA"
        if f["prob_up"] <= BEAR_PROB: return "BAJISTA"
    return "NEUTRA"

# === MENSAJES Y GRÁFICOS ===
def build_caption(tk,f,tend,obj):
    flecha = "🟩↑" if tend=="ALCISTA" else ("🟥↓" if tend=="BAJISTA" else "⬜")
    return (f"{flecha} {tk}\n"
            f"Precio: {f['last']:.4f} | Score: {f['score']}\n"
            f"RSI: {f['rsi']:.1f} | ATR: {f['atr_pct']:.2f}%\n"
            f"Tendencia: {tend} | Objetivo: {obj:.4f}")

def make_chart(df,c,e20,e50,e200,tend,obj):
    try:
        fig, ax = plt.subplots(figsize=(8,4))
        ax.plot(c, label="Close", linewidth=1.5)
        ax.plot(e20, label="EMA20", linewidth=1)
        ax.plot(e50, label="EMA50", linewidth=1)
        ax.plot(e200, label="EMA200", linewidth=1)
        ax.axhline(obj, ls="--", color="red", lw=1, alpha=0.7, label="Objetivo")
        ax.set_title(f"Señal {tend}")
        ax.legend()
        ax.grid(ls="--", alpha=0.4)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"❌ Error creando gráfico: {e}")
        return None

# === LOOP PRINCIPAL ===
def bot_loop():
    print("🤖 Iniciando Bot de Trading...")
    send_telegram_text("✅ Bot iniciado correctamente en Render")
    
    signal_count = 0
    
    while True:
        try:
            region = get_region_by_time()
            print(f"\n[{utc_now()}] 🔄 Escaneando región: {region}")
            
            tickers = TICKERS_ALL[region]
            print(f"📊 Analizando {len(tickers)} tickers...")
            
            for i, tk in enumerate(tickers, 1):
                try:
                    print(f"  {i}/{len(tickers)} Analizando {tk}...")
                    
                    df = fetch_history(tk)
                    if len(df) < 50: 
                        continue
                        
                    result = compute_features(df)
                    if result[0] is None:
                        continue
                        
                    feat, c, e20, e50, e200 = result
                    tend = classify(feat)
                    
                    if tend == "NEUTRA": 
                        continue
                        
                    obj = feat["last"] + feat["atr_abs"] if tend=="ALCISTA" else feat["last"] - feat["atr_abs"]
                    cap = build_caption(tk, feat, tend, obj)
                    img = make_chart(df, c, e20, e50, e200, tend, obj)
                    
                    if img:
                        success = send_telegram_photo(cap, img, f"{tk}.png")
                    else:
                        success = send_telegram_text(cap)
                    
                    if success:
                        signal_count += 1
                        print(f"✅ Señal #{signal_count} enviada: {tk} {tend}")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Error con {tk}: {e}")
                    continue
                    
            print(f"📈 [{utc_now()}] Ciclo completado. Total señales: {signal_count}")
            print(f"⏰ Esperando {POLL_SECONDS} segundos...\n")
            time.sleep(POLL_SECONDS)
            
        except Exception as e:
            print(f"💥 Error en loop principal: {e}")
            print("🔄 Reintentando en 60 segundos...")
            time.sleep(60)

# === APLICACIÓN FLASK ===
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <html>
        <head><title>🤖 Trading Bot</title></head>
        <body>
            <h1>🤖 Bot de Trading Automático</h1>
            <div style="background: #f0f8ff; padding: 20px; border-radius: 10px;">
                <h3>🟢 SISTEMA ACTIVO</h3>
                <p><strong>Región actual:</strong> {get_region_by_time()}</p>
                <p><strong>Hora UTC:</strong> {utc_now()}</p>
                <p><strong>Estado:</strong> Monitoreo 24/7 activo</p>
            </div>
            <p>El bot está analizando mercados globales y enviando señales a Telegram automáticamente.</p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return "🟢 OK - Bot funcionando correctamente"

@app.route('/status')
def status():
    return {
        "status": "active",
        "service": "Trading Bot",
        "region": get_region_by_time(),
        "utc_time": utc_now(),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    }

# === INICIO ===
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 INICIANDO BOT DE TRADING - VERSIÓN RENDER")
    print("=" * 50)
    
    print("🔧 Configuración:")
    print(f"   Telegram: {'✅ CONFIGURADO' if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID else '❌ NO CONFIGURADO'}")
    print(f"   Tickers totales: {sum(len(v) for v in TICKERS_ALL.values())}")
    
    import threading
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    
    print("🤖 Bot iniciado en segundo plano")
    print("🌐 Iniciando servidor web...")
    
    port = int(os.environ.get('PORT', 10000))
    print(f"📍 Servidor en puerto: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
