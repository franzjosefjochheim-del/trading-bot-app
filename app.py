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

# 🔑 API-Schlüssel (sicher in secrets.toml oder als ENV-Vars speichern)
ALPACA_API_KEY = "PKP5A2PXUW701XQZJIF5"
ALPACA_SECRET_KEY = "b7hVdITr9PeHBVXQLsfJbimbprrUdPVtAhOHLQl7"

# 🧠 Clients initialisieren
stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# 📈 Zeitintervall-Mapping
TIMEFRAME_MAP = {
    "1Min": TimeFrame.Minute,
    "5Min": TimeFrame(5, TimeFrame.Unit.Minute),
    "15Min": TimeFrame(15, TimeFrame.Unit.Minute),
    "1H": TimeFrame.Hour,
    "1D": TimeFrame.Day
}

# 🎯 Bollinger-Logik
def calculate_bollinger_bands(df, window=20, num_std=2):
    df['SMA'] = df['close'].rolling(window=window).mean()
    df['STD'] = df['close'].rolling(window=window).std()
    df['Upper'] = df['SMA'] + (num_std * df['STD'])
    df['Lower'] = df['SMA'] - (num_std * df['STD'])
    return df

# 📦 Handelslogik
def check_signals_and_trade(df, symbol):
    latest = df.iloc[-1]
    if latest['close'] > latest['Upper']:
        place_order(symbol, OrderSide.SELL)
        return "🔻 SELL Signal erkannt"
    elif latest['close'] < latest['Lower']:
        place_order(symbol, OrderSide.BUY)
        return "🟢 BUY Signal erkannt"
    return "⚪ Kein Signal"

# 🛒 Order auslösen
def place_order(symbol, side):
    try:
        order = MarketOrderRequest(
            symbol=symbol,
            qty=1,
            side=side,
            time_in_force=TimeInForce.GTC
        )
        trading_client.submit_order(order)
        st.success(f"{side.name} Order platziert für {symbol}")
    except Exception as e:
        st.error(f"Fehler bei Orderplatzierung: {e}")

# 📊 Daten holen
def get_data(symbol, start_date, end_date, timeframe):
    tf = TIMEFRAME_MAP.get(timeframe)
    if "USD" in symbol:
        request = CryptoBarsRequest(
            symbol=symbol,
            timeframe=tf,
            start=start_date,
            end=end_date
        )
        bars = crypto_client.get_crypto_bars(request).df
    else:
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start_date,
            end=end_date
        )
        bars = stock_client.get_stock_bars(request).df
    return bars

# 🎨 Plot
def plot_chart(df, symbol):
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['close'], label='Kurs')
    plt.plot(df.index, df['Upper'], label='Upper Band', linestyle='--')
    plt.plot(df.index, df['Lower'], label='Lower Band', linestyle='--')
    plt.title(f"{symbol} Bollinger Bands")
    plt.xlabel("Zeit")
    plt.ylabel("Preis")
    plt.legend()
    st.pyplot(plt)

# 🚀 Streamlit UI
st.set_page_config(page_title="Trading Bot mit Bollinger Bands", layout="centered")
st.title("📊 Trading Bot mit Bollinger Bands")

symbol = st.selectbox("Wähle ein Symbol", ["AAPL", "MSFT", "BTC/USD", "ETH/USD"])
selected_timeframe = st.selectbox("Zeitintervall", list(TIMEFRAME_MAP.keys()))
start_date = datetime.now() - timedelta(days=5)
end_date = datetime.now()

if st.button("🔍 Analyse starten"):
    try:
        bars = get_data(symbol, start_date, end_date, selected_timeframe)
        if bars.empty:
            st.warning("Keine Daten verfügbar.")
        else:
            if "symbol" in bars.columns:
                bars = bars[bars['symbol'] == symbol]
            bars = calculate_bollinger_bands(bars)
            signal = check_signals_and_trade(bars, symbol.replace("/", ""))
            st.info(signal)
            plot_chart(bars, symbol)
    except Exception as e:
        st.error(f"Fehler beim Abrufen von {symbol}-Daten: {e}")
