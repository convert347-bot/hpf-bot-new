import ccxt
import pandas as pd
import time
import requests
from datetime import datetime

# ========== ТВОИ НАСТРОЙКИ ==========
BOT_TOKEN = "8514251161:AFAHwx9cETJBoHeAX-v_PBpPEXWJCRrC6s"
CHAT_ID = "ТВОЙ_CHAT_ID"          # Сюда вставим ID позже

TIMEFRAME = "30m"
DROP_PERCENT = 1.5
MIN_BARS_BETWEEN = 6

# Настройки для памяти 128 MB
BATCH_SIZE = 80
DELAY_BETWEEN_BATCHES = 30
MAIN_CYCLE_DELAY = 900
# ====================================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data)
    except:
        pass

def get_all_symbols():
    print("📡 Получаю список монет...")
    try:
        exchange = ccxt.bingx({'options': {'defaultType': 'future'}})
        markets = exchange.load_markets()
        symbols = [s for s in markets if s.endswith('/USDT')]
        usdt_futures = []
        for s in symbols:
            clean = s.split(':')[0]
            if '/USDT' in clean and 'USDT' in clean:
                usdt_futures.append(clean)
        return sorted(usdt_futures)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def find_point_c(symbol):
    try:
        exchange = ccxt.bingx({'options': {'defaultType': 'future'}})
        bars = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
        if len(bars) < 50:
            return None
        df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        highs = df['h'].values
        pivot_b_index = None
        for i in range(3, len(highs)-3):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                pivot_b_index = i
                break
        if pivot_b_index is None:
            return None
        b_price = highs[pivot_b_index]
        lows = df['l'].values
        pivot_c_index = None
        for i in range(pivot_b_index+1, len(lows)-3):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                pivot_c_index = i
                break
        if pivot_c_index is None:
            return None
        c_price = lows[pivot_c_index]
        bars_between = pivot_c_index - pivot_b_index
        if bars_between < MIN_BARS_BETWEEN:
            return None
        drop = (b_price - c_price) / b_price * 100
        if drop < DROP_PERCENT:
            return None
        return {
            'symbol': symbol,
            'b_price': round(b_price, 8),
            'c_price': round(c_price, 8),
            'drop': round(drop, 2),
            'bars': bars_between
        }
    except Exception as e:
        return None

def main():
    print("="*50)
    print("✅ Бот ЗАПУЩЕН. Ищу точки C...")
    send_telegram("🤖 Бот запущен! Сканирую BingX...")
    all_pairs = get_all_symbols()
    if not all_pairs:
        print("❌ Нет монет. Проверь интернет.")
        return
    print(f"✅ Загружено {len(all_pairs)} монет. Буду сканировать порциями по {BATCH_SIZE}.")
    sent = set()
    while True:
        total = len(all_pairs)
        start_time = time.time()
        print(f"\n🔁 [{datetime.now().strftime('%H:%M:%S')}] Новый цикл...")
        for i in range(0, total, BATCH_SIZE):
            batch = all_pairs[i:i+BATCH_SIZE]
            print(f"📦 Порция {i//BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1)//BATCH_SIZE}...")
            for sym in batch:
                print(f"  {sym}...", end=" ", flush=True)
                signal = find_point_c(sym)
                if signal:
                    key = f"{signal['symbol']}_{signal['b_price']}"
                    if key not in sent:
                        sent.add(key)
                        msg = (f"🔔 ТОЧКА C СФОРМИРОВАНА!\n\n"
f"{signal['symbol']}\n"
                               f"📈 Пик B: {signal['b_price']}\n"
                               f"📉 Точка C: {signal['c_price']}\n"
                               f"📊 Падение: {signal['drop']}%\n"
                               f"⏱️ Баров: {signal['bars']}\n\n"
                               f"👉 Смотри график 30m! Вход от C 🚀")
                        send_telegram(msg)
                        print("✅ СИГНАЛ!")
                else:
                    print("❌ нет")
                time.sleep(0.2)
            print(f"⏳ Пауза {DELAY_BETWEEN_BATCHES} сек...")
            time.sleep(DELAY_BETWEEN_BATCHES)
        elapsed = time.time() - start_time
        print(f"✅ Цикл за {elapsed:.0f} сек. Найдено сигналов: {len(sent)}.")
        print(f"😴 Сплю {MAIN_CYCLE_DELAY // 60} мин...")
        time.sleep(MAIN_CYCLE_DELAY)

if name == "main":
    try:
        main()
    except KeyboardInterrupt:
        print("🛑 Бот остановлен.")
        send_telegram("⚠️ Бот остановлен.")
    except Exception as e:
        print(f"🔥 Ошибка: {e}")
        send_telegram(f"⚠️ Ошибка: {e}")
