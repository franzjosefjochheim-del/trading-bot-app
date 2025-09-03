import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ta.volatility import BollingerBands
from datetime import datetime, timedelta
import os

from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# API Keys from Render environment
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Clients
stock_client = StockHistoricalDataClient(api_key=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# UI Title
st.title("📈 Trading Bot mit Bollinger Bands")

# Symbolauswahl
symbol = st.selectbox("Asset auswählen", ["AAPL", "MSFT", "GOOG", "BTC/USD"])

# Zeitraum
start_date = st.date_input("Startdatum", datetime.now() - timedelta(days=30))
end_date = st.date_input("Enddatum", datetime.now())

# Zeitintervall-Auswahl
interval = st.selectbox("Zeitintervall", ["1Min", "5Min", "15Min", "1H", "1D"])

TIMEFRAME_MAP = {
    "1Min": TimeFrame(1, TimeFrameUnit.Minute),
    "5Min": TimeFrame(5, TimeFrameUnit.Minute),
    "15Min": TimeFrame(15, TimeFrameUnit.Minute),
    "1H": TimeFrame(1, TimeFrameUnit.Hour),
    "1D": TimeFrame(1, TimeFrameUnit.Day)
}

# Funktion: Daten abrufen
def get_data(symbol, start, end, timeframe):
    if symbol == "BTC/USD":
        request_params = CryptoBarsRequest(
            symbol="BTC/USD",
            start=start,
            end=end,
            timeframe=timeframe
        )
        bars = crypto_client.get_crypto_bars(request_params).df
        bars = bars[bars['symbol'] == 'BTC/USD']
    else:
        request_params = StockBarsRequest(
            symbol=symbol,
            start=start,
            end=end,
            timeframe=timeframe
        )
        bars = stock_client.get_stock_bars(request_params).df
        bars = bars[bars['symbol'] == symbol]
    return bars.copy()

# Daten abrufen
data = get_data(symbol, start_date, end_date, TIMEFRAME_MAP[interval])

# Bollinger berechnen
indicator_bb = BollingerBands(close=data["close"], window=20, window_dev=2)
data["bb_bbm"] = indicator_bb.bollinger_mavg()
data["bb_bbh"] = indicator_bb.bollinger_hband()
data["bb_bbl"] = indicator_bb.bollinger_lband()

# Signale berechnen
data["Signal"] = np.where(data["close"] < data["bb_bbl"], "Buy",
                  np.where(data["close"] > data["bb_bbh"], "Sell", "Hold"))

# Chart anzeigen
st.subheader(f"Bollinger Chart für {symbol}")
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(data.index, data["close"], label="Close")
ax.plot(data.index, data["bb_bbm"], label="BB Mittelwert")
ax.plot(data.index, data["bb_bbh"], label="BB Hoch")
ax.plot(data.index, data["bb_bbl"], label="BB Tief")
ax.legend()
st.pyplot(fig)

# Letztes Signal
latest_signal = data["Signal"].iloc[-1]
st.markdown(f"### 📊 Letztes Signal: `{latest_signal}`")

# Auto-Trading
def place_order(symbol, side, qty=1):
    try:
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.DAY
        )
        order = trading_client.submit_order(order_data)
        st.success(f"✅ Order erfolgreich: {side.upper()} {qty} {symbol}")
    except Exception as e:
        st.error(f"❌ Fehler bei Order: {e}")

# Automatisches Handeln
if st.button("🚀 Automatisch handeln"):
    if latest_signal == "Buy":
        place_order(symbol.replace("/", ""), OrderSide.BUY)
    elif latest_signal == "Sell":
        place_order(symbol.replace("/", ""), OrderSide.SELL)
    else:
        st.info("Kein klares Signal. Keine Aktion.")

# Manuelle Orderbuttons
st.subheader("🛠️ Manuelle Order")
col1, col2 = st.columns(2)
with col1:
    if st.button("📈 BUY"):
        place_order(symbol.replace("/", ""), OrderSide.BUY)
with col2:
    if st.button("📉 SELL"):
        place_order(symbol.replace("/", ""), OrderSide.SELL)
