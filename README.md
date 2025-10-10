# 🤖 Trading Bot Ultra - 24/7

Bot de análisis técnico automático con rotación por regiones (América, México, Europa, Asia).

## 🚀 Características

- ✅ Análisis técnico avanzado (EMA, RSI, MACD, ATR)
- 🌍 Rotación automática por zona horaria
- 📊 Gráficos automáticos
- 📱 Notificaciones a Telegram
- 🔄 Ejecución continua 24/7

## 📦 Despliegue en Render

### 1. Preparar repositorio GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin TU_URL_GITHUB
git push -u origin main
```

### 2. Configurar Render

1. Ve a [render.com](https://render.com) y crea una cuenta
2. Conecta tu cuenta de GitHub
3. Click en "New +" → "Web Service"
4. Selecciona tu repositorio
5. Render detectará automáticamente `render.yaml`

### 3. Configurar Variables de Entorno

En Render, ve a tu servicio → Environment y agrega:

```
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

### 4. Deploy

Render desplegará automáticamente. ¡Listo! 🎉

## 🔧 Ejecución Local

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
python pro_market_bot_ultra_fixed.py
```

## 📊 Activos Analizados

- **Índices**: S&P500, Nasdaq, DAX, Nikkei, etc.
- **Acciones**: Tech, Financiero, Consumo
- **Cripto**: BTC, ETH, SOL, ADA, etc.
- **Forex**: USD/MXN, EUR/USD, etc.
- **Commodities**: Oro, Plata, Petróleo

## ⚙️ Configuración

Edita estas variables en el código:

- `MIN_SCORE`: Score mínimo para señal (default: 60)
- `BULL_PROB`: Probabilidad alcista (default: 70%)
- `BEAR_PROB`: Probabilidad bajista (default: 30%)
- `POLL_SECONDS`: Tiempo entre análisis (default: 300s)

## 📝 Licencia

MIT

## 🤝 Contribuciones

Pull requests son bienvenidos.
