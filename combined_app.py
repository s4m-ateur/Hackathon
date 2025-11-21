from dotenv import load_dotenv
load_dotenv()

import os
import logging
from time import time
from flask import Flask, request, jsonify, send_from_directory, make_response
import requests

# ===============================
# CONFIG
# ===============================
PORT = 5001
STATIC_FOLDER = os.path.abspath('.')

app = Flask(__name__, static_folder=STATIC_FOLDER)
devices = {}   # device_id → {lat, lon, ts, distress}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Telegram credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ===============================
# CORS Headers
# ===============================
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

# ===============================
# Serve front-end (report.html)
# ===============================
@app.route('/')
def index():
    path = os.path.join(STATIC_FOLDER, 'report.html')
    if not os.path.exists(path):
        return make_response("report.html not found", 404)
    return send_from_directory(STATIC_FOLDER, 'report.html')

# ===============================
# Telegram Alert Function
# ===============================
def send_telegram_alert(device_id, lat, lon, ts):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram not configured. Missing token or chat_id.")
        return False, "not_configured"

    maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    text = (
        f"🚨 *SOS ALERT*\n\n"
        f"Device: {device_id}\n"
        f"Latitude: {lat}\n"
        f"Longitude: {lon}\n"
        f"Time: {ts}\n"
        f"Google Maps: {maps_link}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })
        r.raise_for_status()
        logging.info("Telegram alert sent successfully.")
        return True, "sent"
    except Exception as e:
        logging.error(f"Telegram alert failed: {e}")
        return False, str(e)

# ===============================
# Receive location + distress
# ===============================
@app.route('/report_location', methods=['POST', 'OPTIONS'])
def report_location():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    try:
        data = request.get_json(force=True)
    except:
        return make_response(jsonify({"error": "invalid JSON"}), 400)

    device_id = str(data.get("device_id", "")).strip()
    if not device_id:
        return make_response(jsonify({"error": "device_id required"}), 400)

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except:
        return make_response(jsonify({"error": "lat/lon must be numeric"}), 400)

    ts = int(time() * 1000)
    distress = bool(data.get("distress", False))

    # Save in memory
    devices[device_id] = {
        "lat": lat,
        "lon": lon,
        "ts": ts,
        "distress": distress
    }

    logging.info(f"{device_id}: lat={lat}, lon={lon}, distress={distress}")

    # Send Telegram alert if distress detected
    if distress:
        ok, info = send_telegram_alert(device_id, lat, lon, ts)
        if not ok:
            logging.warning(f"Telegram FAILED for {device_id}: {info}")

    return jsonify({"status": "ok"}), 200

# ===============================
# Return device list for dashboard
# ===============================
@app.route('/devices', methods=['GET'])
def get_devices():
    return jsonify(devices), 200

# ===============================
# Health check
# ===============================
@app.route('/health')
def health():
    return jsonify({"status": "ok", "devices": len(devices)})

# ===============================
# Start server
# ===============================
if __name__ == "__main__":
    logging.info(f"Backend running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
