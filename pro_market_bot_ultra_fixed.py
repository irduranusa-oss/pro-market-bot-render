# pro_market_bot_ultra_fixed.py
# Bot GLOBAL 24/7 – OPTIMIZADO para Render Free Tier
# Version ligera con menos tickers para evitar errores 502/503

import os, time, io, json, warnings, traceback, requests
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# === CONFIGURACIÓN CON VARIABLES DE ENTORNO ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
PORT = int(os.getenv("PORT", 10000))

MIN_SCORE   = 65  # Aumentado para ser más selectivo
BULL_PROB   = 70
BEAR_PROB   = 30
MIN_ATR_PCT = 0.5  # Aumentado para filtrar más
POLL_SECONDS = 600  # 10 minutos entre ciclos (más tiempo)

# === SERVIDOR HTTP PARA HEALTH CHECK DE RENDER ===
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot running OK')
    
    def log_message(self, format, *args):
        pass

def start_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    print(f"[INFO] Health check server running on port {PORT}")
    server.serve_forever()

# === FUNCIONES DE TIEMPO ===
def utc_now(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
def current_hour(): return datetime.now(timezone.utc).hour

# === LISTA REDUCIDA DE TICKERS (SOLO LO MÁS IMPORTANTE) ===
TICKERS_ALL = {
    "AMERICA": [
        "^GSPC","^DJI","^IXIC","^VIX",
        "AAPL","MSFT","GOOGL","AMZN","META","TSLA","NVDA",
        "BTC-USD","ETH-USD","SOL-USD",
        "USDMXN=X","GC=F","CL=F"
    ],
    "MEXICO": [
        "^MXX",
        "AMXL.MX","GFNORTEO.MX","CEMEXCPO.MX","WALMEX.MX","FEMSAUBD.MX",
        "BIMBOA.MX","GMEXICOB.MX",
        "USDMXN=X","GC=F","CL=F"
    ],
    "EUROPA": [
        "^FTSE","^GDAXI","^FCHI","^STOXX50E",
        "SIE.DE","SAP.DE","AIR.PA","MC.PA",
        "EURUSD=X","BTC-EUR"
    ],
    "ASIA": [
        "^N225","^HSI","^BSESN",
        "BABA","TCEHY","USDJPY=X",
        "BTC-USD","GC=F"
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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARNING] Telegram credentials not configured")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: 
        _http.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
        print(f"[INFO] Message sent to Telegram")
    except Exception as e: 
        print(f"[ERROR] Telegram text: {e}")

def send_telegram_photo(caption, img, filename="chart.png"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try: 
        _http.post(url, files={"photo": (filename, img)}, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, timeout=20)
        print(f"[INFO] Photo sent to Telegram")
    except Exception as e: 
        print(f"[ERROR] Telegram photo: {e}")

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
        if tk.endswith("-USD") or tk.endswith("=X") or tk.endswith("-EUR"):
            df = yf.download(tk, period="30d", interval="1h", auto_adjust=True, progress=False)
        else:
            df = yf.download(tk, period="90d", interval="1d", auto_adjust=True, progress=False)
        return df.dropna()
    except Exception as e:
        print(f"[ERROR] Fetching {tk}: {e}")
        return pd.DataFrame()

# === CÁLCULO DE FEATURES ===
def compute_features(df):
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
    return (f"{flecha} {tk}\nÚlt: {f['last']:.4f} | Prev: {f['prev']:.4f}\n"
            f"Score: {f['score']} | RSI: {f['rsi']:.1f} | MACD: {f['macd_hist']:.3f}\n"
            f"ATR: {f['atr_abs']:.4f} ({f['atr_pct']:.2f}%)\n"
            f"Tendencia: {tend} | Objetivo: {obj:.4f}")

def make_chart(df,c,e20,e50,e200,tend,obj):
    try:
        fig, ax = plt.subplots(figsize=(8,4))
        ax.plot(c.tail(100), label="Close")  # Solo últimos 100 datos
        ax.plot(e20.tail(100), label="EMA20")
        ax.plot(e50.tail(100), label="EMA50")
        ax.plot(e200.tail(100), label="EMA200")
        ax.axhline(obj, ls="--", lw=1, color='red')
        ax.set_title(f"Señal {tend}")
        ax.legend(); ax.grid(ls="--", alpha=0.4)
        buf = io.BytesIO(); fig.tight_layout()
        fig.savefig(buf, format="png", dpi=100)  # Reducida calidad
        plt.close(fig)
        buf.seek(0); return buf.read()
    except Exception as e:
        print(f"[ERROR] Creating chart: {e}")
        return None

# === LOOP PRINCIPAL ===
def loop():
    print(f"[{utc_now()}] Bot iniciando...")
    send_telegram_text("✅ ULTRA Bot iniciado (versión optimizada para Render)")
    
    while True:
        try:
            region = get_region_by_time()
            print(f"\n[{utc_now()}] === Región activa: {region} ===")
            
            signals_found = 0
            for tk in TICKERS_ALL[region]:
                try:
                    print(f"[{utc_now()}] Analizando {tk}...", end=" ")
                    df = fetch_history(tk)
                    if len(df) < 50: 
                        print("Datos insuficientes")
                        continue
                    
                    feat,c,e20,e50,e200 = compute_features(df)
                    tend = classify(feat)
                    
                    if tend == "NEUTRA": 
                        print(f"Neutral (score={feat['score']})")
                        continue
                    
                    print(f"¡SEÑAL {tend}! (score={feat['score']})")
                    signals_found += 1
                    
                    obj = feat["last"] + feat["atr_abs"] if tend=="ALCISTA" else feat["last"] - feat["atr_abs"]
                    cap = build_caption(tk, feat, tend, obj)
                    img = make_chart(df, c, e20, e50, e200, tend, obj)
                    
                    if img:
                        send_telegram_photo(cap, img, f"{tk}.png")
                    else:
                        send_telegram_text(cap)
                    
                    # Pequeña pausa entre señales
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"[ERROR] {tk}: {e}")
                    continue
            
            print(f"\n[{utc_now()}] Ciclo terminado. Señales encontradas: {signals_found}")
            print(f"[{utc_now()}] Esperando {POLL_SECONDS}s hasta el próximo análisis...\n")
            time.sleep(POLL_SECONDS)
            
        except Exception as e:
            err = traceback.format_exc()
            print(f"[ERROR CRÍTICO] {err}")
            send_telegram_text(f"⚠️ Error en ciclo:\n{str(e)[:500]}")
            time.sleep(60)  # Espera 1 min antes de reintentar

if __name__ == "__main__":
    # Iniciar servidor de health check en thread separado
    health_thread = Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    print(f"[{utc_now()}] Aplicación iniciada correctamente")
    print(f"[{utc_now()}] Puerto: {PORT}")
    print(f"[{utc_now()}] Telegram configurado: {bool(TELEGRAM_BOT_TOKEN)}")
    
    # Iniciar bot principal
    try:
        loop()
    except Exception:
        err = traceback.format_exc()
        print(err)
        send_telegram_text(f"⚠️ Error crítico al iniciar:\n{err[:3500]}")
