# pro_market_bot_ultra_fixed.py
# Bot GLOBAL 24/7 – VERSIÓN EXCLUSIVA RENDER
# ✅ Funciona 100% en la nube - Apaga tu PC cuando quieras

import os, time, io, json, warnings, traceback, requests
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf
from flask import Flask

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# === CONFIGURACIÓN RENDER ===
# Variables de entorno para seguridad
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "8371038763:AAEtYlJKqR1lD07dB7tdCmR4iR9NfTUTnxU")
TELEGRAM_CHAT_ID   = os.getenv("CHAT_ID", "5424722852")

MIN_SCORE   = 60
BULL_PROB   = 70
BEAR_PROB   = 30
MIN_ATR_PCT = 0.4
POLL_SECONDS = 300

# === FUNCIONES DE TIEMPO ===
def utc_now(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
def current_hour(): return datetime.now(timezone.utc).hour

# === LISTA GLOBAL DE TICKERS (optimizada) ===
TICKERS_ALL = {
    "AMERICA": [
        "^GSPC","^DJI","^IXIC","^MXX","^BVSP",
        "AAPL","MSFT","GOOGL","AMZN","META","TSLA","NVDA",
        "JPM","V","MA","DIS","NKE","KO","PEP","WMT",
        "BTC-USD","ETH-USD","SOL-USD",
        "USDMXN=X","USDCAD=X","USDBRL=X",
        "GC=F","CL=F","SI=F"
    ],
    "MEXICO": [
        "^MXX",
        "AMXL.MX","GFNORTEO.MX","CEMEXCPO.MX","WALMEX.MX","FEMSAUBD.MX",
        "BIMBOA.MX","GMEXICOB.MX","ALPEKA.MX","GCC.MX","AC.MX","ALSEA.MX",
        "USDMXN=X","EURMXN=X",
        "GC=F","SLV=F"
    ],
    "EUROPA": [
        "^FTSE","^GDAXI","^FCHI","^STOXX50E","^IBEX",
        "SIE.DE","SAP.DE","AIR.PA","BN.PA","MC.PA",
        "ULVR.L","BP.L","HSBA.L","AZN.L",
        "EURUSD=X","GBPUSD=X"
    ],
    "ASIA": [
        "^N225","^HSI","^AXJO",
        "BABA","JD","PDD",
        "USDJPY=X","AUDUSD=X",
        "GC=F","CL=F"
    ]
}

def get_region_by_time():
    h = current_hour()
    if 0 <= h < 7: return "ASIA"
    if 7 <= h < 14: return "EUROPA"
    if 14 <= h < 20: return "MEXICO"
    return "AMERICA"

# === TELEGRAM ===
_http = requests.Session()
def send_telegram_text(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: 
        _http.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
        print(f"✅ Telegram: {text[:50]}...")
    except Exception as e: 
        print(f"❌ Error Telegram texto: {e}")

def send_telegram_photo(caption, img, filename="chart.png"):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try: 
        _http.post(url, files={"photo": (filename, img)}, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, timeout=20)
        print(f"✅ Telegram foto: {caption[:50]}...")
    except Exception as e: 
        print(f"❌ Error Telegram foto: {e}")

# === INDICADORES ===
def ema(s, n): return s.ewm(span=n, adjust=False).mean()
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
            df = yf.download(tk, period="1y", interval="1d", auto_adjust=True, progress=False)
        
        if df.empty:
            return pd.DataFrame()
        return df.dropna()
    except Exception as e:
        print(f"❌ Error descargando {tk}: {e}")
        return pd.DataFrame()

# === CÁLCULO DE FEATURES ===
def compute_features(df):
    c = df["Close"]
    e20, e50, e200 = ema(c,20), ema(c,50), ema(c,200)
    r = rsi(c,14)
    _,_,m_hist = macd(c)
    a = atr(df)

    # valores finales
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
    return (f"{flecha} {tk}\nÚlt: {f['last']:.4f} | Prev: {f['prev']:.4f}\n"
            f"Score: {f['score']} | RSI: {f['rsi']:.1f} | MACD: {f['macd_hist']:.3f}\n"
            f"ATR: {f['atr_abs']:.4f} ({f['atr_pct']:.2f}%)\n"
            f"Tendencia: {tend} | Objetivo: {obj:.4f}")

def make_chart(df,c,e20,e50,e200,tend,obj):
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(c, label="Close")
    ax.plot(e20, label="EMA20")
    ax.plot(e50, label="EMA50")
    ax.plot(e200, label="EMA200")
    ax.axhline(obj, ls="--", lw=1)
    ax.set_title(f"Señal {tend}")
    ax.legend(); ax.grid(ls="--", alpha=0.4)
    buf = io.BytesIO(); fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130); plt.close(fig)
    buf.seek(0); return buf.read()

# === LOOP PRINCIPAL ===
def bot_loop():
    print("🤖 INICIANDO BOT EN RENDER...")
    send_telegram_text("✅ ULTRA Bot iniciado en RENDER - PC APAGADA SEGURA")
    
    while True:
        try:
            region = get_region_by_time()
            print(f"[{utc_now()}] 🔄 Región activa: {region}")
            
            for tk in TICKERS_ALL[region]:
                df = fetch_history(tk)
                if len(df) < 50: continue
                try:
                    feat,c,e20,e50,e200 = compute_features(df)
                    tend = classify(feat)
                    if tend == "NEUTRA": continue
                    obj = feat["last"] + feat["atr_abs"] if tend=="ALCISTA" else feat["last"] - feat["atr_abs"]
                    cap = build_caption(tk, feat, tend, obj)
                    img = make_chart(df, c, e20, e50, e200, tend, obj)
                    send_telegram_photo(cap, img, f"{tk}.png")
                    print(f"[{utc_now()}] ✅ Señal enviada: {tk} {tend}")
                except Exception as e:
                    print(f"[{utc_now()}] ❌ {tk} error: {e}")
            
            print(f"[{utc_now()}] 🔁 Ciclo terminado - Esperando {POLL_SECONDS}s\n")
            time.sleep(POLL_SECONDS)
            
        except Exception as e:
            print(f"💥 ERROR GLOBAL: {e}")
            time.sleep(60)

# === FLASK PARA RENDER ===
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <html>
        <head><title>🤖 Bot Trading 24/7</title></head>
        <body>
            <h1>✅ BOT ACTIVO EN RENDER</h1>
            <p><strong>Tu PC puede estar APAGADA</strong></p>
            <p>Región: {get_region_by_time()} | Hora: {utc_now()}</p>
            <p>🤖 Analizando mercados 24/7</p>
            <p>📱 Enviando señales a Telegram</p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return "🟢 OK - Bot funcionando en Render"

# === INICIO RENDER ===
if __name__ == "__main__":
    print("🚀" * 20)
    print("🤖 BOT INICIANDO EN RENDER")
    print("💻 PC APAGADA - SEGURO")
    print("🚀" * 20)
    
    # Iniciar bot en segundo plano
    import threading
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Iniciar servidor web (OBLIGATORIO para Render)
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 Servidor web en puerto: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
