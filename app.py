import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
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

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    st.error("Bitte setze deine ALPACA_API_KEY und ALPACA_SECRET_KEY Umgebungsvariablen in Render.")
    st.stop()

# === Clients ===
stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient()
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# === Zeitintervall-Auswahl ===
TIMEFRAME_MAP = {
    "1Min": TimeFrame.Minute,
    "5Min": TimeFrame.Minute5,
    "15Min": TimeFrame.Minute15,
    "1H": TimeFrame.Hour,
    "1D": TimeFrame.Day
}

# === Streamlit UI ===
st.title("📈 Trading-Bot mit Bollinger-Strategie")
symbol = st.selectbox("Wähle Symbol", ["AAPL", "MSFT", "GOOG", "BTC/USD"])
interval = st.selectbox("Wähle Zeitintervall", list(TIMEFRAME_MAP.keys()))
start_date = st.date_input("Startdatum", datetime.date.today() - datetime.timedelta(days=30))
end_date = st.date_input("Enddatum", datetime.date.today())

# === Daten abrufen ===
def get_data(symbol, start, end, timeframe):
    if symbol == "BTC/USD":
        request = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            start=start,
            end=end,
            timeframe=timeframe
        )
        bars = crypto_client.get_crypto_bars(request).df
        bars = bars[bars['symbol'] == symbol]
    else:
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            start=start,
            end=end,
            timeframe=timeframe
        )
        bars = stock_client.get_stock_bars(request).df
        bars = bars[bars['symbol'] == symbol]
    return bars.copy()

# === Bollinger-Strategie ===
def apply_bollinger_strategy(df):
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['Upper'] = df['MA20'] + 2 * df['close'].rolling(window=20).std()
    df['Lower'] = df['MA20'] - 2 * df['close'].rolling(window=20).std()
    df['Signal'] = np.where(df['close'] < df['Lower'], 'BUY',
                     np.where(df['close'] > df['Upper'], 'SELL', 'HOLD'))
    return df

# === Order platzieren ===
def place_order(symbol, side):
    try:
        order_data = MarketOrderRequest(
            symbol=symbol.replace("/", ""),  # BTC/USD → BTCUSD
            qty=1,
            side=OrderSide.BUY if side == 'BUY' else OrderSide.SELL,
            time_in_force=TimeInForce.GTC
        )
        trading_client.submit_order(order_data)
        st.success(f"{side} Order für {symbol} platziert!")
    except Exception as e:
        st.error(f"Fehler bei Orderplatzierung: {e}")

# === Hauptverarbeitung ===
if st.button("Starte Strategie"):
    with st.spinner("Hole Daten..."):
        data = get_data(symbol, start_date, end_date, TIMEFRAME_MAP[interval])
    
    if data.empty:
        st.warning("Keine Daten gefunden.")
    else:
        data = apply_bollinger_strategy(data)
        
        st.subheader("📊 Bollinger Chart")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(data.index, data['close'], label='Close')
        ax.plot(data.index, data['MA20'], label='MA20')
        ax.plot(data.index, data['Upper'], label='Upper Band')
        ax.plot(data.index, data['Lower'], label='Lower Band')
        ax.set_title(f"{symbol} Bollinger Bands Strategie")
        ax.legend()
        st.pyplot(fig)

        latest_signal = data['Signal'].iloc[-1]
        st.subheader(f"Aktuelles Signal: {latest_signal}")

        if latest_signal in ['BUY', 'SELL']:
            if st.button(f"📥 {latest_signal} Order ausführen"):
                place_order(symbol, latest_signal)
