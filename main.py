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

def generate_signature(method, path, expiry, payload=""):
    message = method + str(expiry) + path + payload
    return hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

def get_live_price():
    try:
        url = f"{BASE_URL}/v2/tickers/{PRODUCT_ID}"
        response = requests.get(url)
        data = response.json()
        return float(data['result']['mark_price'])
    except Exception as e:
        print(f"Error fetching live price: {e}")
        return None

def execute_bracket_order(side, size, tp_price, sl_price):
    path = "/v2/orders"
    expiry = int(time.time()) + 60
    
    payload_dict = {
        "product_id": PRODUCT_ID,
        "size": int(size),
        "side": side.lower(),
        "order_type": "market",
        "bracket_order": {
            "profit_trigger_price": str(tp_price),
            "loss_trigger_price": str(sl_price)
        }
    }
    
    payload_str = str(payload_dict).replace("'", '"') 

    headers = {
        "api-key": API_KEY,
        "api-signature": generate_signature("POST", path, expiry, payload_str),
        "api-expires": str(expiry),
        "Content-Type": "application/json"
    }
    
    response = requests.post(BASE_URL + path, json=payload_dict, headers=headers)
    print(f"Order Executed! Response: {response.json()}")

def run_trading_strategy():
    """YOUR TRADING STRATEGY BRAIN Runs in the background"""
    print("Bot is scanning Delta Exchange markets...")
    
    # -------------------------------------------------------------
    # CHANGE YOUR TARGET PRICE RULES HERE
    # -------------------------------------------------------------
    buy_trigger_price = 64000.0  # Buy when Bitcoin drops to this price
    take_profit_price = 66000.0  # Take Profit target
    stop_loss_price   = 63000.0  # Stop Loss level
    order_size        = 10       # Number of contracts to trade
    # -------------------------------------------------------------

    while True:
        current_price = get_live_price()
        if current_price:
            print(f"Current BTC Price: ${current_price}")
            
            if current_price <= buy_trigger_price:
                print("Strategy rule triggered! Placing automated bracket order...")
                execute_bracket_order("buy", order_size, take_profit_price, stop_loss_price)
                time.sleep(3600) # Pause 1 hour after a trade
                
        time.sleep(60) # Check every 60 seconds

@app.route('/')
def home():
    return jsonify({"status": "running", "bot": "delta-autonomous-v1"}), 200

if __name__ == '__main__':
    # Start the strategy loop inside a safe background thread
    strategy_thread = threading.Thread(target=run_trading_strategy, daemon=True)
    strategy_thread.start()
    
    # Run the web port so Render doesn't crash
    app.run(host='0.0.0.0', port=10000)
