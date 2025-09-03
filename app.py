import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Load environment variables
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Clients
stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# TimeFrame mapping
TIMEFRAME_MAP = {
    "1Min": TimeFrame(unit=TimeFrameUnit.Minute, value=1),
    "5Min": TimeFrame(unit=TimeFrameUnit.Minute, value=5),
    "15Min": TimeFrame(unit=TimeFrameUnit.Minute, value=15),
    "1H": TimeFrame(unit=TimeFrameUnit.Hour, value=1),
    "1D": TimeFrame(unit=TimeFrameUnit.Day, value=1),
}

# Technical Indicators
def calculate_bollinger_bands(df, window=20, num_std=2):
    df['SMA'] = df['close'].rolling(window=window).mean()
    df['Upper'] = df['SMA'] + num_std * df['close'].rolling(window=window).std()
    df['Lower'] = df['SMA'] - num_std * df['close'].rolling(window=window).std()
    return df

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def calculate_ema(df, span=20):
    df['EMA'] = df['close'].ewm(span=span, adjust=False).mean()
    return df

# Data fetching
def get_data(symbol, start, end, timeframe):
    if symbol == "BTC/USD":
        request = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            start=start,
            end=end,
            timeframe=timeframe
        )
        bars = crypto_client.get_crypto_bars(request).df
    else:
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            start=start,
            end=end,
            timeframe=timeframe
        )
        bars = stock_client.get_stock_bars(request).df

    if symbol in bars.index.names:
        bars = bars.xs(symbol, level="symbol")

    return bars

# Trading logic
def should_buy(df):
    return df['close'].iloc[-1] < df['Lower'].iloc[-1]

def should_sell(df):
    return df['close'].iloc[-1] > df['Upper'].iloc[-1]

def place_order(symbol, side):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=1,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    trading_client.submit_order(order)

# Streamlit UI
st.title("📈 Trading Bot mit Bollinger Bands, RSI & EMA")

symbol = st.selectbox("Wähle das Symbol:", ["AAPL", "GOOG", "MSFT", "BTC/USD"])
interval = st.selectbox("Intervall", list(TIMEFRAME_MAP.keys()), index=1)
days = st.slider("Zeitraum (in Tagen)", 1, 90, 7)

start_date = datetime.now() - timedelta(days=days)
end_date = datetime.now()

if st.button("🚀 Starte Analyse"):
    try:
        df = get_data(symbol, start_date, end_date, TIMEFRAME_MAP[interval])
        df = calculate_bollinger_bands(df)
        df = calculate_rsi(df)
        df = calculate_ema(df)

        st.subheader(f"📊 Chart für {symbol}")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df['close'], label="Close")
        ax.plot(df.index, df['Upper'], label="Upper BB", linestyle='--')
        ax.plot(df.index, df['Lower'], label="Lower BB", linestyle='--')
        ax.plot(df.index, df['EMA'], label="EMA", linestyle=':")
        ax.set_title(f"{symbol} Preis & Bollinger Bands")
        ax.legend()
        st.pyplot(fig)

        st.subheader("📈 RSI")
        st.line_chart(df['RSI'])

        # Automatische Entscheidung & Order
        if should_buy(df):
            st.success("Bollinger Signal: BUY")
            place_order(symbol.replace("/", ""), OrderSide.BUY)
        elif should_sell(df):
            st.error("Bollinger Signal: SELL")
            place_order(symbol.replace("/", ""), OrderSide.SELL)
        else:
            st.info("Kein klares Signal aktuell.")

    except Exception as e:
        st.error(f"Fehler: {e}")
