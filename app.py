import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Verhindert Matplotlib-Fontcache-Fehler beim Render-Deploy
matplotlib.use("Agg")

# .env laden
load_dotenv()

# Alpaca-API Schlüssel
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Alpaca-Client
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

# Streamlit App
st.set_page_config(page_title="📈 Automatisierter Trading-Bot", layout="centered")
st.title("📈 Automatisierter Trading-Bot (MA + RSI)")

symbol = st.text_input("🔍 Tickersymbol eingeben", "AAPL")
timeframe_str = st.selectbox("🕒 Zeitrahmen", ["1Min", "5Min", "15Min", "1H", "1D"])
short_window = st.slider("📉 Kurzfristiger MA", 1, 50, 10)
long_window = st.slider("📈 Langfristiger MA", 10, 200, 50)
rsi_period = st.slider("📊 RSI-Periode", 2, 50, 14)
order_qty = st.number_input("📃 Order-Menge", min_value=1, value=1, step=1)

timeframe_mapping = {
    "1Min": TimeFrame.Minute,
    "5Min": TimeFrame.Minute,  # später ggf. auf Minute5 anpassen, wenn verfügbar
    "15Min": TimeFrame.Minute,
    "1H": TimeFrame.Hour,
    "1D": TimeFrame.Day
}

if st.button("🔎 Analyse starten"):
    try:
        timeframe = timeframe_mapping[timeframe_str]
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=100)

        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe,
            start=start_date,
            end=end_date,
            feed="iex"
        )

        bars = data_client.get_stock_bars(request_params).df

        if bars.empty:
            st.warning("⚠️ Keine Daten gefunden.")
        else:
            df = bars[bars['symbol'] == symbol].copy()
            df['MA_short'] = df['close'].rolling(window=short_window).mean()
            df['MA_long'] = df['close'].rolling(window=long_window).mean()

            delta = df['close'].diff()
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = pd.Series(gain).rolling(window=rsi_period).mean()
            avg_loss = pd.Series(loss).rolling(window=rsi_period).mean()
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))

            latest = df.iloc[-1]
            previous = df.iloc[-2]

            decision = "📍 Kein Signal"
            if latest['MA_short'] > latest['MA_long'] and previous['MA_short'] <= previous['MA_long'] and latest['RSI'] < 70:
                decision = "🟢 KAUFEN"
                order = MarketOrderRequest(
                    symbol=symbol,
                    qty=order_qty,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
                trading_client.submit_order(order)
            elif latest['MA_short'] < latest['MA_long'] and previous['MA_short'] >= previous['MA_long'] and latest['RSI'] > 30:
                decision = "🔴 VERKAUFEN"
                order = MarketOrderRequest(
                    symbol=symbol,
                    qty=order_qty,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                trading_client.submit_order(order)

            st.success(f"📌 Entscheidung: {decision}")

            # Chart anzeigen
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(df.index, df['close'], label='Kurs')
            ax.plot(df.index, df['MA_short'], label=f'MA {short_window}')
            ax.plot(df.index, df['MA_long'], label=f'MA {long_window}')
            ax.set_title(f"{symbol} Chart mit MA + RSI")
            ax.legend()
            st.pyplot(fig)

            # RSI anzeigen
            st.line_chart(df['RSI'])

    except Exception as e:
        st.error(f"❌ Fehler: {e}")
