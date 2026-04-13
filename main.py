import requests
import pandas as pd
import time
from datetime import datetime

TELEGRAM_TOKEN = "8709725090:AAEjO_4CdeNhAKKHXFR-j71jeoJqcHti9Cw"
CHAT_ID = "500524644"

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram error:", e)

# Sample F&O universe grouped by sector
SECTORS = {
    "Auto": ["TATAMOTORS", "MARUTI", "M&M", "BHARATFORG"],
    "Bank": ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO"],
    "Energy": ["RELIANCE", "BPCL", "IOC", "ONGC"],
    "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "LUPIN"],
    "Metal": ["TATASTEEL", "JSWSTEEL", "HINDALCO"],
}

# Full updated F&O universe (user-provided)
FNO_STOCKS = [
    # BANKING / FINANCE
    "HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK",
    "INDUSINDBK","BANKBARODA","PNB","IDFCFIRSTB","FEDERALBNK",
    "AUBANK","BANDHANBNK",

    # IT
    "TCS","INFY","WIPRO","HCLTECH","TECHM","LTIM","PERSISTENT","COFORGE",

    # AUTO
    "TATAMOTORS","MARUTI","M&M","BAJAJ-AUTO","EICHERMOT","ASHOKLEY",

    # PHARMA
    "SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","LUPIN","ALKEM",

    # METAL
    "TATASTEEL","JSWSTEEL","HINDALCO","VEDL","SAIL","NMDC",

    # FMCG
    "HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO",

    # ENERGY / OIL & GAS
    "RELIANCE","ONGC","BPCL","IOC","GAIL","ADANIENT","ADANIPORTS",

    # INFRA / CAPITAL GOODS
    "LT","SIEMENS","ABB","BHEL","BEL",

    # REALTY
    "DLF","GODREJPROP","OBEROIRLTY",

    # CEMENT
    "ULTRACEMCO","SHREECEM","ACC","AMBUJACEM",

    # TELECOM / MEDIA
    "BHARTIARTL","ZEEL","SUNTV",

    # NEW AGE / RECENT ADDITIONS
    "ZOMATO","PAYTM","JIOFIN","NYKAA","DMART",

    # RECENTLY ADDED (2026)
    "ADANIPOWER","COCHINSHIP","FORCEMOT","GODFRYPHLP",
    "HYUNDAI","MOTILALOFS","NAM-INDIA","VISHAL",
]

# Use the full list for advance/decline calculations
FNO_UNIVERSE = FNO_STOCKS

# Choose a sector here or set to None to auto-pick based on sector weakness/strength
SELECTED_SECTOR = "Auto"  # e.g. "Bank", "Auto", or "Auto" to auto-select

def get_top_n_losers(symbols, n=3):
    losers = []
    for stock in symbols:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock}.NS?interval=5m&range=1d"
            resp = requests.get(url, timeout=10)
            data = resp.json()

            result = data.get('chart', {}).get('result')
            if not result:
                continue

            close_prices = result[0].get('indicators', {}).get('quote', [{}])[0].get('close', [])
            if not close_prices or close_prices[0] is None:
                continue

            prev_close = close_prices[0]
            current_price = close_prices[-1]
            change_pct = ((current_price - prev_close) / prev_close) * 100
            losers.append((stock, change_pct))
        except Exception as e:
            print("Error fetching", stock, e)

    if not losers:
        return symbols[:n]

    losers.sort(key=lambda x: x[1])
    return [x[0] for x in losers[:n]]

def get_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=5m&range=1d"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        result = data.get('chart', {}).get('result')
        if not result:
            return pd.DataFrame()

        quote = result[0].get('indicators', {}).get('quote', [{}])[0]
        df = pd.DataFrame(quote)
        df['time'] = pd.to_datetime(result[0].get('timestamp', []), unit='s')
        return df

    except Exception as e:
        print("Data error:", symbol, e)
        return pd.DataFrame()

day_low_vol = {}
top_stocks = []
alerted = set()
last_reset_date = None

def compute_advance_decline(universe):
    adv = 0
    dec = 0
    for s in universe:
        df = get_data(s)
        if df.empty or len(df) < 1:
            continue
        last = df.iloc[-1]
        if last['close'] > last['open']:
            adv += 1
        elif last['close'] < last['open']:
            dec += 1
    return adv, dec

def pick_sector(universe_sectors):
    # pick sector with largest average decline (weakest)
    scores = []
    for sector, symbols in universe_sectors.items():
        vals = []
        for s in symbols:
            try:
                df = get_data(s)
                if df.empty:
                    continue
                first = df['close'].iloc[0]
                last = df['close'].iloc[-1]
                vals.append(((last - first) / first) * 100)
            except Exception:
                continue
        if vals:
            scores.append((sector, sum(vals) / len(vals)))
    if not scores:
        return list(universe_sectors.keys())[0]
    # choose sector with smallest average return (weakest)
    scores.sort(key=lambda x: x[1])
    return scores[0][0]

while True:
    now = datetime.now()

    # Weekend skip
    if now.weekday() >= 5:
        time.sleep(600)
        continue

    # Market hours (9:15–15:30)
    if now.hour < 9 or now.hour > 15:
        time.sleep(300)
        continue

    # Daily reset
    today = now.date()
    if last_reset_date != today:
        day_low_vol.clear()
        alerted.clear()
        top_stocks = []
        last_reset_date = today

    # 9:25 selection
    if now.hour == 9 and now.minute == 25 and not top_stocks:
        # compute market direction (advance/decline)
        adv, dec = compute_advance_decline(FNO_UNIVERSE)
        market_dir = "Bullish" if adv > dec else "Bearish"

        # sector selection
        sector_to_use = SELECTED_SECTOR
        if SELECTED_SECTOR == "Auto":
            sector_to_use = pick_sector(SECTORS)

        symbols = SECTORS.get(sector_to_use, FNO_UNIVERSE)
        top_stocks = get_top_n_losers(symbols, n=3)
        print("Market:", market_dir, "Sector:", sector_to_use, "Top:", top_stocks)
        send_alert(f"📉 Market: {market_dir}\nSector: {sector_to_use}\nTop: {top_stocks}")

    if not top_stocks:
        time.sleep(60)
        continue

    for stock in top_stocks:
        df = get_data(stock)

        if df.empty:
            continue

        last = df.iloc[-1]
        if stock not in day_low_vol:
            day_low_vol[stock] = last.get('volume', 0)

        if last.get('volume', 0) < day_low_vol[stock]:
            day_low_vol[stock] = last.get('volume', 0)

        is_green = last['close'] > last['open']
        is_red = last['close'] < last['open']
        is_lowest = last.get('volume', 0) == day_low_vol[stock]

        # determine market direction from the alert message we sent (quick local recompute)
        # simpler: recompute A/D for safety
        adv, dec = compute_advance_decline(FNO_UNIVERSE)
        market_bull = adv > dec

        # Bullish market -> look for RED low-volume pullback to BUY
        if market_bull and is_red and is_lowest:
            key = (stock, str(last['time']))
            if key not in alerted:
                msg = f"🔥 BUY Setup: {stock}\nPrice: {last['close']}\nLow: {last['low']}\nHigh: {last['high']}"
                print(msg)
                send_alert(msg)
                alerted.add(key)

        # Bearish market -> look for GREEN low-volume pullback to SELL
        if (not market_bull) and is_green and is_lowest:
            key = (stock, str(last['time']))
            if key not in alerted:
                msg = f"🔥 SELL Setup: {stock}\nPrice: {last['close']}\nLow: {last['low']}\nHigh: {last['high']}"
                print(msg)
                send_alert(msg)
                alerted.add(key)

    time.sleep(10)