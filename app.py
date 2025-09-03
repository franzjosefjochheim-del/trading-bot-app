import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# .env laden
load_dotenv()

# Alpaca API-Keys
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Clients
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

# Streamlit UI
st.set_page_config(page_title="Trading-Bot", layout="centered")
st.title("📈 Automatisierter Trading-Bot (MA + RSI)")

# Benutzer-Eingaben
symbol = st.text_input("🔍 Tickersymbol eingeben", value="AAPL")

st.selectbox("🕰️ Zeitrahmen", options=["1D"], index=0, disabled=True)
st.info("📉 Nur Tagesdaten (1D) werden unterstützt – kostenloser IEX-Feed aktiv.")

short_window = st.slider("🧪 Kurzfristiger MA", min_value=5, max_value=50, value=10)
long_window = st.slider("🧪 Langfristiger MA", min_value=20, max_value=200, value=50)
rsi_period = st.slider("📊 RSI-Periode", min_value=2, max_value=50, value=14)
order_qty = st.number_input("🥜 Order-Menge", min_value=1, value=1, step=1)

if st.button("🔍 Analyse starten"):
    try:
        # Daten abrufen
        end = datetime.now()
        start = end - timedelta(days=365)
        bars_request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed="iex"  # wichtig für kostenlose Nutzer
        )

        bars = data_client.get_stock_bars(bars_request).df

        if bars.empty:
            st.error("Keine Daten gefunden. Symbol korrekt?")
        else:
            df = bars[bars.index.get_level_values(0) == symbol].copy()
            df.index = df.index.droplevel(0)

            # Berechnungen
            df["SMA_short"] = SMAIndicator(df["close"], window=short_window).sma_indicator()
            df["SMA_long"] = SMAIndicator(df["close"], window=long_window).sma_indicator()
            df["RSI"] = RSIIndicator(df["close"], window=rsi_period).rsi()

            # Signale
            last_row = df.iloc[-1]
            signal = ""
            if last_row["SMA_short"] > last_row["SMA_long"] and last_row["RSI"] < 70:
                signal = "BUY"
            elif last_row["SMA_short"] < last_row["SMA_long"] and last_row["RSI"] > 30:
                signal = "SELL"
            else:
                signal = "HOLD"

            # Ergebnis anzeigen
            st.subheader("📈 Kursdiagramm")
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(df["close"], label="Kurs")
            ax.plot(df["SMA_short"], label=f"SMA {short_window}")
            ax.plot(df["SMA_long"], label=f"SMA {long_window}")
            ax.set_title(f"{symbol} Kurs + MA")
            ax.legend()
            st.pyplot(fig)

            st.subheader("🧠 Entscheidungslogik")
            st.write(f"Aktueller RSI: {last_row['RSI']:.2f}")
            st.write(f"Signal: **{signal}**")

            # Order
            if signal in ["BUY", "SELL"]:
                side = OrderSide.BUY if signal == "BUY" else OrderSide.SELL
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=order_qty,
                    side=side,
                    time_in_force=TimeInForce.DAY
                )
                try:
                    order = trading_client.submit_order(order_data)
                    st.success(f"✅ Order ausgeführt: {order.side.upper()} {order.qty} {symbol}")
                except Exception as e:
                    st.error(f"❌ Orderfehler: {e}")
            else:
                st.info("ℹ️ Kein Handelssignal. Keine Order ausgeführt.")

    except Exception as e:
        st.error(f"Fehler: {e}")
