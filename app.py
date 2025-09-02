import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide
from ta.volatility import BollingerBands

import os

# ⏱ Zeitintervall
TIMEFRAME = TimeFrame.Hour  # kurzfristiger als 1Day

# 🔐 Umgebungsvariablen
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# 🧠 Clients
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
stock_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()

# 🎯 Funktion zum Abrufen der Daten
def get_data(symbol, start, end):
    if symbol == "BTC/USD":
        request = CryptoBarsRequest(
            symbol_or_symbols="BTC/USD",
            timeframe=TIMEFRAME,
            start=start,
            end=end
        )
        bars = crypto_client.get_crypto_bars(request).df
        df = bars[bars['symbol'] == 'BTC/USD'].copy()
    else:
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TIMEFRAME,
            start=start,
            end=end,
            feed='iex'  # FIXED: kein Enum
        )
        try:
            bars = stock_client.get_stock_bars(request).df
            df = bars[bars['symbol'] == symbol].copy()
        except Exception as e:
            st.error(f"Fehler beim Abrufen von {symbol}-Daten: {e}")
            return pd.DataFrame()

    df = df.sort_index()
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df.dropna(subset=['close'], inplace=True)
    return df

# 📈 Bollinger Bands Strategie
def apply_bollinger_strategy(df):
    indicator = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_mavg'] = indicator.bollinger_mavg()
    df['bb_upper'] = indicator.bollinger_hband()
    df['bb_lower'] = indicator.bollinger_lband()

    df['signal'] = 0
    df.loc[df['close'] < df['bb_lower'], 'signal'] = 1  # Kaufen
    df.loc[df['close'] > df['bb_upper'], 'signal'] = -1  # Verkaufen

    return df

# 🛒 Order senden
def submit_order(symbol, qty, side):
    try:
        order = MarketOrderRequest(
            symbol=symbol.replace("/", ""),  # BTC/USD → BTCUSD
            qty=qty,
            side=side,
            time_in_force="gtc"
        )
        trading_client.submit_order(order)
        st.success(f"{side.upper()} order submitted for {symbol} ({qty})")
    except Exception as e:
        st.error(f"Order konnte nicht gesendet werden: {e}")

# 🎨 Streamlit UI
st.set_page_config(layout="wide")
st.title("📊 Trading Bot mit Bollinger Bands")

symbol = st.selectbox("Wähle ein Symbol", ["AAPL", "MSFT", "TSLA", "BTC/USD"])
start_date = datetime.now() - timedelta(days=30)
end_date = datetime.now()

if st.button("📈 Analyse starten"):
    data = get_data(symbol, start_date, end_date)

    if data.empty:
        st.warning("Keine Daten verfügbar.")
    else:
        df = apply_bollinger_strategy(data)

        st.subheader("Bollinger Bands")
        st.line_chart(df[['close', 'bb_upper', 'bb_lower']])

        latest_signal = df['signal'].iloc[-1]
        st.write(f"Aktuelles Signal: {'🟢 Kaufen' if latest_signal == 1 else '🔴 Verkaufen' if latest_signal == -1 else '⚪️ Halten'}")

        if latest_signal == 1:
            if st.button("Jetzt kaufen"):
                submit_order(symbol, 1, OrderSide.BUY)

        elif latest_signal == -1:
            if st.button("Jetzt verkaufen"):
                submit_order(symbol, 1, OrderSide.SELL)
