import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta, timezone
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import os

# --- Zugriff auf Umgebungsvariablen ---
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# --- Alpaca-Clients initialisieren ---
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

# --- Streamlit UI Setup ---
st.set_page_config(page_title="Trading Bot (MA + RSI)", layout="centered")
st.title("📉 Automatisierter Trading-Bot (MA + RSI)")

symbol = st.text_input("🔍 Tickersymbol eingeben", value="AAPL")

timeframes = {
    "1Min": TimeFrame.Minute,
    "5Min": TimeFrame(5, TimeFrame.Unit.Minute),
    "15Min": TimeFrame(15, TimeFrame.Unit.Minute),
    "1H": TimeFrame.Hour,
    "1D": TimeFrame.Day,
}
timeframe_str = st.selectbox("🕰️ Zeitrahmen", list(timeframes.keys()))
timeframe = timeframes[timeframe_str]

short_window = st.slider("📉 Kurzfristiger MA", 5, 50, 10)
long_window = st.slider("📈 Langfristiger MA", 20, 200, 50)
rsi_period = st.slider("📊 RSI-Periode", 5, 30, 14)
qty = st.number_input("📃 Order-Menge", min_value=1, value=1)

if st.button("🔍 Analyse starten") and symbol:
    try:
        # 📅 Datenabrufzeitraum festlegen
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=60)

        # 📥 Daten abrufen
        request_params = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=timeframe,
            start=start_date,
            end=end_date,
        )
        bars = data_client.get_stock_bars(request_params)
        df = bars.data.get(symbol)

        if df is None or df.empty:
            st.error("❌ Keine Daten gefunden. Möglicherweise ungültiges Symbol oder Zeitrahmen.")
        else:
            df.index = pd.to_datetime(df.timestamp)
            df["SMA_short"] = df.close.rolling(window=short_window).mean()
            df["SMA_long"] = df.close.rolling(window=long_window).mean()

            delta = df.close.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(rsi_period).mean()
            avg_loss = loss.rolling(rsi_period).mean()
            rs = avg_gain / avg_loss
            df["RSI"] = 100 - (100 / (1 + rs))

            # 📈 Plotten
            st.subheader(f"Kursverlauf & Indikatoren für {symbol}")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df.close, label="Kurs")
            ax.plot(df.SMA_short, label=f"MA {short_window}")
            ax.plot(df.SMA_long, label=f"MA {long_window}")
            ax.set_title(f"{symbol} Kursdaten")
            ax.legend()
            st.pyplot(fig)

            # 📊 RSI anzeigen
            st.line_chart(df["RSI"])

            # ✅ Trading-Signale prüfen
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]

            signal = ""
            if (
                prev_row["SMA_short"] < prev_row["SMA_long"]
                and last_row["SMA_short"] > last_row["SMA_long"]
                and last_row["RSI"] < 70
            ):
                signal = "BUY"
            elif (
                prev_row["SMA_short"] > prev_row["SMA_long"]
                and last_row["SMA_short"] < last_row["SMA_long"]
                and last_row["RSI"] > 30
            ):
                signal = "SELL"

            if signal:
                st.success(f"📢 Trading-Signal erkannt: {signal}")

                try:
                    order = MarketOrderRequest(
                        symbol=symbol,
                        qty=qty,
                        side=OrderSide.BUY if signal == "BUY" else OrderSide.SELL,
                        time_in_force=TimeInForce.DAY,
                    )
                    response = trading_client.submit_order(order)
                    st.success(f"✅ Order ausgeführt: {response.id}")
                except Exception as e:
                    st.error(f"❌ Orderfehler: {e}")
            else:
                st.info("ℹ️ Kein klares Signal erkannt – keine Aktion durchgeführt.")

    except Exception as e:
        st.error(f"❌ Fehler: {e}")
