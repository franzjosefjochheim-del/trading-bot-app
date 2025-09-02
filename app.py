import streamlit as st
import pandas as pd
import datetime
import os
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# ⛔ Umgebungsvariablen (Render → Environment)
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Alpaca Clients
stock_client = StockHistoricalDataClient(API_KEY, API_SECRET)
crypto_client = CryptoHistoricalDataClient()
trading_client = TradingClient(API_KEY, API_SECRET, paper=True)

# Streamlit App
st.title("📈 Automatisierter Trading-Bot (MA/RSI + Bollinger)")

symbol = st.selectbox("🔍 Tickersymbol eingeben", ["AAPL", "BTC/USD"])
interval = st.selectbox("🕒 Zeitrahmen", ["1D", "1H", "15Min"])
short_ma = st.slider("📉 Kurzfristiger MA", 5, 20, 10)
long_ma = st.slider("📈 Langfristiger MA", 20, 100, 50)
rsi_period = st.slider("📊 RSI-Periode", 7, 21, 14)
quantity = st.number_input("📦 Order-Menge", min_value=1, value=1)

if st.button("🔍 Analyse starten"):
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=90)

    tf_map = {
        "1D": TimeFrame.Day,
        "1H": TimeFrame.Hour,
        "15Min": TimeFrame.Minute
    }

    tf = tf_map[interval]

    if symbol == "AAPL":
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            start=start,
            end=end,
            timeframe=tf
        )
        bars = stock_client.get_stock_bars(request_params).df
        data = bars[bars['symbol'] == symbol]
    else:
        request_params = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            start=start,
            end=end,
            timeframe=tf
        )
        bars = crypto_client.get_crypto_bars(request_params).df
        data = bars[bars['symbol'] == symbol]

    if data.empty:
        st.error("Keine Daten gefunden.")
        st.stop()

    # Signal-Strategie
    signal = "HOLD"

    if symbol == "AAPL":
        data["MA_Short"] = data["close"].rolling(window=short_ma).mean()
        data["MA_Long"] = data["close"].rolling(window=long_ma).mean()
        rsi = RSIIndicator(close=data["close"], window=rsi_period)
        data["RSI"] = rsi.rsi()

        if (
            data["MA_Short"].iloc[-1] > data["MA_Long"].iloc[-1]
            and data["RSI"].iloc[-1] < 70
        ):
            signal = "BUY"
        elif (
            data["MA_Short"].iloc[-1] < data["MA_Long"].iloc[-1]
            and data["RSI"].iloc[-1] > 30
        ):
            signal = "SELL"

        st.line_chart(data[["MA_Short", "MA_Long", "close"]])
        st.line_chart(data["RSI"])

    elif symbol == "BTC/USD":
        bb = BollingerBands(close=data["close"], window=20, window_dev=2)
        data["bb_mavg"] = bb.bollinger_mavg()
        data["bb_upper"] = bb.bollinger_hband()
        data["bb_lower"] = bb.bollinger_lband()

        if data["close"].iloc[-1] < data["bb_lower"].iloc[-1]:
            signal = "BUY"
        elif data["close"].iloc[-1] > data["bb_upper"].iloc[-1]:
            signal = "SELL"

        st.line_chart(data[["close", "bb_upper", "bb_lower"]])

    st.subheader(f"Aktueller Handelssignal für {symbol}: 📉 {signal}")

    if signal in ["BUY", "SELL"]:
        order = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY if signal == "BUY" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        try:
            trading_client.submit_order(order)
            st.success(f"✅ Order ausgeführt: {signal} {quantity} {symbol}")
        except Exception as e:
            st.error(f"❌ Fehler beim Ordern: {e}")
