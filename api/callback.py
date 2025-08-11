from flask import Flask, request, jsonify
from .db import get_db_connection

app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    data = request.json

    conn = get_db_connection()
    cur = conn.cursor()

    # Save raw callback data
    cur.execute(
        "INSERT INTO mpesa_callbacks (callback_data) VALUES (%s)",
        [str(data)]
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

def handler(request):
    with app.request_context(request.environ):
        return app.full_dispatch_request()