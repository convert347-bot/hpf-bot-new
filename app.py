import ccxt
import pandas as pd
import time
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8514251161:AAHouiVoNirkwkgG64js147HVgAoQFalvw"
CHAT_ID = "5916071793"

TIMEFRAME = "30m"
LIMIT = 30
BATCH_SIZE = 15
DELAY_BETWEEN_BATCHES = 60
MAIN_CYCLE_DELAY = 1200

FIB_LEVELS = [0.382, 0.5, 0.618, 0.707, 0.786, 0.886]
FIB_TOLERANCE = 0.1

BLOCKLIST = [
    'OIL', 'GAS', 'GOLD', 'SILVER', 'COPPER', 'URAN', 'PLAT', 'PALL',
    'NASDAQ', 'SPX', 'RUSSELL', 'DOW', 'FTSE', 'DAX', 'NIKKEI', 'HSI',
    'META', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'GOOGL', 'COIN',
    'MSTR', 'JPM', 'BABA', 'NFLX', 'AMD', 'INTL', 'C', 'WMT', 'JNJ', 'V', 'PG'
]
# ================================

# --- Микро-веб-сервер для health check ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8000), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_health_server, daemon=True).start()
# -----------------------------------------

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, data=data)
    except:
        pass

def get_crypto_symbols():
    ex = ccxt.bingx({'options': {'defaultType': 'future'}})
    markets = ex.load_markets()
    crypto_pairs = []
    for s in markets:
        if s.endswith('/USDT'):
            clean = s.split(':')[0]
            is_blocked = False
            for kw in BLOCKLIST:
                if kw in clean.upper():
                    is_blocked = True
                    break
            if not is_blocked:
                crypto_pairs.append(clean)
    return sorted(crypto_pairs)

def is_fib_ratio(ratio):
    for level in FIB_LEVELS:
        if abs(ratio - level) <= FIB_TOLERANCE:
            return True
    return False

def find_c(symbol):
    try:
        ex = ccxt.bingx({'options': {'defaultType': 'future'}})
        bars = ex.fetch_ohlcv(symbol, TIMEFRAME, limit=LIMIT)
        if len(bars) < 30:
            return None
        df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
        highs = df['h'].values
        lows = df['l'].values

        b_idx = None
        for i in range(2, len(highs)-2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                b_idx = i
                break
        if b_idx is None:
            return None
        b = highs[b_idx]

        c_idx = None
        for i in range(b_idx+1, len(lows)-2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                c_idx = i
                break
        if c_idx is None:
            return None
        c = lows[c_idx]

        a_idx = None
        for i in range(b_idx-1, -1, -1):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                a_idx = i
                break
        if a_idx is None:
            return None
        a = lows[a_idx]

        ab = b - a
        if ab <= 0:
            return None
        bc = b - c
        ratio = bc / ab
        if not is_fib_ratio(ratio):
            return None

        drop = (b - c) / b * 100
        if drop < 2.0:
            return None

        return {
            'symbol': symbol,
            'b': round(b, 6),
            'c': round(c, 6),
            'drop': round(drop, 1),
            'ratio': round(ratio, 3)
        }
    except:
        return None

def main():
    print("✅ Бот запущен (крипто-фьючерсы + Фибоначчи + health check). Ищу точки C...")
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
                        msg = (f"🔔 ТОЧКА C (FIB)!\n{sig['symbol']}\n"
                               f"B: {sig['b']}\nC: {sig['c']}\n"
                               f"Падение: {sig['drop']}%\nBC/AB = {sig['ratio']}\n"
                               f"👉 Вход от C, стоп за A")
                        send_telegram(msg)
                        print(f"✅ СИГНАЛ на {sig['symbol']}")
                else:
                    print(f"❌ {sym}")
                time.sleep(0.6)
            print(f"⏳ Пауза {DELAY_BETWEEN_BATCHES} сек между порциями...")
            time.sleep(DELAY_BETWEEN_BATCHES)
        print(f"😴 Цикл закончен, сплю {MAIN_CYCLE_DELAY // 60} минут...")
        time.sleep(MAIN_CYCLE_DELAY)

if __name__ == "__main__":
    main()
