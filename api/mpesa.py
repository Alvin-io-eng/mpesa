import os
import requests
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth
from flask import Flask, request, jsonify
import psycopg

app = Flask(__name__)

# --- Environment Variables ---
# Ensure these are set in your Vercel project settings
BUSINESS_SHORTCODE = os.getenv("BUSINESS_SHORTCODE")
PASSKEY = os.getenv("PASSKEY")
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")
DATABASE_URL = os.getenv("POSTGRES_URL")

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    # The psycopg library connects directly using the DATABASE_URL
    return psycopg.connect(DATABASE_URL, autocommit=True)

def get_access_token():
    """Generates an M-Pesa API access token."""
    try:
        api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        # Use HTTPBasicAuth for cleaner authentication
        r = requests.get(api_url, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET))
        # Raise an exception for bad status codes (4xx or 5xx)
        r.raise_for_status()
        data = r.json()
        # The token is what's needed, not the "Bearer " prefix yet
        return data.get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"Error getting access token: {e}")
        return None

@app.route('/stkpush', methods=['GET'])
def stk_push():
    """Initiates an STK Push request."""
    try:
        phone_number = '254728902689' # Example phone number
        amount = '1' # Example amount

        if not all([phone_number, amount]):
            return jsonify({"success": False, "message": "Phone number and amount are required"}), 400

        access_token = get_access_token()
        if not access_token:
            return jsonify({'success': False, 'message': "Failed to generate access token"}), 500

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{BUSINESS_SHORTCODE}{PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode('utf-8')

        payload = {
            "BusinessShortCode": BUSINESS_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": BUSINESS_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "TestPayment123",
            "TransactionDesc": "Payment for testing purposes"
        }

        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()

        return jsonify(response.json()), 200

    except requests.exceptions.RequestException as e:
        # More specific error for failed HTTP requests
        return jsonify({"success": False, "message": "Request to M-Pesa API failed", "error": str(e)}), 502 # Bad Gateway
    except Exception as e:
        print(f"An unexpected error occurred in stk_push: {e}")
        return jsonify({"success": False, "message": "An internal server error occurred", "error": str(e)}), 500

@app.route("/callback", methods=["POST"])
def callback():
    """Handles the callback response from M-Pesa."""
    # Use get_json with silent=True to avoid errors on empty/invalid JSON
    data = request.get_json(silent=True)
    if not data:
        print("Callback received with no JSON data.")
        return jsonify({"ResultCode": -1, "ResultDesc": "No JSON data received"}), 400

    print("Callback Data Received:", data)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Storing the entire JSON data is better for flexibility
            cur.execute(
                "INSERT INTO mpesa_callbacks (callback_data) VALUES (%s)",
                (jsonify(data),) # Use jsonify to properly format the data for JSONB column type
            )
        print("Callback data stored successfully.")
    except psycopg.Error as e:
        print(f"Database error: {e}")
        # Avoid exposing detailed DB errors to the client
        return jsonify({"ResultCode": -1, "ResultDesc": "Failed due to a database error."}), 500
    finally:
        if conn:
            conn.close()

    # Acknowledge receipt to M-Pesa API
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

# This allows running the app locally for testing if needed
# if __name__ == "__main__":
#     app.run(debug=True)
