import streamlit as st
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
from ta.volatility import BollingerBands
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import yfinance as yf
import pytz
import os

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="Trading Bot mit Bollinger Bands", page_icon="📈")

st.title("📊 Trading Bot mit Bollinger Bands")

# 🧠 Setze deine Alpaca API Keys (ggf. über .env oder Render Environment)
ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

# -------------------------------
# FUNKTION: Daten holen
# -------------------------------
def get_data(symbol: str, start_date: dt.date, end_date: dt.date):
    if symbol == "BTC/USD" or symbol == "BTC-USD":
        # Krypto von Yahoo Finance
        return yf.download("BTC-USD", start=start_date, end=end_date)

    else:
        # Aktien von Alpaca
        request = StockBarsRequest(
            symbol=symbol,
            start=pd.Timestamp(start_date, tz=pytz.UTC),
            end=pd.Timestamp(end_date, tz=pytz.UTC),
            timeframe=TimeFrame.Day
        )
        bars = client.get_stock_bars(request).df
        if bars.empty:
            return pd.DataFrame()
        return bars.reset_index().set_index("timestamp")


# -------------------------------
# FUNKTION: Plot Bollinger Bands
# -------------------------------
def plot_bollinger_bands(data: pd.DataFrame, symbol: str):
    indicator = BollingerBands(close=data["close"], window=20, window_dev=2)
    data['bb_bbm'] = indicator.bollinger_mavg()
    data['bb_bbh'] = indicator.bollinger_hband()
    data['bb_bbl'] = indicator.bollinger_lband()

    st.subheader(f"Bollinger Bands für {symbol}")
    fig, ax = plt.subplots()
    ax.plot(data.index, data["close"], label="Kurs", color="blue")
    ax.plot(data.index, data["bb_bbm"], label="BB Mitte", linestyle="--")
    ax.plot(data.index, data["bb_bbh"], label="BB Hoch", linestyle="--")
    ax.plot(data.index, data["bb_bbl"], label="BB Tief", linestyle="--")
    ax.fill_between(data.index, data["bb_bbl"], data["bb_bbh"], alpha=0.1)
    ax.set_title(f"{symbol} Bollinger Bands")
    ax.legend()
    st.pyplot(fig)

# -------------------------------
# UI
# -------------------------------
symbol = st.selectbox("Wähle ein Symbol", ["AAPL", "BTC/USD"])
start_date = st.date_input("Startdatum", dt.date.today() - dt.timedelta(days=180))
end_date = st.date_input("Enddatum", dt.date.today())

if st.button("🧪 Analyse starten"):
    try:
        st.info(f"Hole Daten für {symbol}...")
        df = get_data(symbol, start_date, end_date)

        if df.empty:
            st.warning("Keine Daten verfügbar.")
        else:
            # Vereinheitliche Spaltennamen
            if 'Close' in df.columns:
                df.rename(columns={'Close': 'close'}, inplace=True)
            elif 'close' not in df.columns:
                raise ValueError("Spalte 'close' fehlt im DataFrame.")

            plot_bollinger_bands(df, symbol)

    except Exception as e:
        st.error(f"Fehler beim Abrufen von {symbol}-Daten: {e}")
