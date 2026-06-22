import os
import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Fetch API keys securely from Render Environment Variables
API_KEY = os.getenv("DELTA_API_KEY")
API_SECRET = os.getenv("DELTA_API_SECRET")
BASE_URL = "https://delta.exchange"

def generate_signature(method, path, expiry, payload=""):
    """Generates the cryptographic signature required by Delta Exchange API"""
    message = method + str(expiry) + path + payload
    return hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

def check_confirmation_logic(data):
    """
    YOUR CONFIRMATION ENGINE
    """
    # Simply processes the order if confirmation is true
    if data.get("confirm", "true") == "true":
        return True
    return False

@app.route('/webhook', methods=['POST'])
def webhook():
    # 1. Receive data from TradingView
    alert_data = request.json
    if not alert_data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    print(f"Received Alert: {alert_data}")

    # 2. Run your Confirmation Check
    if not check_confirmation_logic(alert_data):
        print("Trade cancelled: Failed confirmation check.")
        return jsonify({"status": "ignored", "message": "Failed confirmation logic"}), 200

    # 3. Extract trade details from TradingView alert message
    try:
        symbol = alert_data['symbol']   # Delta Product ID (integer)
        size = alert_data['size']       # Order Size
        side = alert_data['side']       # "buy" or "sell"
        tp_price = alert_data['tp']     # Take Profit Target Price
        sl_price = alert_data['sl']     # Stop Loss Target Price
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing parameters: {str(e)}"}), 400

    # 4. Construct Delta Exchange Order Payload with automatic TP/SL
    path = "/v2/orders"
    expiry = int(time.time()) + 60
    
    payload_dict = {
        "product_id": int(symbol),
        "size": int(size),
        "side": side.lower(),
        "order_type": "market",
        "bracket_order": {
            "profit_trigger_price": str(tp_price),
            "loss_trigger_price": str(sl_price)
        }
    }
    
    # Convert payload dictionary to string format for signing
    payload_str = str(payload_dict).replace("'", '"') 

    # 5. Sign the Request
    headers = {
        "api-key": API_KEY,
        "api-signature": generate_signature("POST", path, expiry, payload_str),
        "api-expires": str(expiry),
        "Content-Type": "application/json"
    }
    
    # 6. Execute trade on Delta Exchange
    response = requests.post(BASE_URL + path, json=payload_dict, headers=headers)
    print(f"Delta Exchange Response: {response.json()}")
    
    return jsonify({"status": "success", "exchange_response": response.json()}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
