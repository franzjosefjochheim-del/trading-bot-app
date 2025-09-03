import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import os

# === Authentifizierung ===
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# === UI ===
st.title("📊 Trading Bot App mit Strategien")

symbol = st.selectbox("Symbol", ["AAPL", "MSFT", "GOOG", "BTC/USD"])
interval = st.selectbox("Intervall", ["1Min", "5Min", "15Min", "1H", "1D"])
strategy = st.selectbox("Strategie", ["Bollinger", "RSI", "EMA", "Bollinger + RSI"])
auto_trade = st.checkbox("🚀 Auto-Trading aktivieren")
stop_loss_pct = st.slider("Stop-Loss %", 1, 20, 5)
take_profit_pct = st.slider("Take-Profit %", 1, 50, 10)

start_date = datetime.now() - timedelta(days=3)
end_date = datetime.now()

TIMEFRAME_MAP = {
    "1Min": TimeFrame.Minute,
    "5Min": TimeFrame.Minute5,
    "15Min": TimeFrame.Minute15,
    "1H": TimeFrame.Hour,
    "1D": TimeFrame.Day
}

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
    return bars[bars.index.get_level_values("symbol") == symbol].copy()

def calculate_indicators(df):
    df['EMA20'] = df['close'].ewm(span=20).mean()
    df['RSI'] = compute_rsi(df['close'])
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['STD'] = df['close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def signal_strategy(df):
    last = df.iloc[-1]
    if strategy == "Bollinger":
        if last['close'] < last['Lower']:
            return "BUY"
        elif last['close'] > last['Upper']:
            return "SELL"
    elif strategy == "RSI":
        if last['RSI'] < 30:
            return "BUY"
        elif last['RSI'] > 70:
            return "SELL"
    elif strategy == "EMA":
        if last['close'] > last['EMA20']:
            return "BUY"
        elif last['close'] < last['EMA20']:
            return "SELL"
    elif strategy == "Bollinger + RSI":
        if last['close'] < last['Lower'] and last['RSI'] < 30:
            return "BUY"
        elif last['close'] > last['Upper'] and last['RSI'] > 70:
            return "SELL"
    return "HOLD"

def place_order(signal, symbol, qty=1):
    side = OrderSide.BUY if signal == "BUY" else OrderSide.SELL
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    trading_client.submit_order(order)

# === Hauptlogik ===
if st.button("📈 Strategie prüfen") or auto_trade:
    df = get_data(symbol, start_date, end_date, TIMEFRAME_MAP[interval])
    df = calculate_indicators(df)
    sig = signal_strategy(df)
    st.subheader(f"Signal: {sig}")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df['close'], label='Close')
    ax.plot(df['EMA20'], label='EMA20')
    ax.plot(df['Upper'], label='Upper BB')
    ax.plot(df['Lower'], label='Lower BB')
    ax.set_title(f"{symbol} mit {strategy}")
    ax.legend()
    st.pyplot(fig)

    if sig in ["BUY", "SELL"] and auto_trade:
        st.info(f"🚀 Platziere Order: {sig}")
        place_order(sig, symbol)
    elif sig in ["BUY", "SELL"]:
        if st.button(f"🛒 Manuell {sig} ausführen"):
            place_order(sig, symbol)
            st.success(f"Order {sig} platziert!")
