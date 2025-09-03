import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import pytz

# 🔑 Alpaca API Keys (Paper Trading)
ALPACA_API_KEY = "PKP5A2PXUW701XQZJIF5"
ALPACA_SECRET_KEY = "b7hVdlTr9PeHBVXQLsfJbimbprrUdPVtAhOHLQI7"

# 🌍 Zeitzone & Zeitraum
timezone = pytz.timezone("America/New_York")
end_date = datetime.now(tz=timezone)
start_date = end_date - timedelta(days=2)

# 🕐 Gültige Zeitintervalle
TIMEFRAME_MAP = {
    "1Min": TimeFrame.Minute,
    "5Min": TimeFrame.Min5,
    "15Min": TimeFrame.Min15,
    "1H": TimeFrame.Hour,
    "1D": TimeFrame.Day
}

# 📉 Bollinger-Strategie
def apply_bollinger_bands(df):
    df['SMA'] = df['close'].rolling(window=20).mean()
    df['STD'] = df['close'].rolling(window=20).std()
    df['Upper'] = df['SMA'] + 2 * df['STD']
    df['Lower'] = df['SMA'] - 2 * df['STD']

    last_price = df['close'].iloc[-1]
    lower_band = df['Lower'].iloc[-1]
    upper_band = df['Upper'].iloc[-1]

    if last_price < lower_band:
        return "buy"
    elif last_price > upper_band:
        return "sell"
    else:
        return "hold"

# 📦 Order platzieren
def place_order(symbol, action):
    if action not in ["buy", "sell"]:
        return

    trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

    order = MarketOrderRequest(
        symbol=symbol,
        qty=1,
        side=OrderSide.BUY if action == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )

    try:
        result = trading_client.submit_order(order)
        st.success(f"Order gesendet: {action.upper()} {symbol}")
        st.json(result.model_dump())
    except Exception as e:
        st.error(f"Orderfehler: {e}")

# 📊 Daten abrufen
def get_data(symbol, timeframe_str):
    tf = TIMEFRAME_MAP.get(timeframe_str)

    try:
        if "/" in symbol:  # Krypto
            client = CryptoHistoricalDataClient()
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start_date,
                end=end_date
            )
            bars = client.get_crypto_bars(request).df
        else:  # Aktien
            client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start_date,
                end=end_date
            )
            bars = client.get_stock_bars(request).df

        df = bars[bars['symbol'] == symbol].copy()
        df = df.reset_index()
        return df

    except Exception as e:
        st.error(f"Fehler beim Abrufen von {symbol}-Daten: {e}")
        return pd.DataFrame()

# 🎯 UI
st.set_page_config(page_title="Trading Bot mit Bollinger Bands", layout="centered")
st.title("📊 Trading Bot mit Bollinger Bands")

symbol = st.selectbox("Wähle ein Symbol", ["BTC/USD", "AAPL", "TSLA", "ETH/USD"])
timeframe = st.selectbox("Zeitintervall", list(TIMEFRAME_MAP.keys()))

if st.button("🔍 Analyse starten"):
    data = get_data(symbol, timeframe)

    if data.empty:
        st.warning("Keine Daten verfügbar.")
    else:
        action = apply_bollinger_bands(data)

        st.subheader(f"Aktuelle Empfehlung: **{action.upper()}**")

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(data['timestamp'], data['close'], label='Preis', color='blue')
        ax.plot(data['timestamp'], data['Upper'], label='Upper Band', linestyle='--', color='green')
        ax.plot(data['timestamp'], data['Lower'], label='Lower Band', linestyle='--', color='red')
        ax.set_title(f"{symbol} mit Bollinger Bands")
        ax.legend()
        st.pyplot(fig)

        if action in ["buy", "sell"]:
            place_order(symbol.split("/")[0] if "/" in symbol else symbol, action)
