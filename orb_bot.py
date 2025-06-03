import os
import requests
import pandas as pd
from ta.trend import EMAIndicator
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = 'https://api.dhan.co'

symbol = 'RELIANCE'
exchange = 'NSE_EQ'
risk_amount = 100

headers = {
    'access-token': ACCESS_TOKEN,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

def fetch_historical_data():
    url = f"{BASE_URL}/market/v1/instruments/historical/daily"
    params = {
        "symbol": symbol,
        "exchange": exchange,
        "securityId": "",
        "interval": "5minute",
        "from_date": datetime.today().strftime('%Y-%m-%d'),
        "to_date": datetime.today().strftime('%Y-%m-%d')
    }
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    df = pd.DataFrame(data['data'])
    df['timestamp'] = pd.to_datetime(df['startTime'])
    df.set_index('timestamp', inplace=True)
    df = df.astype(float)
    return df

def calculate_ema(df):
    df['ema20'] = EMAIndicator(df['close'], window=20).ema_indicator()
    return df

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, data=payload)
        if res.status_code != 200:
            print("Telegram error:", res.text)
    except Exception as e:
        print("Telegram failed:", e)

def place_order(side, qty):
    print(f"Order to {side} {qty} units sent.")
    # Replace with Dhan's actual order placement API if needed

def run_strategy():
    df = fetch_historical_data()
    if df.empty:
        print("No data")
        return

    df.index = pd.to_datetime(df.index)
    df = calculate_ema(df)

    try:
        orb_candle = df.between_time("09:15", "09:20").iloc[0]
    except IndexError:
        print("ORB candle not found yet")
        return

    orb_high = orb_candle['high']
    orb_low = orb_candle['low']
    orb_range = orb_high - orb_low

    df_after_orb = df[df.index > orb_candle.name]
    if df_after_orb.empty:
        print("Waiting for post-ORB candles")
        return

    latest = df_after_orb.iloc[-1]

    if latest['close'] > orb_high and latest['close'] > latest['ema20']:
        qty = int(risk_amount / orb_range)
        msg = f"📢 *{symbol}* ORB Breakout Alert\n\n💹 *Side:* BUY\n💰 *Price:* {latest['close']:.2f}\n📏 *Range:* {orb_low:.2f} - {orb_high:.2f}\n🕒 *Time:* {latest.name.strftime('%H:%M')}"
        send_telegram_alert(msg)
        place_order("BUY", qty)

    elif latest['close'] < orb_low and latest['close'] < latest['ema20']:
        qty = int(risk_amount / orb_range)
        msg = f"📢 *{symbol}* ORB Breakdown Alert\n\n💹 *Side:* SELL\n💰 *Price:* {latest['close']:.2f}\n📏 *Range:* {orb_low:.2f} - {orb_high:.2f}\n🕒 *Time:* {latest.name.strftime('%H:%M')}"
        send_telegram_alert(msg)
        place_order("SELL", qty)
    else:
        print("No breakout yet.")
        send_telegram_alert(f"📊 *{symbol}* Update: No breakout yet as of {latest.name.strftime('%H:%M')}.")

if __name__ == "__main__":
    run_strategy()
