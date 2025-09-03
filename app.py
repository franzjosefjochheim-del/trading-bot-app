import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime, timedelta
import pytz
import os
from dotenv import load_dotenv
import ta

# 🔐 Lade Umgebungsvariablen
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL")

# 🔌 Alpaca Clients
data_client = StockHistoricalDataClient(API_KEY, API_SECRET)
trading_client = TradingClient(API_KEY, API_SECRET, paper=True)

# 🎯 Streamlit UI
st.set_page_config(page_title="Trading-Bot (MA + RSI)", layout="centered")
st.title("📈 Automatisierter Trading-Bot (MA + RSI)")

# Eingabe
symbol = st.text_input("🔍 Tickersymbol eingeben", value="AAPL")

# Nur 1D als Zeitrahmen erlauben
st.selectbox("⏱ Zeitrahmen", ["1D"], index=0)
st.info("📢 Nur Tagesdaten (1D) werden unterstützt – kostenloser IEX-Feed aktiv.")

short_window = st.slider("📉 Kurzfristiger MA", min_value=5, max_value=50, value=10)
long_window = st.slider("📈 Langfristiger MA", min_value=20, max_value=200, value=50)
rsi_period = st.slider("📊 RSI-Periode", min_value=5, max_value=30, value=14)
order_qty = st.number_input("📦 Order-Menge", min_value=1, value=1)

# Start-Button
if st.button("🔎 Analyse starten"):
    try:
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=365)

        # 📊 Hole historische Tagesdaten mit feed='iex'
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date,
            feed="iex"
        )
        bars = data_client.get_stock_bars(request).df

        if bars.empty:
            st.error("❌ Keine Daten gefunden – bitte Symbol prüfen.")
        else:
            df = bars[bars.index.get_level_values(0) == symbol].copy()
            df["SMA_short"] = df["close"].rolling(window=short_window).mean()
            df["SMA_long"] = df["close"].rolling(window=long_window).mean()
            df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=rsi_period).rsi()

            latest = df.iloc[-1]
            previous = df.iloc[-2]

            # 📈 Visualisierung
            st.subheader("📊 Kursdiagramm")
            fig, ax = plt.subplots()
            ax.plot(df.index, df["close"], label="Close")
            ax.plot(df.index, df["SMA_short"], label=f"MA {short_window}")
            ax.plot(df.index, df["SMA_long"], label=f"MA {long_window}")
            ax.legend()
            st.pyplot(fig)

            # 📊 RSI Plot
            st.subheader("📉 RSI-Indikator")
            fig2, ax2 = plt.subplots()
            ax2.plot(df.index, df["RSI"], label="RSI", color="purple")
            ax2.axhline(70, color='red', linestyle='--')
            ax2.axhline(30, color='green', linestyle='--')
            ax2.legend()
            st.pyplot(fig2)

            # 📋 Strategie-Logik
            if (
                previous["SMA_short"] < previous["SMA_long"]
                and latest["SMA_short"] > latest["SMA_long"]
                and latest["RSI"] < 70
            ):
                st.success("🟢 Kaufsignal erkannt – Order wird gesendet...")

                order = MarketOrderRequest(
                    symbol=symbol,
                    qty=order_qty,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
                response = trading_client.submit_order(order)
                st.write("✅ Order gesendet:", response)

            elif latest["RSI"] > 70:
                st.warning("🔴 RSI überkauft – kein Einstieg empfohlen.")
            else:
                st.info("ℹ️ Kein Handelssignal aktuell.")
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
