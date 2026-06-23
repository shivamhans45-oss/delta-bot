import os
import hmac
import hashlib
import time
import requests
import threading
from flask import Flask, jsonify

app = Flask(__name__)

# API Configuration securely loaded from Render environment variables
API_KEY = os.getenv("DELTA_API_KEY")
API_SECRET = os.getenv("DELTA_API_SECRET")
BASE_URL = "https://delta.exchange"
PRODUCT_ID = 27  # BTCUSD Perpetual Contract ID on Delta Exchange
TRADE_SIZE = int(os.getenv("TRADE_SIZE", 0.1))

def generate_signature(method, path, expiry, payload=""):
    message = method + str(expiry) + path + payload
    return hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

def get_market_data(resolution):
    """Fetches candle data from Delta Exchange to calculate trend directions"""
    try:
        end_time = int(time.time())
        start_time = end_time - (3600 * 24) # Fetch past 24 hours
        url = f"{BASE_URL}/v2/history/candles?product_id={PRODUCT_ID}&resolution={resolution}&start={start_time}&end={end_time}"
        response = requests.get(url).json()
        return response.get('result', [])
    except Exception as e:
        print(f"Error fetching {resolution} data: {e}")
        return []

def execute_bracket_order(side, tp_price, sl_price):
    path = "/v2/orders"
    expiry = int(time.time()) + 60
    payload_dict = {
        "product_id": PRODUCT_ID,
        "size": TRADE_SIZE,
        "side": side.lower(),
        "order_type": "market",
        "bracket_order": {
            "profit_trigger_price": str(round(tp_price, 1)),
            "loss_trigger_price": str(round(sl_price, 1))
        }
    }
    payload_str = str(payload_dict).replace("'", '"') 
    headers = {
        "api-key": API_KEY,
        "api-signature": generate_signature("POST", path, expiry, payload_str),
        "api-expires": str(expiry),
        "Content-Type": "application/json"
    }
    res = requests.post(BASE_URL + path, json=payload_dict, headers=headers)
    print(f"Executed {side.upper()}! Response: {res.json()}")

def run_fibo_strategy():
    """YOUR 1H -> 15M -> 5M NESTED FIBONACCI CYCLE TRACKER ENGINE"""
    print("Bot initialized. Monitoring multi-timeframe structural blocks...")
    bounce_count = 0
    
    while True:
        try:
            candles_1h = get_market_data("1h")
            candles_15m = get_market_data("15m")
            candles_5m = get_market_data("5m")
            
            if not candles_1h or not candles_15m or not candles_5m:
                time.sleep(60)
                continue
                
            # 1. Higher Timeframe Trend Filter (1-Hour direction)
            trend_1h = "BULL" if float(candles_1h[-1]['close']) > float(candles_1h[-2]['close']) else "BEAR"
            
            # 2. Extract local Swing High (1.0) and Swing Low (0.0) from past 100 periods
            recent_5m = candles_5m[-100:]
            high_1_0 = max([float(c['high']) for c in recent_5m])
            low_0_0 = min([float(c['low']) for c in recent_5m])
            total_range = high_1_0 - low_0_0
            
            # Define Fibo targets
            fibo_0_75 = low_0_0 + (total_range * 0.75)
            fibo_0_60 = low_0_0 + (total_range * 0.60)
            fibo_0_50 = low_0_0 + (total_range * 0.50)
            fibo_0_20 = low_0_0 + (total_range * 0.20)
            
            current_price = float(candles_5m[-1]['close'])
            print(f"[Scan] BTC: ${current_price} | 1H: {trend_1h} | 0.50 Level: ${round(fibo_0_50, 1)}")
            
            # --- BUY SIDE LOGIC (1H Trend is Bullish) ---
            if trend_1h == "BULL":
                # Check for structural invalidation (Never break 0.20)
                if current_price < fibo_0_20:
                    print("Structure broken! Price breached 0.20 floor. Resetting counters.")
                    bounce_count = 0
                
                # Check if price taps / stays near 0.50 pullback midpoint
                elif abs(current_price - fibo_0_50) <= (total_range * 0.02):
                    bounce_count += 1
                    print(f"Price holding 0.50 support. Multi-bounce count: {bounce_count}/3")
                
                # Trigger on continuation from 0.60 after 2-3 structural validations
                if bounce_count >= 2 and current_price >= fibo_0_60:
                    print("Continuation breakout confirmed! Firing automated execution order...")
                    execute_bracket_order(side="buy", tp_price=high_1_0, sl_price=fibo_0_20)
                    bounce_count = 0
                    time.sleep(1800) # Cooldown 30 mins
                    
        except Exception as e:
            print(f"Error in strategy execution loop: {e}")
            
        time.sleep(60) # Scan candlesticks every 60 seconds

@app.route('/')
def home():
    return jsonify({"status": "running", "bot": "delta-fibo-v1"}), 200

if __name__ == '__main__':
    threading.Thread(target=run_fibo_strategy, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
