import os
import hmac
import hashlib
import time
import requests

# API Configuration securely loaded from Render environment variables
API_KEY = os.getenv("DELTA_API_KEY")
API_SECRET = os.getenv("DELTA_API_SECRET")
BASE_URL = "https://delta.exchange"
PRODUCT_ID = 27  # BTCUSD Perpetual Contract ID on Delta Exchange

def generate_signature(method, path, expiry, payload=""):
    """Generates the cryptographic signature required by Delta Exchange API"""
    message = method + str(expiry) + path + payload
    return hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

def get_live_price():
    """Fetches the live ticker price of Bitcoin from Delta Exchange"""
    try:
        url = f"{BASE_URL}/v2/tickers/{PRODUCT_ID}"
        response = requests.get(url)
        data = response.json()
        return float(data['result']['mark_price'])
    except Exception as e:
        print(f"Error fetching live price: {e}")
        return None

def execute_bracket_order(side, size, tp_price, sl_price):
    """Sends a market order linked with automated Take Profit and Stop Loss"""
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
    """YOUR TRADING STRATEGY BRAIN"""
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
            
            # Match condition: Price drops to or below your target
            if current_price <= buy_trigger_price:
                print("Strategy rule triggered! Placing automated bracket order...")
                execute_bracket_order("buy", order_size, take_profit_price, stop_loss_price)
                
                # Pause the script for 1 hour after trading to avoid duplicate loops
                time.sleep(3600) 
                
        # Wait 60 seconds before checking the market price again
        time.sleep(60)

if __name__ == '__main__':
    run_trading_strategy()
