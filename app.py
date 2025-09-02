import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 🔑 Authentifizierung
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    st.error("API-Schlüssel fehlen. Bitte Umgebungsvariablen setzen.")
    st.stop()

stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# 🌐 UI Setup
st.set_page_config(page_title="Trading Bot", layout="centered")
st.title("📊 Trading Bot mit Bollinger Bands")

symbol = st.selectbox("Wähle ein Symbol", ["AAPL", "BTC/USD"])
timeframe_str = st.selectbox("Zeitintervall", ["5Min", "15Min", "1Hour", "1Day"])

start_date = datetime.now() - timedelta(days=5)
end_date = datetime.now()

def get_timeframe_object(tf):
    return {
        "5Min": TimeFrame.Minute,
        "15Min": TimeFrame.Minute,
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day
    }[tf]

def get_data(symbol, start, end, timeframe):
    tf_obj = get_timeframe_object(timeframe)
    try:
        if symbol == "BTC/USD":
            request = CryptoBarsRequest(
                symbol_or_symbols="BTC/USD",
                timeframe=tf_obj,
                start=start,
                end=end
            )
            bars = crypto_client.get_crypto_bars(request).df
            return bars[bars['symbol'] == 'BTC/USD'].copy()
        else:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf_obj,
                start=start,
                end=end
            )
            bars = stock_client.get_stock_bars(request).df
            return bars[bars['symbol'] == symbol].copy()
    except Exception as e:
        st.error(f"Fehler beim Abrufen von {symbol}-Daten: {e}")
        return pd.DataFrame()

def calculate_bollinger_bands(df, window=20, num_std=2):
    df['sma'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upper'] = df['sma'] + (df['std'] * num_std)
    df['lower'] = df['sma'] - (df['std'] * num_std)
    return df

def signal_bollinger(df):
    if df.empty or df['close'].isnull().all():
        return "HOLD"
    latest = df.iloc[-1]
    if latest['close'] < latest['lower']:
        return "BUY"
    elif latest['close'] > latest['upper']:
        return "SELL"
    return "HOLD"

def place_order(symbol, side):
    try:
        order = MarketOrderRequest(
            symbol=symbol,
            qty=1,
            side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        trading_client.submit_order(order)
        st.success(f"{side} Order für {symbol} platziert!")
    except Exception as e:
        st.error(f"Order-Fehler: {e}")

# ⚙️ Analyse starten
if st.button("🔍 Analyse starten"):
    bars = get_data(symbol, start_date, end_date, timeframe_str)

    if bars.empty:
        st.warning("Keine Daten verfügbar.")
    else:
        df = calculate_bollinger_bands(bars)
        signal = signal_bollinger(df)

        st.subheader(f"Signal: {signal}")

        # 📈 Plot
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df.index, df['close'], label='Close')
        ax.plot(df.index, df['upper'], label='Upper Band', linestyle='--')
        ax.plot(df.index, df['lower'], label='Lower Band', linestyle='--')
        ax.fill_between(df.index, df['lower'], df['upper'], color='gray', alpha=0.1)
        ax.set_title(f"{symbol} Bollinger Bands")
        ax.legend()
        st.pyplot(fig)

        # 🚀 Automatische Order bei Aktien
        if symbol != "BTC/USD" and signal in ["BUY", "SELL"]:
            place_order(symbol, signal)
