import streamlit as st
import alpaca_trade_api as tradeapi
import pandas as pd
import datetime
import os

st.set_page_config(page_title="Auto-Trader", layout="wide")
st.title("📈 Automatisierter Trading-Bot (MA + RSI)")

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

if not API_KEY or not SECRET_KEY:
    st.error("Bitte ALPACA_API_KEY und ALPACA_SECRET_KEY als Umgebungsvariablen setzen.")
    st.stop()

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

symbol = st.text_input("🪙 Tickersymbol eingeben", value="AAPL")
timeframe = st.selectbox("Zeitrahmen", ["1Min", "5Min", "15Min", "1D"], index=3)
ma_short = st.slider("Kurzfristiger MA", 5, 20, 10)
ma_long = st.slider("Langfristiger MA", 30, 100, 50)
rsi_period = st.slider("RSI-Periode", 5, 30, 14)

if st.button("🔍 Analyse starten"):
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=100)
    df = api.get_bars(
        symbol,
        timeframe,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d")
    ).df

    df = df[df['symbol'] == symbol]

    df['MA_Short'] = df['close'].rolling(ma_short).mean()
    df['MA_Long'] = df['close'].rolling(ma_long).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    st.line_chart(df[['close', 'MA_Short', 'MA_Long']].dropna())
    st.line_chart(df[['RSI']].dropna())

    latest = df.iloc[-1]
    signal = "📉 SELL" if latest.MA_Short < latest.MA_Long or latest.RSI < 40 else "📈 BUY" if latest.MA_Short > latest.MA_Long and latest.RSI > 50 else "⚠️ HOLD"
    st.subheader(f"Aktueller Handelssignal für {symbol}: {signal}")
