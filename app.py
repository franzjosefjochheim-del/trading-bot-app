import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from ta.volatility import BollingerBands

from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
import pytz
import os

# 🌐 API-Zugangsdaten aus Umgebungsvariablen
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# 📦 Clients initialisieren mit benannten Parametern
stock_client = StockHistoricalDataClient(api_key=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()

# 📊 Streamlit UI
st.set_page_config(page_title="Trading Bot", layout="centered")
st.title("📊 Trading Bot mit Bollinger Bands")

symbol = st.selectbox("Wähle ein Symbol", ["AAPL", "BTC/USD"])
start_analysis = st.button("🔍 Analyse starten")

# Zeitintervall anpassen für kurzfristige Strategien
TIMEFRAME = TimeFrame.Hour  # z.B. 1-Stunden-Intervalle
DAYS_BACK = 14              # Datenzeitraum (verringert für Krypto-Performance)

def get_data(symbol, start, end):
    try:
        if symbol == "BTC/USD":
            request_params = CryptoBarsRequest(
                symbol="BTC/USD",
                timeframe=TIMEFRAME,
                start=start,
                end=end
            )
            bars = crypto_client.get_crypto_bars(request_params).df
            if bars.empty:
                return pd.DataFrame()
            df = bars[bars.index.get_level_values("symbol") == "BTC/USD"].copy()
        else:
            request_params = StockBarsRequest(
                symbol_or_symbols=["AAPL"],
                timeframe=TIMEFRAME,
                start=start,
                end=end
            )
            bars = stock_client.get_stock_bars(request_params, feed="iex").df
            if bars.empty:
                return pd.DataFrame()
            df = bars[bars.index.get_level_values("symbol") == "AAPL"].copy()
        
        df = df.reset_index()
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Europe/Berlin")
        df.set_index("timestamp", inplace=True)
        return df

    except Exception as e:
        st.error(f"Fehler beim Abrufen von {symbol}-Daten: {e}")
        return pd.DataFrame()

def plot_bollinger(df):
    indicator_bb = BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_bbm"] = indicator_bb.bollinger_mavg()
    df["bb_bbh"] = indicator_bb.bollinger_hband()
    df["bb_bbl"] = indicator_bb.bollinger_lband()

    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["close"], label="Close Price", color="blue")
    plt.plot(df.index, df["bb_bbm"], label="Bollinger MAVG", linestyle="--")
    plt.plot(df.index, df["bb_bbh"], label="Upper Band", linestyle="--")
    plt.plot(df.index, df["bb_bbl"], label="Lower Band", linestyle="--")
    plt.fill_between(df.index, df["bb_bbl"], df["bb_bbh"], alpha=0.2)
    plt.title(f"Bollinger Bands für {symbol}")
    plt.xlabel("Datum")
    plt.ylabel("Preis")
    plt.legend()
    st.pyplot(plt)

# ⏱ Daten abrufen und analysieren
if start_analysis:
    end_date = datetime.now(pytz.utc)
    start_date = end_date - timedelta(days=DAYS_BACK)

    data = get_data(symbol, start_date, end_date)

    if data.empty:
        st.warning("Keine Daten verfügbar.")
    else:
        plot_bollinger(data)
