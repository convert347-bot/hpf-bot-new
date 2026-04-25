import ccxt
import pandas as pd
import time
import requests
from datetime import datetime

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8514251161:AAHouiVoNirkwkgG64js147HVgAoQFalvw"
CHAT_ID = "5916071793"

TIMEFRAME = "30m"
LIMIT = 50                      # смотрим последние 50 свечей (25 часов)
BATCH_SIZE = 40                 # обрабатываем по 40 монет за раз
DELAY_BETWEEN_BATCHES = 30
MAIN_CYCLE_DELAY = 900          # 15 минут между циклами

# Только криптовалюты (исключаем нефть, газ, индексы, акции, золото)
BLOCKLIST = [
    'OIL', 'GAS', 'GOLD', 'SILVER', 'COPPER', 'URAN', 'PLAT', 'PALL',
    'NASDAQ', 'SPX', 'RUSSELL', 'DOW', 'FTSE', 'DAX', 'NIKKEI', 'HSI',
    'META', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'COIN',
    'MSTR', 'JPM', 'BABA', 'NFLX', 'AMD', 'INTL', 'C', 'WMT', 'JNJ', 'V', 'PG'
]
# ================================

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, data=data)
    except:
        pass

def get_crypto_symbols():
    """Возвращает только криптовалютные фьючерсные пары (игнорирует TradFi)"""
    ex = ccxt.bingx({'options': {'defaultType': 'future'}})
    markets = ex.load_markets()
    crypto_pairs = []
    for s in markets:
        if s.endswith('/USDT'):
            clean = s.split(':')[0]
            # Проверяем, есть ли в названии запрещённое слово
            is_blocked = False
            for kw in BLOCKLIST:
                if kw in clean.upper():
                    is_blocked = True
                    break
            if not is_blocked:
                crypto_pairs.append(clean)
    return sorted(crypto_pairs)

def find_c(symbol):
    try:
        ex = ccxt.bingx({'options': {'defaultType': 'future'}})
        bars = ex.fetch_ohlcv(symbol, TIMEFRAME, limit=LIMIT)
        if len(bars) < 50:
            return None
        df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
        highs = df['h'].values
        lows = df['l'].values

        # Поиск пика B
        b_idx = None
        for i in range(3, len(highs)-3):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                b_idx = i
                break
        if b_idx is None:
            return None
        b = highs[b_idx]

        # Поиск впадины C
        c_idx = None
        for i in range(b_idx+1, len(lows)-3):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                c_idx = i
                break
        if c_idx is None:
            return None
        c = lows[c_idx]
        drop = (b - c) / b * 100 if b > 0 else 0
        if drop < 2.0:
            return None

        return {
            'symbol': symbol,
            'b': round(b, 6),
            'c': round(c, 6),
            'drop': round(drop, 1),
            'bars': c_idx - b_idx
        }
    except:
        return None

def main():
    print("✅ Бот запущен. Ищу точки C (только крипто-фьючерсы)...")
    send_telegram("✅ Бот запущен. Ищу точки C...")
    all_pairs = get_crypto_symbols()
    print(f"Загружено крипто-пар: {len(all_pairs)}")
    sent = set()
    while True:
        for i in range(0, len(all_pairs), BATCH_SIZE):
            batch = all_pairs[i:i+BATCH_SIZE]
            print(f"📦 Обрабатываю порцию {i//BATCH_SIZE + 1}/{(len(all_pairs) + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} монет)")
            for sym in batch:
                sig = find_c(sym)
                if sig:
                    key = f"{sig['symbol']}_{sig['b']}"
                    if key not in sent:
                        sent.add(key)
                        msg = (f"🔔 ТОЧКА C!\n{sig['symbol']}\n"
                               f"B: {sig['b']}\nC: {sig['c']}\n"
                               f"Падение: {sig['drop']}%\nБаров: {sig['bars']}\n\n"
                               f"👉 Вход от C, стоп за A")
                        send_telegram(msg)
                        print(f"✅ СИГНАЛ на {sig['symbol']}")
                else:
                    print(f"❌ {sym}")
                time.sleep(0.2)
            print(f"⏳ Пауза {DELAY_BETWEEN_BATCHES} сек между порциями...")
            time.sleep(DELAY_BETWEEN_BATCHES)
        print("😴 Цикл закончен, сплю 15 минут...")
        time.sleep(MAIN_CYCLE_DELAY)

if __name__ == "__main__":
    main()
