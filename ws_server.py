#!/usr/bin/env python3
"""Simple WebSocket broadcast server for TheBot runtime_state updates.

Run this on the same machine as the bot and dashboard. The bot will connect
to this server as a client and send JSON messages; the server broadcasts
received messages to all connected dashboard clients.

Usage:
  python ws_server.py

Requires: `websockets` package
"""
import asyncio
import logging
import json
import os
import yaml
from websockets import serve

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CONNECTED = set()

# Read config to get expected token (optional)
BASE_DIR = os.path.dirname(__file__) or "."
CFG_PATH = os.path.join(BASE_DIR, "config.yaml")
EXPECTED_TOKEN = None
try:
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
            EXPECTED_TOKEN = cfg.get("ws_server_token")
except Exception:
    EXPECTED_TOKEN = None

async def handler(ws, path):
    # path may contain query string like '/?token=XYZ'
    # simple auth: require token query param if EXPECTED_TOKEN set
    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(path).query)
    token = qs.get("token", [None])[0]
    if EXPECTED_TOKEN and token != EXPECTED_TOKEN:
        logging.warning("Rejecting connection without valid token from %s", ws.remote_address)
        try:
            await ws.close(code=4001, reason="Authentication required")
        except Exception:
            pass
        return

    logging.info("Client connected: %s", ws.remote_address)
    CONNECTED.add(ws)
    try:
        async for msg in ws:
            # Received a message from a client — broadcast to others
            logging.debug("Received message, broadcasting to %d clients", len(CONNECTED))
            await broadcast(msg, sender=ws)
    except Exception:
        pass
    finally:
        CONNECTED.discard(ws)
        logging.info("Client disconnected: %s", ws.remote_address)

async def broadcast(message, sender=None):
    if not CONNECTED:
        return
    to_send = []
    for c in list(CONNECTED):
        if c == sender:
            continue
        try:
            to_send.append(asyncio.create_task(c.send(message)))
        except Exception:
            CONNECTED.discard(c)
    if to_send:
        await asyncio.gather(*to_send, return_exceptions=True)

async def main(host="0.0.0.0", port=8765):
    async with serve(handler, host, port):
        logging.info("WebSocket server listening ws://%s:%d", host, port)
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("ws_server stopped")
