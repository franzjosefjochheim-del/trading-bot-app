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

# API Keys aus Umgebungsvariablen laden
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Clients initialisieren
stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()

# Streamlit UI
st.set_page_config(page_title="Trading Bot mit Bollinger Bands", page_icon=":chart_with_upwards_trend:")
st.title("📊 Trading Bot mit Bollinger Bands")
st.markdown("Wähle ein Symbol")

symbol = st.selectbox("Wähle ein Symbol", ["AAPL", "BTC/USD"])
start_analysis = st.button("🔍 Analyse starten")

# Daten abrufen
def get_data(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    if "USD" in symbol and "/" in symbol:  # BTC/USD
        request_params = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
        )
        bars = crypto_client.get_crypto_bars(request_params).df
    else:  # Aktie wie AAPL
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
        )
        bars = stock_client.get_stock_bars(request_params).df

    # Prüfen, ob Daten vorhanden sind
    if bars.empty:
        return pd.DataFrame()

    # Bei MultiIndex (mehrere Symbole) filtern
    if isinstance(bars.index, pd.MultiIndex):
        bars = bars.loc[symbol]

    bars = bars.reset_index()
    return bars

# Bollinger-Berechnung & Plot
def analyze_bollinger(data: pd.DataFrame):
    indicator_bb = BollingerBands(close=data["close"], window=20, window_dev=2)
    data["bb_bbm"] = indicator_bb.bollinger_mavg()
    data["bb_bbh"] = indicator_bb.bollinger_hband()
    data["bb_bbl"] = indicator_bb.bollinger_lband()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(data["timestamp"], data["close"], label="Kurs")
    ax.plot(data["timestamp"], data["bb_bbm"], label="BB Mittel")
    ax.plot(data["timestamp"], data["bb_bbh"], label="BB Obere")
    ax.plot(data["timestamp"], data["bb_bbl"], label="BB Untere")
    ax.set_title(f"Bollinger Bands für {symbol}")
    ax.set_xlabel("Datum")
    ax.set_ylabel("Preis")
    ax.legend()
    st.pyplot(fig)

# Analyse starten
if start_analysis:
    start_date = datetime.now(pytz.UTC) - timedelta(days=90)
    end_date = datetime.now(pytz.UTC)
    try:
        data = get_data(symbol, start_date, end_date)
        if data.empty:
            st.warning("Keine Daten verfügbar.")
        else:
            analyze_bollinger(data)
    except Exception as e:
        st.error(f"Fehler beim Abrufen von {symbol}-Daten: {e}")
