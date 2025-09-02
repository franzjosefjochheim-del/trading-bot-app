import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 🔐 API-Zugangsdaten
ALPACA_API_KEY = "PKP5A2PXUW701XQZJIF5"
ALPACA_SECRET_KEY = "b7hVdITr9PeHBVXQLsfJbimbprrUdPVtAhOHLQI7"

# 🔗 Clients initialisieren
stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# 📊 Streamlit UI
st.set_page_config(page_title="Trading Bot mit Bollinger Bands", layout="centered")
st.title("📊 Trading Bot mit Bollinger Bands")

symbol = st.selectbox("Wähle ein Symbol", ["AAPL", "BTC/USD"])
interval = st.selectbox("Zeitintervall", ["1Min", "5Min", "15Min", "1H", "1D"])
start_analysis = st.button("🔍 Analyse starten")

# 📦 Daten abrufen
def get_data(symbol, interval, start_date, end_date):
    try:
        if symbol == "BTC/USD":
            bars = crypto_client.get_crypto_bars(
                CryptoBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=interval,
                    start=start_date,
                    end=end_date
                )
            ).df
        else:
            bars = stock_client.get_stock_bars(
                StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=interval,
                    start=start_date,
                    end=end_date
                )
            ).df

        if symbol in bars.columns:
            bars = bars[bars['symbol'] == symbol]

        bars = bars.reset_index()
        bars['timestamp'] = pd.to_datetime(bars['timestamp'])
        return bars

    except Exception as e:
        st.error(f"Fehler beim Abrufen von {symbol}-Daten: {e}")
        return pd.DataFrame()

# 📈 Bollinger Bands berechnen
def calculate_bollinger_bands(df, window=20, num_std=2):
    df['MA'] = df['close'].rolling(window=window).mean()
    df['Upper'] = df['MA'] + (df['close'].rolling(window=window).std() * num_std)
    df['Lower'] = df['MA'] - (df['close'].rolling(window=window).std() * num_std)
    return df

# 🧠 Strategie (Buy/Sell Entscheidung)
def decide_and_trade(df, symbol):
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    action = None
    if latest['close'] > latest['Upper'] and previous['close'] <= previous['Upper']:
        action = "sell"
    elif latest['close'] < latest['Lower'] and previous['close'] >= previous['Lower']:
        action = "buy"

    if action:
        st.success(f"Automatische Entscheidung: {action.upper()}")
        try:
            if symbol == "BTC/USD":
                st.warning("⚠ Automatischer Handel für Krypto ist derzeit deaktiviert.")
            else:
                order = trading_client.submit_order(
                    order_data=MarketOrderRequest(
                        symbol=symbol,
                        qty=1,
                        side=OrderSide.BUY if action == "buy" else OrderSide.SELL,
                        time_in_force=TimeInForce.DAY
                    )
                )
                st.info(f"✅ Order ausgeführt: {action.upper()} {symbol}")
        except Exception as e:
            st.error(f"❌ Fehler bei Order-Platzierung: {e}")
    else:
        st.info("Keine Kauf-/Verkaufsentscheidung getroffen.")

# 📊 Plot-Funktion
def plot_bollinger(df):
    plt.figure(figsize=(12, 6))
    plt.plot(df['timestamp'], df['close'], label='Close Price')
    plt.plot(df['timestamp'], df['Upper'], label='Upper Band', linestyle='--')
    plt.plot(df['timestamp'], df['MA'], label='Moving Average', linestyle='-')
    plt.plot(df['timestamp'], df['Lower'], label='Lower Band', linestyle='--')
    plt.fill_between(df['timestamp'], df['Lower'], df['Upper'], alpha=0.1)
    plt.legend()
    plt.title('Bollinger Bands')
    st.pyplot(plt)

# 🏁 Analyse starten
if start_analysis:
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=5)

    df = get_data(symbol, interval, start_date, end_date)

    if not df.empty:
        df = calculate_bollinger_bands(df)
        plot_bollinger(df)
        decide_and_trade(df, symbol)
    else:
        st.warning("Keine Daten verfügbar.")
