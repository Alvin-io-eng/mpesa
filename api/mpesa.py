import os
import requests
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth
from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

BUSINESS_SHORTCODE = os.getenv("BUSINESS_SHORTCODE")
PASSKEY = os.getenv("PASSKEY")
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def accessToken():
    try:
        api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        r = requests.get(api_url, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET))
        r.raise_for_status()
        data = r.json()
        access_token = "Bearer " + data['access_token']
        return access_token
    except Exception as e:
        return {
            'success': False,
            'message': "Failed to generate access token",
            "error": str(e)
        }

@app.route('/stkpush')
def stk_push():
    try:
        phone_number = '254728902689'
        amount = '1'
        if not phone_number or not amount:
            return jsonify({"success": False, "message": "Phone number and amount are required"}), 400

        access_token = accessToken()
        if 'success' in access_token and not access_token['success']:
            return jsonify(access_token), 500

        headers = {
            'Authorization': access_token,
            'Content-Type': 'application/json'
        }

        payload = {
            "BusinessShortCode": BUSINESS_SHORTCODE,
            "Password": base64.b64encode(f"{BUSINESS_SHORTCODE}{PASSKEY}{datetime.now().strftime('%Y%m%d%H%M%S')}".encode()).decode('utf-8'),
            "Timestamp": datetime.now().strftime('%Y%m%d%H%M%S'),
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": BUSINESS_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "Test123",
            "TransactionDesc": "Payment for testing"
        }

        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()

        return jsonify(response.json()), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": "Request failed", "error": str(e)}), 500
    except Exception as e:
        return jsonify({"success": False, "message": "An error occurred", "error": str(e)}), 500

# --- Callback Endpoint ---
@app.route("/callback", methods=["POST"])
def callback():
    data = request.json or {}
    print("Callback Data:", data)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO mpesa_callbacks (callback_data) VALUES (%s)",
            [str(data)]
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB error:", e)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

# --- Required for Vercel ---
def handler(request, response=None):
    with app.request_context(request.environ):
        return app.full_dispatch_request()