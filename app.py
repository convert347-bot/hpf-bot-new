import ccxt
import pandas as pd
import time
import requests
from datetime import datetime

BOT_TOKEN = "8514251161:AAFAHwx9cETJBoHeAX-v_PBpPEXWJCRrC6s"
CHAT_ID = "5916071793"
TIMEFRAME = "30m"
MIN_BARS = 6
DROP = 2.0

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, data=data)
    except:
        pass

def get_symbols():
    ex = ccxt.bingx({'options': {'defaultType': 'future'}})
    markets = ex.load_markets()
    pairs = []
    for s in markets:
        if s.endswith('/USDT'):
            clean = s.split(':')[0]
            if '/USDT' in clean and 'USDT' in clean:
                pairs.append(clean)
    return sorted(pairs)

def find_c(symbol):
    try:
        ex = ccxt.bingx({'options': {'defaultType': 'future'}})
        bars = ex.fetch_ohlcv(symbol, TIMEFRAME, limit=150)
        if len(bars) < 50:
            return None
        df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
        highs = df['h'].values
        lows = df['l'].values

        b_idx = None
        for i in range(3, len(highs)-3):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                b_idx = i
                break
        if b_idx is None:
            return None
        b_price = highs[b_idx]

        c_idx = None
        for i in range(b_idx+1, len(lows)-3):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                c_idx = i
                break
        if c_idx is None or (c_idx - b_idx) < MIN_BARS:
            return None
        c_price = lows[c_idx]

        drop = (b_price - c_price) / b_price * 100
        if drop < DROP:
            return None

        return {
            'symbol': symbol,
            'b': round(b_price, 8),
            'c': round(c_price, 8),
            'drop': round(drop, 1),
            'bars': c_idx - b_idx
        }
    except:
        return None

def main():
    print("✅ Бот запущен. Ищу точки C...")
    send_telegram("✅ Бот запущен. Ищу точки C...")
    all_pairs = get_symbols()
    print(f"Загружено монет: {len(all_pairs)}")
    sent = set()
    while True:
        for sym in all_pairs:
            signal = find_c(sym)
            if signal:
                key = f"{signal['symbol']}_{signal['b']}"
                if key not in sent:
                    sent.add(key)
                    msg = (f"🔔 ТОЧКА C СФОРМИРОВАНА!\n\n"
                           f"{signal['symbol']}\n"
                           f"📈 Пик B: {signal['b']}\n"
                           f"📉 Точка C: {signal['c']}\n"
                           f"📊 Падение: {signal['drop']}%\n"
                           f"⏱️ Баров: {signal['bars']}\n\n"
                           f"👉 Смотри график 30m! Вход от C")
                    send_telegram(msg)
                    print(f"✅ СИГНАЛ на {signal['symbol']}")
            else:
                print(f"❌ {sym}")
            time.sleep(0.3)
        print("😴 Цикл закончен, сплю 15 минут...")
        time.sleep(900)

if __name__ == "__main__":
    main()
