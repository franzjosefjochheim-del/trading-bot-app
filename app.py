import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import os

# Alpaca API Keys aus Umgebungsvariablen laden (.env oder Render-Konfiguration)
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Streamlit UI
st.set_page_config(page_title="Trading-Bot (MA + RSI)", layout="centered")

st.title("📈 Automatisierter Trading-Bot (MA + RSI)")
symbol = st.text_input("🔍 Tickersymbol eingeben", value="AAPL").upper()

timeframes = {
    "1Min": TimeFrame.Minute,
    "5Min": TimeFrame.Minute,
    "15Min": TimeFrame.Minute,
    "1H": TimeFrame.Hour,
    "1D": TimeFrame.Day
}
selected_tf = st.selectbox("⏱ Zeitrahmen", list(timeframes.keys()))
timeframe = timeframes[selected_tf]

short_window = st.slider("📉 Kurzfristiger MA", min_value=5, max_value=50, value=10)
long_window = st.slider("📈 Langfristiger MA", min_value=20, max_value=200, value=50)
rsi_period = st.slider("📊 RSI-Periode", min_value=5, max_value=30, value=14)
order_qty = st.number_input("🍩 Order-Menge", min_value=1, step=1, value=1)

if st.button("🔍 Analyse starten"):

    try:
        # Alpaca Clients
        data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

        # Zeitbereich
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=100)

        # Daten anfragen mit feed='iex'
        request_params = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=timeframe,
            start=start_date,
            end=end_date,
            feed="iex"  # kostenloses Feed
        )

        bars = data_client.get_stock_bars(request_params).df

        if bars.empty:
            st.error("⚠️ Keine Daten gefunden. Versuche einen anderen Zeitraum oder Ticker.")
        else:
            bars = bars[bars.symbol == symbol]

            bars['SMA_short'] = bars['close'].rolling(window=short_window).mean()
            bars['SMA_long'] = bars['close'].rolling(window=long_window).mean()

            delta = bars['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=rsi_period).mean()
            avg_loss = loss.rolling(window=rsi_period).mean()
            rs = avg_gain / avg_loss
            bars['RSI'] = 100 - (100 / (1 + rs))

            # Plot
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(bars.index, bars['close'], label='Kurs')
            ax.plot(bars.index, bars['SMA_short'], label=f'MA {short_window}')
            ax.plot(bars.index, bars['SMA_long'], label=f'MA {long_window}')
            ax.set_title(f"{symbol} - Kurs mit MA")
            ax.legend()
            st.pyplot(fig)

            # RSI Plot
            fig2, ax2 = plt.subplots(figsize=(12, 3))
            ax2.plot(bars.index, bars['RSI'], color='purple', label='RSI')
            ax2.axhline(70, color='red', linestyle='--', label='Overbought')
            ax2.axhline(30, color='green', linestyle='--', label='Oversold')
            ax2.set_title("RSI")
            ax2.legend()
            st.pyplot(fig2)

            # Signal logik
            last = bars.iloc[-1]
            signal = None
            if (
                last['SMA_short'] > last['SMA_long']
                and last['RSI'] < 30
            ):
                signal = "buy"
            elif (
                last['SMA_short'] < last['SMA_long']
                and last['RSI'] > 70
            ):
                signal = "sell"

            if signal:
                st.success(f"📢 Signal erkannt: {signal.upper()}")

                try:
                    order_data = MarketOrderRequest(
                        symbol=symbol,
                        qty=order_qty,
                        side=OrderSide.BUY if signal == "buy" else OrderSide.SELL,
                        time_in_force=TimeInForce.DAY
                    )
                    order = trading_client.submit_order(order_data)
                    st.success(f"✅ Order ausgeführt: {order.side} {order.qty} {order.symbol}")
                except Exception as e:
                    st.error(f"❌ Order-Fehler: {e}")
            else:
                st.info("ℹ️ Kein klares Kaufs- oder Verkaufssignal.")

    except Exception as e:
        st.error(f"❌ Fehler: {e}")
