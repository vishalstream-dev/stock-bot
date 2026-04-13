
    import requests
import pandas as pd
import time
from datetime import datetime

# ================= TELEGRAM =================
TELEGRAM_TOKEN = "8709725090:AAEjO_4CdeNhAKKHXFR-j71jeoJqcHti9Cw"
CHAT_ID = "500524644"

def send_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

# ================= NIFTY 50 =================
nifty50 = [
"RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","LT","SBIN","AXISBANK",
"KOTAKBANK","HINDUNILVR","ITC","BHARTIARTL","ASIANPAINT","MARUTI",
"HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO","NESTLEIND","POWERGRID",
"NTPC","BAJFINANCE","BAJAJFINSV","WIPRO","ONGC","JSWSTEEL","TATASTEEL",
"INDUSINDBK","TECHM","ADANIENT","ADANIPORTS","GRASIM","CIPLA","DRREDDY",
"COALINDIA","EICHERMOT","HEROMOTOCO","BRITANNIA","SHREECEM","HDFCLIFE",
"SBILIFE","DIVISLAB","APOLLOHOSP","LTIM","BPCL","IOC","UPL","BAJAJ-AUTO"
]

# ================= SECTOR MAP =================
sector_map = {
"AUTO": ["TATAMOTORS","MARUTI","M&M","BAJAJ-AUTO","EICHERMOT","ASHOKLEY"],
"BANK": ["HDFCBANK","ICICIBANK","SBIN","AXISBANK","KOTAKBANK"],
"IT": ["TCS","INFY","WIPRO","HCLTECH","TECHM"],
}

selected_sector = "AUTO"
market_bullish = True

# ================= DATA FETCH =================
def get_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=5m&range=1d"
        data = requests.get(url).json()

        candles = data['chart']['result'][0]['indicators']['quote'][0]
        df = pd.DataFrame(candles)
        df['time'] = pd.to_datetime(data['chart']['result'][0]['timestamp'], unit='s')
        return df
    except:
        return pd.DataFrame()

# ================= TOP 6 LOSERS =================
def get_top_6_losers():
    losers = []
    for stock in nifty50:
        df = get_data(stock)
        if df.empty:
            continue

        try:
            prev = df['close'].iloc[0]
            curr = df['close'].iloc[-1]
            change = ((curr - prev) / prev) * 100
            losers.append((stock, change))
        except:
            continue

    losers.sort(key=lambda x: x[1])
    return [x[0] for x in losers[:6]]

# ================= GLOBAL =================
day_low_vol = {}
alerted = set()
top_stocks = []
last_reset = None

# ================= MAIN LOOP =================
while True:
    now = datetime.now()

    # WEEKEND SKIP
    if now.weekday() >= 5:
        time.sleep(600)
        continue

    # MARKET HOURS (9:15–15:30)
    if now.hour < 9 or now.hour > 15:
        time.sleep(300)
        continue

    # DAILY RESET
    if last_reset != now.date():
        day_low_vol.clear()
        alerted.clear()
        top_stocks = []
        last_reset = now.date()
        print("🔄 Reset Done")

    # ================= 9:25 TOP 6 =================
    if now.hour == 9 and now.minute == 25 and not top_stocks:
        top_stocks = get_top_6_losers()
        send_alert(f"📊 Top 6 Losers:\n{top_stocks}")

    # WAIT BEFORE 9:25
    if not top_stocks:
        time.sleep(60)
        continue

    # ================= STOCK ALERT SYSTEM =================
    for stock in top_stocks:
        df = get_data(stock)
        if df.empty:
            continue

        last = df.iloc[-1]

        if stock not in day_low_vol:
            day_low_vol[stock] = last['volume']

        if last['volume'] < day_low_vol[stock]:
            day_low_vol[stock] = last['volume']

        is_green = last['close'] > last['open']
        is_lowest = last['volume'] == day_low_vol[stock]

        key = ("stock", stock, last['time'])

        if is_green and is_lowest and key not in alerted:
            msg = f"""⚡ STOCK ALERT

Stock: {stock}

Signal:
Green Candle + Lowest Volume

Entry: High break
SL: Low break"""
            send_alert(msg)
            alerted.add(key)

    # ================= F&O ALERT SYSTEM =================
    for stock in sector_map[selected_sector]:
        df = get_data(stock)
        if df.empty:
            continue

        last = df.iloc[-1]

        if stock not in day_low_vol:
            day_low_vol[stock] = last['volume']

        if last['volume'] < day_low_vol[stock]:
            day_low_vol[stock] = last['volume']

        is_green = last['close'] > last['open']
        is_red = last['close'] < last['open']
        is_lowest = last['volume'] == day_low_vol[stock]

        key = ("fo", stock, last['time'])

        if market_bullish and is_red and is_lowest and key not in alerted:
            msg = f"""🚀 F&O ALERT

Sector: {selected_sector}
Stock: {stock}

Signal:
Pullback (Low Volume Candle)

Action:
BUY"""
            send_alert(msg)
            alerted.add(key)

        if not market_bullish and is_green and is_lowest and key not in alerted:
            msg = f"""🚀 F&O ALERT

Sector: {selected_sector}
Stock: {stock}

Signal:
Pullback (Low Volume Candle)

Action:
SELL"""
            send_alert(msg)
            alerted.add(key)

    # ================= LOOP DELAY =================
    time.sleep(300)