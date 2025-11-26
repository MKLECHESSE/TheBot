"""
Simple webhook server to accept authenticated POST requests that contain
proposed action JSON. Writes `proposed_changes.json` into the project folder so
`TheBot.py` running locally will process them.

Security model:
- Uses an HMAC-SHA256 signature header `X-Signature` computed over the raw body
  using a shared secret. The server validates the signature before accepting.
- The shared secret must be provided via environment variable `WEBHOOK_SECRET`.

Usage:
    # install dependencies
    pip install flask

    # run (example)
    set WEBHOOK_SECRET=your_secret_here
    python webhook_server.py --host 0.0.0.0 --port 8080

POST payload expected: JSON array of action objects or single action object.
Examples of actions:
  {"action":"order_send", "symbol":"EURUSD", "signal":"BUY", "comment":"from-webhook"}
  {"action":"modify_sl", "position":12345, "new_sl":1.2345}

The server writes `proposed_changes.json` (appended) so the local bot can process.
"""
from __future__ import annotations
import os
import hmac
import hashlib
import json
import argparse
from flask import Flask, request, jsonify
from datetime import datetime

BASE_DIR = os.path.dirname(__file__) or "."
APP = Flask(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
if not WEBHOOK_SECRET:
    # allow running but require explicit env when accepting requests
    print("WARNING: WEBHOOK_SECRET not set. The server will reject requests without a secret.")

SIGNATURE_HEADER = "X-Signature"


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    if not signature:
        return False
    try:
        computed = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)
    except Exception:
        return False


def append_proposed(items: list[dict]):
    path = os.path.join(BASE_DIR, "proposed_changes.json")
    existing = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing.extend(items)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


@APP.route("/webhook", methods=["POST"])
def webhook():
    if not WEBHOOK_SECRET:
        return jsonify({"error": "server not configured (missing WEBHOOK_SECRET)"}), 500

    body = request.get_data()
    sig = request.headers.get(SIGNATURE_HEADER, "")
    if not verify_signature(WEBHOOK_SECRET, body, sig):
        return jsonify({"error": "invalid signature"}), 401

    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    if isinstance(payload, dict):
        items = [payload]
    elif isinstance(payload, list):
        items = payload
    else:
        return jsonify({"error": "payload must be object or array"}), 400

    # timestamp each item and append
    for it in items:
        it.setdefault("ts", datetime.now(timezone.utc).isoformat())

    try:
        append_proposed(items)
    except Exception as e:
        return jsonify({"error": "failed to write proposed file", "detail": str(e)}), 500

    return jsonify({"ok": True, "count": len(items)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    print(f"Starting webhook server on {args.host}:{args.port}")
    APP.run(host=args.host, port=args.port)
