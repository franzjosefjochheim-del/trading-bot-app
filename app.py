import streamlit as st
import pandas as pd
import numpy as np
import datetime
from ta.momentum import RSIIndicator
import matplotlib.pyplot as plt
from alpaca_trade_api.rest import REST
import os

# Alpaca API konfigurieren
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

api = REST(API_KEY, SECRET_KEY, base_url=BASE_URL)

# App-Titel
st.set_page_config(page_title="Trading-Bot (MA + RSI)")
st.title("📈 Automatisierter Trading-Bot (MA + RSI)")

# Eingabeparameter
symbol = st.text_input("🔍 Tickersymbol eingeben", value="AAPL")
timeframe = st.selectbox("🕒 Zeitrahmen", options=["1Min", "5Min", "15Min", "1D"], index=3)
ma_short = st.slider("📉 Kurzfristiger MA", 5, 50, 10)
ma_long = st.slider("📈 Langfristiger MA", 20, 200, 50)
rsi_period = st.slider("📊 RSI-Periode", 5, 30, 14)
quantity = st.number_input("🧾 Order-Menge", min_value=1, step=1, value=1)

# Wenn auf Button geklickt
if st.button("🔍 Analyse starten"):
    try:
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=180)

        df = api.get_bars(
            symbol,
            timeframe,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            feed="iex"  # <- kostenloser Feed für Paper Trading
        ).df

        df = df[df['symbol'] == symbol] if 'symbol' in df.columns else df

        if df.empty:
            st.error("Keine Daten empfangen. Bitte Symbol/Zeitfenster prüfen.")
        else:
            # Technische Indikatoren berechnen
            df['MA_Short'] = df['close'].rolling(window=ma_short).mean()
            df['MA_Long'] = df['close'].rolling(window=ma_long).mean()
            df['RSI'] = RSIIndicator(close=df['close'], window=rsi_period).rsi()

            # Aktuelle Werte extrahieren
            last_close = df['close'].iloc[-1]
            last_ma_short = df['MA_Short'].iloc[-1]
            last_ma_long = df['MA_Long'].iloc[-1]
            last_rsi = df['RSI'].iloc[-1]

            # Handelslogik
            signal = ""
            if last_ma_short > last_ma_long and last_rsi < 70:
                signal = "BUY"
            elif last_ma_short < last_ma_long and last_rsi > 30:
                signal = "SELL"
            else:
                signal = "HOLD"

            # Visualisierung MA
            st.line_chart(df[['MA_Short', 'MA_Long', 'close']])

            # Visualisierung RSI
            st.line_chart(df['RSI'])

            # Handelssignal anzeigen
            st.markdown(f"### Aktueller Handelssignal für {symbol.upper()}: 📈 **{signal}**")

            # Order ausführen bei BUY/SELL
            if signal in ["BUY", "SELL"]:
                try:
                    side = "buy" if signal == "BUY" else "sell"
                    order = api.submit_order(
                        symbol=symbol,
                        qty=quantity,
                        side=side,
                        type='market',
                        time_in_force='gtc'
                    )
                    st.success(f"✅ Order ausgeführt: {side.upper()} {quantity} {symbol}")
                except Exception as e:
                    st.error(f"❌ Fehler beim Senden der Order: {e}")

    except Exception as e:
        st.error(f"🚨 Fehler bei der Analyse oder API-Abfrage: {e}")
