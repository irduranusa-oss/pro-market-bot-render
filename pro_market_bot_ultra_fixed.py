# pro_market_bot_ultra_fixed.py
# Bot GLOBAL 24/7 – rotación automática por región.
# Señales técnicas fuertes con score, objetivo, gráfico y envío a Telegram.
# Reqs: pip install yfinance requests pandas numpy matplotlib openpyxl

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

MIN_SCORE   = 60
BULL_PROB   = 70
BEAR_PROB   = 30
MIN_ATR_PCT = 0.4
POLL_SECONDS = 300

CSV_LOG  = "signals_log.csv"
XLSX_DASH = "dashboard.xlsx"

# === SERVIDOR HTTP PARA HEALTH CHECK DE RENDER ===
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot running OK')
    
    def log_message(self, format, *args):
        pass  # Silenciar logs del servidor

def start_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    print(f"[INFO] Health check server running on port {PORT}")
    server.serve_forever()

# === FUNCIONES DE TIEMPO ===
def utc_now(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
def current_hour(): return datetime.now(timezone.utc).hour

# === LISTA GLOBAL DE TICKERS EXTENDIDA ===
TICKERS_ALL = {
    "AMERICA": [
        "^GSPC","^DJI","^IXIC","^MXX","^BVSP","^RUT","^VIX",
        "AAPL","MSFT","GOOGL","AMZN","META","TSLA","NVDA","AMD","INTC","JPM","V","MA",
        "DIS","NKE","PFE","MRNA","KO","PEP","WMT","BA","COST","XOM","CVX",
        "ORCL","ADBE","CRM","PYPL","AVGO","CSCO","QCOM","ABNB","UBER","SNOW",
        "BBDC4.SA","ITUB4.SA","PETR4.SA","VALE3.SA","WEGE3.SA","B3SA3.SA",
        "BTC-USD","ETH-USD","SOL-USD","DOGE-USD","ADA-USD","BNB-USD","XRP-USD","DOT-USD",
        "USDMXN=X","USDCAD=X","USDCLP=X","USDARS=X","USDCOP=X","USDBRL=X","USDPEN=X",
        "GC=F","CL=F","SI=F","HG=F","NG=F","ZC=F","ZS=F","ZL=F","ZO=F"
    ],
    "MEXICO": [
        "^MXX",
        "AMXL.MX","GFNORTEO.MX","CEMEXCPO.MX","WALMEX.MX","FEMSAUBD.MX",
        "BIMBOA.MX","GMEXICOB.MX","KIMBERA.MX","ALPEKA.MX","GCC.MX","AC.MX","ALSEA.MX",
        "TLEVISACPO.MX","BBAJIOO.MX","MEGACPO.MX","GAPB.MX","ASURB.MX","OMAB.MX",
        "LABB.MX","GFINBURO.MX","PINFRA.MX","ALFA.MX","PE&OLES.MX","CUERVO.MX",
        "LIVEPOLC-1.MX","ELEKTRA.MX","GRUMAB.MX","GCARSOA1.MX","SORIANAB.MX",
        "POSADAS.MX","VOLARA.MX","VESTA.MX","FUNO11.MX","TERRA13.MX",
        "NAFTRACISHRS.MX","MEXTRACISHRS.MX",
        "USDMXN=X","EURMXN=X","GBPMXN=X","MXNPKR=X",
        "GC=F","SLV=F","HG=F","CL=F"
    ],
    "EUROPA": [
        "^FTSE","^GDAXI","^FCHI","^STOXX50E","^IBEX","^AEX","^OMX","^SMI",
        "SIE.DE","SAP.DE","VOW3.DE","BMW.DE","BAS.DE","ALV.DE","DAI.DE",
        "AIR.PA","BN.PA","MC.PA","OR.PA","SAN.PA","TTE.PA","FR.PA",
        "NESN.SW","ROG.SW","NOVN.SW","UBSG.SW","CSGN.SW","ZURN.SW",
        "ULVR.L","BP.L","RIO.L","HSBA.L","AZN.L","GSK.L","BATS.L","DGE.L","REL.L",
        "ENEL.MI","ISP.MI","ENI.MI","STLAM.MI","UCG.MI","PST.MI",
        "SAN.MC","BBVA.MC","ITX.MC","IBE.MC","REP.MC","TEF.MC","AENA.MC","MAP.MC",
        "ASML.AS","INGA.AS","PHIA.AS","AD.AS","UNA.AS",
        "EURUSD=X","GBPUSD=X","EURCHF=X","USDCHF=X","EURGBP=X","EURNOK=X","EURSEK=X",
        "BTC-EUR","ETH-EUR","SOL-EUR","ADA-EUR"
    ],
    "ASIA": [
        "^N225","^HSI","^BSESN","^KS11","^TWII","^AXJO","^STI","^JKSE",
        "7203.T","6758.T","9984.T","8035.T","7974.T","9433.T","9434.T","8766.T",
        "005930.KS","000660.KS","035420.KS","051910.KS","006400.KS",
        "2317.TW","2330.TW","2454.TW","2303.TW","2308.TW",
        "BABA","JD","PDD","TCEHY","NTES","BIDU","NIO","XPEV","LI",
        "RELIANCE.NS","INFY.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","HINDUNILVR.NS",
        "BHP.AX","RIO.AX","CBA.AX","NAB.AX","WBC.AX",
        "BTC-USD","ETH-USD","SOL-USD","XRP-USD","TRX-USD","ADA-USD","AVAX-USD",
        "USDJPY=X","AUDUSD=X","USDCNH=X","USDINR=X","USDSGD=X","USDKRW=X","USDTWD=X",
        "GC=F","SI=F","CL=F"
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
    try: _http.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
    except Exception as e: print(f"[ERROR] Telegram text: {e}")

def send_telegram_photo(caption, img, filename="chart.png"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try: _http.post(url, files={"photo": (filename, img)}, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, timeout=20)
    except Exception as e: print(f"[ERROR] Telegram photo: {e}")

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
            df = yf.download(tk, period="60d", interval="1h", auto_adjust=True, progress=False)
        else:
            df = yf.download(tk, period="1y", interval="1d", auto_adjust=True, progress=False)
        return df.dropna()
    except: return pd.DataFrame()

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
def loop():
    send_telegram_text("✅ ULTRA Bot iniciado sin errores en Render.")
    while True:
        region = get_region_by_time()
        print(f"[{utc_now()}] Región activa: {region}")
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
                print(f"[{utc_now()}] Señal enviada: {tk} {tend}")
            except Exception as e:
                print(f"[{utc_now()}] {tk} error: {e}")
        print(f"[{utc_now()}] Ciclo terminado.\n")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    # Iniciar servidor de health check en thread separado
    health_thread = Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Iniciar bot principal
    try:
        loop()
    except Exception:
        err = traceback.format_exc()
        print(err)
        send_telegram_text(f"⚠️ Error crítico:\n{err[:3500]}")
