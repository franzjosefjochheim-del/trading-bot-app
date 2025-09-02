# trading_bot_app/app.py

import streamlit as st
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import StockFeed
from datetime import datetime, timedelta
from ta.volatility import BollingerBands
import os

# ⭐ ENV-VARIABLEN von Render verwenden
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# === UI ===
st.set_page_config(page_title="Trading Bot", layout="wide")
st.title("💰 Trading Bot mit Bollinger Bands")

symbol = st.selectbox("Asset auswählen", ["AAPL", "TSLA", "MSFT", "BTC/USD"])
timeframe_str = st.selectbox("Zeitintervall", ["1Min", "5Min", "15Min", "1Hour", "1Day"])
period_days = st.slider("Vergangene Tage", 1, 60, 10)

# === Zeitkonfiguration ===
now = datetime.utcnow()
start_date = now - timedelta(days=period_days)

# === Daten abrufen ===
def fetch_data(symbol, timeframe_str, start_date, now):
    tf_map = {
        "1Min": TimeFrame.Minute,
        "5Min": TimeFrame(5, TimeFrame.Unit.Minute),
        "15Min": TimeFrame(15, TimeFrame.Unit.Minute),
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day
    }
    timeframe = tf_map[timeframe_str]

    if "/" in symbol:  # Crypto
        crypto_client = CryptoHistoricalDataClient()
        request_params = CryptoBarsRequest(symbols=[symbol], timeframe=timeframe, start=start_date, end=now)
        bars = crypto_client.get_crypto_bars(request_params).df
    else:  # Stocks
        stock_client = StockHistoricalDataClient(API_KEY, SECRET_KEY, feed=StockFeed.IEX)
        request_params = StockBarsRequest(symbol_or_symbols=symbol, timeframe=timeframe, start=start_date, end=now)
        bars = stock_client.get_stock_bars(request_params).df

    if bars.empty:
        st.warning("Keine Daten verfügbar für diese Auswahl.")
        return pd.DataFrame()

    bars = bars[bars.index.get_level_values("symbol") == symbol]
    bars = bars.reset_index()
    return bars

# === Bollinger Bands Strategie ===
def bollinger_strategy(df):
    if df.empty:
        return df, []

    indicator_bb = BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_m"] = indicator_bb.bollinger_mavg()
    df["bb_h"] = indicator_bb.bollinger_hband()
    df["bb_l"] = indicator_bb.bollinger_lband()

    signals = []
    for i in range(1, len(df)):
        if df["close"].iloc[i - 1] > df["bb_l"].iloc[i - 1] and df["close"].iloc[i] < df["bb_l"].iloc[i]:
            signals.append((df["timestamp"].iloc[i], "BUY"))
        elif df["close"].iloc[i - 1] < df["bb_h"].iloc[i - 1] and df["close"].iloc[i] > df["bb_h"].iloc[i]:
            signals.append((df["timestamp"].iloc[i], "SELL"))

    return df, signals

# === Hauptlogik ===
data = fetch_data(symbol, timeframe_str, start_date, now)

if not data.empty:
    data, signals = bollinger_strategy(data)

    st.subheader(f"{symbol} Kursdaten mit Bollinger Bands")
    st.line_chart(data.set_index("timestamp")["close"], height=300)
    st.line_chart(data.set_index("timestamp")[["bb_m", "bb_h", "bb_l"]], height=300)

    if signals:
        st.success(f"{len(signals)} Handelssignale gefunden:")
        for ts, sig in signals:
            st.write(f"{sig} am {ts}")
    else:
        st.info("Keine Handelssignale gefunden.")
else:
    st.stop()

# === DEBUG ===
with st.expander("Rohdaten anzeigen"):
    st.dataframe(data)
