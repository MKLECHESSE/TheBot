#!/usr/bin/env python3
"""Starter trading bot (steps 1-6).

Safe to run without MT5: when MT5 is not available the bot runs in simulation mode
and generates synthetic data for indicator testing. `live_trading` is read from
`config.yaml` and defaults to false.
"""

import os
import time
import json
import logging
import argparse
from datetime import datetime

import yaml
from dotenv import load_dotenv
load_dotenv()

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

import pandas as pd
import numpy as np
import requests


# ============================================================
# 🧩 Setup
# ============================================================

BASE_DIR = os.path.dirname(__file__) or "."
LOG_FILE = os.getenv("LOG_FILE") or os.path.join(BASE_DIR, "bot.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Load config.yaml
with open(os.path.join(BASE_DIR, "config.yaml"), "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Command-line args
parser = argparse.ArgumentParser(description="TheBot starter trading bot")
parser.add_argument("--dry-run", action="store_true", help="Force simulation mode and write proposed changes to file")
parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
args = parser.parse_args()
DRY_RUN = bool(args.dry_run)
ONCE = bool(args.once)

LIVE_TRADING = config.get("live_trading", False)
DELAY = config.get("symbol_delay", 2)
CHECK_INTERVAL = config.get("check_interval", 60)

PROFILES = config.get("profiles", {})
SYMBOL_GROUPS = config.get("symbols", {})

# convenience
PROFILE_CLASSIC = PROFILES.get("classic", {})
SYMBOLS_CLASSIC = SYMBOL_GROUPS.get("classic", [])

# ============================================================
# ⚙️ MetaTrader 5 Connection
# ============================================================

def ensure_mt5_init():
    """Try to initialize MT5. Return True if ready, False otherwise.

    When MT5 is not available (e.g., not installed), this returns False and the
    bot will run in simulation mode.
    """
    if mt5 is None:
        logging.warning("MT5 package not available; running in simulation mode.")
        return False
    ok = mt5.initialize()
    if not ok:
        logging.error("MT5 initialize() returned False; running in simulation mode.")
        return False
    logging.info("MT5 initialized")
    return True


# ============================================================
# 📈 Data Fetching & Analysis
# ============================================================

def fetch_mt5_rates(symbol, timeframe, n=500, mt5_ready=False):
    """Fetch rates from MT5. If MT5 not ready, return a synthetic dataframe.

    The synthetic dataframe is a small random-walk useful for exercising
    indicator code during local tests.
    """
    if mt5_ready and mt5 is not None:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No rates for {symbol}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    # simulation fallback: build synthetic series
    now = int(time.time())
    periods = n
    times = pd.to_datetime([now - 60 * i for i in range(periods)][::-1], unit="s")
    # create a simple synthetic price using a sine + noise
    base = 1.0
    idx = np.arange(periods)
    price = base + 0.001 * np.sin(idx / 10.0) + 0.0005 * np.random.randn(periods)
    df = pd.DataFrame({
        "time": times,
        "open": price + 0.0001,
        "high": price + 0.0002,
        "low": price - 0.0002,
        "close": price,
        "tick_volume": np.random.randint(1, 10, size=periods),
    })
    return df


def calculate_indicators_ta(df, profile):
    """Calculate indicators using `ta` when available, otherwise fallback.

    Returns a dict of indicator values for the latest row.
    """
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    ind = {}
    try:
        from ta.momentum import RSIIndicator
        from ta.trend import EMAIndicator, MACD, ADXIndicator
        from ta.volatility import AverageTrueRange, BollingerBands

        ind["rsi"] = float(RSIIndicator(close, window=profile["rsi"]["period"]).rsi().iloc[-1])
        macd = MACD(close,
                    window_slow=profile["macd"]["slow_period"],
                    window_fast=profile["macd"]["fast_period"],
                    window_sign=profile["macd"]["signal_period"])
        ind["macd_hist"] = float(macd.macd_diff().iloc[-1])
        ind["ema_fast"] = float(EMAIndicator(close, profile["moving_averages"]["ema_fast"]).ema_indicator().iloc[-1])
        ind["ema_slow"] = float(EMAIndicator(close, profile["moving_averages"]["ema_slow"]).ema_indicator().iloc[-1])
        ind["adx"] = float(ADXIndicator(high, low, close, window=profile["adx"]["period"]).adx().iloc[-1])
        ind["atr"] = float(AverageTrueRange(high, low, close, window=profile["atr"]["period"]).average_true_range().iloc[-1])
        bb = BollingerBands(close, window=profile["bollinger"]["period"], window_dev=profile["bollinger"]["std_dev"])
        ind["bb_upper"] = float(bb.bollinger_hband().iloc[-1])
        ind["bb_mid"] = float(bb.bollinger_mavg().iloc[-1])
        ind["bb_lower"] = float(bb.bollinger_lband().iloc[-1])
    except Exception as e:
        # fallback minimal indicators
        window = profile.get("rsi", {}).get("period", 14)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(window).mean()
        loss = (-delta).clip(lower=0).rolling(window).mean()
        rs = gain / (loss.replace(0, np.nan))
        ind["rsi"] = float((100 - (100 / (1 + rs))).iloc[-1])
        ind["ema_fast"] = float(close.ewm(span=profile.get("moving_averages", {}).get("ema_fast", 9)).mean().iloc[-1])
        ind["ema_slow"] = float(close.ewm(span=profile.get("moving_averages", {}).get("ema_slow", 21)).mean().iloc[-1])
        ind["macd_hist"] = float((ind["ema_fast"] - ind["ema_slow"]))
        ind["adx"] = 0.0
        ind["atr"] = float((high - low).rolling(profile.get("atr", {}).get("period", 14)).mean().iloc[-1])
        ind["bb_upper"] = float(close.rolling(profile.get("bollinger", {}).get("period", 20)).mean().iloc[-1])
        ind["bb_mid"] = float(close.rolling(profile.get("bollinger", {}).get("period", 20)).mean().iloc[-1])
        ind["bb_lower"] = float(ind["bb_mid"])

    return ind


def analyze_symbol(symbol, profile, mt5_ready=False):
    """Analyze a symbol using M15 signals with optional H1 confirmation.

    Returns (signal, reason, indicators)
    """
    try:
        df_m15 = fetch_mt5_rates(symbol, getattr(mt5, "TIMEFRAME_M15", 15), n=500, mt5_ready=mt5_ready)
    except Exception as e:
        logging.error("Failed to fetch rates for %s: %s", symbol, e)
        return "HOLD", "fetch_error", {}

    if df_m15 is None or df_m15.empty:
        return "HOLD", "no_data", {}

    ind_m15 = calculate_indicators_ta(df_m15, profile)
    # basic filters
    if ind_m15.get("adx", 0.0) < profile.get("adx", {}).get("min_strength", 0):
        return "HOLD", "adx_low", ind_m15
    if ind_m15.get("atr", 0.0) < profile.get("atr", {}).get("min_volatility_factor", 0):
        return "HOLD", "atr_low", ind_m15

    buy = ind_m15.get("macd_hist", 0) > 0 and ind_m15.get("rsi", 50) <= profile.get("rsi", {}).get("buy_threshold", 30) and ind_m15.get("ema_fast", 0) > ind_m15.get("ema_slow", 0)
    sell = ind_m15.get("macd_hist", 0) < 0 and ind_m15.get("rsi", 50) >= profile.get("rsi", {}).get("sell_threshold", 70) and ind_m15.get("ema_fast", 0) < ind_m15.get("ema_slow", 0)

    signal = "HOLD"
    if buy:
        signal = "BUY"
    elif sell:
        signal = "SELL"

    # optional H1 confirmation
    try:
        df_h1 = fetch_mt5_rates(symbol, getattr(mt5, "TIMEFRAME_H1", 60), n=500, mt5_ready=mt5_ready)
        if df_h1 is not None and not df_h1.empty:
            ind_h1 = calculate_indicators_ta(df_h1, profile)
            if signal == "BUY" and ind_h1.get("ema_fast", 0) <= ind_h1.get("ema_slow", 0):
                return "HOLD", "h1_mismatch", ind_m15
            if signal == "SELL" and ind_h1.get("ema_fast", 0) >= ind_h1.get("ema_slow", 0):
                return "HOLD", "h1_mismatch", ind_m15
    except Exception:
        pass

    return signal, "m15_signal", ind_m15


# ============================================================
# 💹 Trade Execution (Live only)
# ============================================================

def execute_trade(symbol, signal, lot=0.1, sl_points=100, tp_points=100):
    """Executes a BUY or SELL order if live trading is enabled."""
    if not LIVE_TRADING:
        logging.info(f"[DEMO] Skipping trade execution for {symbol} ({signal})")
        return

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logging.error(f"Symbol not found: {symbol}")
        return

    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logging.error(f"Failed to get tick for {symbol}")
        return

    if signal == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        sl = price - sl_points * symbol_info.point
        tp = price + tp_points * symbol_info.point
    elif signal == "SELL":
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        sl = price + sl_points * symbol_info.point
        tp = price - tp_points * symbol_info.point
    else:
        return

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 123456,
        "comment": "AutoBot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"❌ Trade failed: {result.retcode}, {result.comment}")
    else:
        logging.info(f"✅ Trade successful: {signal} {symbol}, Ticket #{result.order}")


# ============================================================
# 📧 & 💬 Alerts (Optional)
# ============================================================

def send_email_alert(subject, body):
    # env-driven, safe no-op when not configured
    EMAIL_FROM = os.getenv("EMAIL_FROM")
    EMAIL_PASS = os.getenv("EMAIL_PASSWORD")
    EMAIL_TO = os.getenv("EMAIL_TO")
    if not (EMAIL_FROM and EMAIL_PASS and EMAIL_TO):
        logging.debug("Email not configured; skipping")
        return False
    try:
        from email.mime.text import MIMEText
        import smtplib
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_FROM, EMAIL_PASS)
            s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        logging.info("Email sent")
        return True
    except Exception as e:
        logging.error("Email send failed: %s", e)
        return False


def send_telegram_alert(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        logging.debug("Telegram not configured; skipping")
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat, "text": message}, timeout=10)
        if r.ok:
            logging.info("Telegram sent")
            return True
        logging.error("Telegram send failed: %s", r.text)
        return False
    except Exception as e:
        logging.error("Telegram failed: %s", e)
        return False


def calculate_lot_from_risk(symbol, sl_price, entry_price, risk_percent=None):
    """Calculate lot size based on account balance and SL distance.

    This function uses MT5 account info and symbol info when available. If
    MT5 is not available it returns a safe default (0.01).
    """
    try:
        if mt5 is None:
            return 0.01
        risk_pct = risk_percent or config.get("risk_percentage", 1)
        acc = mt5.account_info()
        if acc is None:
            return 0.01
        balance = float(acc.balance)
        risk_amount = balance * (risk_pct / 100.0)
        sym = mt5.symbol_info(symbol)
        if sym is None:
            return 0.01
        point = getattr(sym, "point", 1.0)
        # estimate value per point: prefer trade_tick_value/trade_tick_size
        tick_value = getattr(sym, "trade_tick_value", None)
        tick_size = getattr(sym, "trade_tick_size", None)
        if tick_value and tick_size:
            value_per_point = tick_value / tick_size
        else:
            # fallback: approximate using contract_size if available
            contract_size = getattr(sym, "trade_contract_size", None) or 1.0
            value_per_point = contract_size
        sl_points = abs(entry_price - sl_price) / (point if point else 1.0)
        if sl_points <= 0:
            return 0.01
        lot = risk_amount / (sl_points * value_per_point)
        # round to two decimals and clamp
        lot = max(round(lot, 2), 0.01)
        return float(lot)
    except Exception:
        return 0.01


def execute_trade(symbol, signal, ind, extra_comment="AutoBot"):
    """Execute a market trade via MT5.

    - Uses ATR from `ind` to compute SL/TP distances (multipliers from config).
    - Computes lot size via `calculate_lot_from_risk()`.
    - Gated by `live_trading` in config: if false, logs simulation only.
    """
    try:
        if not config.get("live_trading", False) or DRY_RUN:
            logging.info("[SIM] live_trading disabled or dry-run; would execute %s %s", signal, symbol)
            proposed = {
                "ts": datetime.utcnow().isoformat(),
                "action": "order_send",
                "symbol": symbol,
                "signal": signal,
                "price": None,
                "sl": None,
                "tp": None,
                "lot": None,
                "indicators": ind,
            }
            save_proposed_change(proposed)
            return {"sim": True}

        if mt5 is None:
            logging.error("MT5 module not available; cannot execute trades")
            return None

        sym = mt5.symbol_info(symbol)
        if sym is None:
            logging.error("Symbol not available on MT5: %s", symbol)
            return None
        if not sym.visible:
            mt5.symbol_select(symbol, True)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logging.error("No tick for %s", symbol)
            return None

        atr = float(ind.get("atr", 0.0))
        sl_mult = config.get("atr_sl_multiplier", 2)
        tp_mult = config.get("atr_tp_multiplier", 4)

        if signal == "BUY":
            price = float(tick.ask)
            sl = price - atr * sl_mult
            tp = price + atr * tp_mult
            order_type = mt5.ORDER_TYPE_BUY
        elif signal == "SELL":
            price = float(tick.bid)
            sl = price + atr * sl_mult
            tp = price - atr * tp_mult
            order_type = mt5.ORDER_TYPE_SELL
        else:
            logging.info("No execution for signal=%s", signal)
            return None

        lot = calculate_lot_from_risk(symbol, sl, price)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": int(config.get("magic_number", 123456)),
            "comment": extra_comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)
        logging.info("order_send result: %s", result)
        return result
    except Exception as e:
        logging.exception("execute_trade failed: %s", e)
        return None


def manage_open_positions():
    """Non-destructive position manager.

    This function enumerates open positions and logs suggested trailing stop and
    breakeven actions. By default it does not modify positions. To enable
    automatic modifications, set `position_management.enabled: true` in
    `config.yaml` (not added by default) and review behavior carefully.
    """
    try:
        if mt5 is None:
            logging.debug("MT5 not available; skipping position management")
            return
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            return
        for pos in positions:
            symbol = pos.symbol
            volume = pos.volume
            price_open = pos.price_open
            profit = pos.profit
            logging.info("Open position %s vol=%s open=%.5f profit=%.2f", symbol, volume, price_open, profit)
            # compute suggested SL movement based on ATR
            try:
                df = fetch_mt5_rates(symbol, getattr(mt5, "TIMEFRAME_M15", 15), n=200, mt5_ready=True)
                if df is not None and not df.empty:
                    ind = calculate_indicators_ta(df, PROFILE_CLASSIC)
                    atr = ind.get("atr", 0.0)
                else:
                    atr = 0.0
            except Exception:
                atr = 0.0

                # do not modify by default; just log suggestion
                logging.info("Suggested ATR for %s = %s", symbol, atr)

                # Optional automatic SL/TP modification (disabled by default)
                pm = config.get("position_management", {})
                if pm.get("enabled", False) and pm.get("auto_modify", False):
                    try:
                        sym = mt5.symbol_info(symbol)
                        if sym is None:
                            continue
                        point = getattr(sym, "point", 1.0)
                        # current market price for the symbol
                        tick = mt5.symbol_info_tick(symbol)
                        if tick is None:
                            continue
                        # for BUY positions current price is bid (we can close at bid)
                        if pos.type == mt5.POSITION_TYPE_BUY:
                            current_price = float(tick.bid)
                            profit_points = (current_price - price_open) / (point if point else 1.0)
                            # breakeven
                            if profit_points >= (pm.get("breakeven_buffer_points", 1.0)) * pm.get("breakeven_buffer_points", 1.0):
                                new_sl = price_open + (pm.get("breakeven_buffer_points", 1.0) * point)
                                if new_sl > pos.sl:
                                    logging.info("Would move BUY SL for %s from %.5f to %.5f", symbol, pos.sl, new_sl)
                                    # attempt modify
                                    try:
                                        action = getattr(mt5, "TRADE_ACTION_SLTP", None)
                                        if action is not None:
                                            req = {"action": action, "position": int(pos.ticket), "sl": float(new_sl), "tp": float(pos.tp)}
                                            if DRY_RUN:
                                                save_proposed_change({"ts": datetime.utcnow().isoformat(), "action": "modify_sl", "symbol": symbol, "position": int(pos.ticket), "new_sl": float(new_sl)})
                                            else:
                                                mt5.order_send(req)
                                        else:
                                            logging.debug("TRADE_ACTION_SLTP not available; skip actual modify")
                                    except Exception as e:
                                        logging.exception("Failed to modify SL for %s: %s", symbol, e)
                            # trailing
                            trailing_trigger = atr * pm.get("trailing_min_profit_atr", 1.0)
                            if profit_points >= trailing_trigger:
                                new_sl = current_price - atr * pm.get("trailing", {}).get("multiplier", config.get("trailing", {}).get("multiplier", 1.5))
                                if new_sl > pos.sl:
                                    logging.info("Would trail BUY SL for %s from %.5f to %.5f", symbol, pos.sl, new_sl)
                                    try:
                                        action = getattr(mt5, "TRADE_ACTION_SLTP", None)
                                        if action is not None:
                                            req = {"action": action, "position": int(pos.ticket), "sl": float(new_sl), "tp": float(pos.tp)}
                                            if DRY_RUN:
                                                save_proposed_change({"ts": datetime.utcnow().isoformat(), "action": "modify_sl", "symbol": symbol, "position": int(pos.ticket), "new_sl": float(new_sl)})
                                            else:
                                                mt5.order_send(req)
                                        else:
                                            logging.debug("TRADE_ACTION_SLTP not available; skip actual modify")
                                    except Exception as e:
                                        logging.exception("Failed to trail SL for %s: %s", symbol, e)
                        else:
                            # SELL position
                            current_price = float(tick.ask)
                            profit_points = (price_open - current_price) / (point if point else 1.0)
                            if profit_points >= (pm.get("breakeven_buffer_points", 1.0)) * pm.get("breakeven_buffer_points", 1.0):
                                new_sl = price_open - (pm.get("breakeven_buffer_points", 1.0) * point)
                                if new_sl < pos.sl or pos.sl == 0.0:
                                    logging.info("Would move SELL SL for %s from %.5f to %.5f", symbol, pos.sl, new_sl)
                                    try:
                                        action = getattr(mt5, "TRADE_ACTION_SLTP", None)
                                        if action is not None:
                                            req = {"action": action, "position": int(pos.ticket), "sl": float(new_sl), "tp": float(pos.tp)}
                                            if DRY_RUN:
                                                save_proposed_change({"ts": datetime.utcnow().isoformat(), "action": "modify_sl", "symbol": symbol, "position": int(pos.ticket), "new_sl": float(new_sl)})
                                            else:
                                                mt5.order_send(req)
                                        else:
                                            logging.debug("TRADE_ACTION_SLTP not available; skip actual modify")
                                    except Exception as e:
                                        logging.exception("Failed to modify SL for %s: %s", symbol, e)
                            trailing_trigger = atr * pm.get("trailing_min_profit_atr", 1.0)
                            if profit_points >= trailing_trigger:
                                new_sl = current_price + atr * pm.get("trailing", {}).get("multiplier", config.get("trailing", {}).get("multiplier", 1.5))
                                if new_sl < pos.sl or pos.sl == 0.0:
                                    logging.info("Would trail SELL SL for %s from %.5f to %.5f", symbol, pos.sl, new_sl)
                                    try:
                                        action = getattr(mt5, "TRADE_ACTION_SLTP", None)
                                        if action is not None:
                                            req = {"action": action, "position": int(pos.ticket), "sl": float(new_sl), "tp": float(pos.tp)}
                                            mt5.order_send(req)
                                        else:
                                            logging.debug("TRADE_ACTION_SLTP not available; skip actual modify")
                                    except Exception as e:
                                        logging.exception("Failed to trail SL for %s: %s", symbol, e)
                    except Exception as e:
                        logging.exception("position modification error for %s: %s", symbol, e)
    except Exception as e:
        logging.exception("manage_open_positions failed: %s", e)


def save_proposed_change(item):
    """Append a proposed change (dict) to `proposed_changes.json` in the project folder."""
    try:
        path = os.path.join(BASE_DIR, "proposed_changes.json")
        existing = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.append(item)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        logging.info("Saved proposed change: %s", item.get("action"))
    except Exception as e:
        logging.exception("Failed to save proposed change: %s", e)


def process_proposed_changes():
    """Process a local `proposed_changes.json` file containing action dicts.

    This allows an external UI or operator to drop-in a JSON file with
    instructions like `{'action':'order_send','symbol':'EURUSD','signal':'BUY'}`
    and have the running bot execute them (when live_trading is enabled).
    After processing, the file is archived to `proposed_changes_executed.json`.
    """
    path = os.path.join(BASE_DIR, "proposed_changes.json")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        logging.exception("Failed to read proposed_changes.json")
        return

    if not items:
        return

    executed = []
    for item in items:
        try:
            act = item.get("action")
            if act == "order_send":
                sym = item.get("symbol")
                sig = item.get("signal")
                ind = item.get("indicators", {})
                logging.info("Processing proposed order_send: %s %s", sig, sym)
                if config.get("live_trading", False) and not DRY_RUN:
                    execute_trade(sym, sig, ind, extra_comment=item.get("comment", "proposed_action"))
                    logging.info("Executed proposed order for %s", sym)
                else:
                    save_proposed_change({"ts": datetime.utcnow().isoformat(), "action": "simulated_execution", "source": "process_proposed_changes", "orig": item})
                executed.append(item)
            elif act == "modify_sl":
                # attempt to modify SL for a position (best-effort)
                pos = int(item.get("position")) if item.get("position") else None
                new_sl = float(item.get("new_sl")) if item.get("new_sl") else None
                if pos and new_sl is not None:
                    try:
                        if mt5 is not None and config.get("live_trading", False) and not DRY_RUN:
                            req = {"action": getattr(mt5, "TRADE_ACTION_SLTP", 0), "position": pos, "sl": float(new_sl), "tp": 0}
                            mt5.order_send(req)
                            logging.info("Modified SL for position %s -> %s", pos, new_sl)
                        else:
                            logging.info("Simulated modify_sl for %s -> %s", pos, new_sl)
                    except Exception:
                        logging.exception("modify_sl failed for %s", pos)
                executed.append(item)
            elif act == "close_position":
                pos = int(item.get("position")) if item.get("position") else None
                if pos:
                    try:
                        if mt5 is not None and config.get("live_trading", False) and not DRY_RUN:
                            req = {"action": mt5.TRADE_ACTION_CLOSE_BY, "position": pos}
                            mt5.order_send(req)
                            logging.info("Closed position %s", pos)
                        else:
                            logging.info("Simulated close_position %s", pos)
                    except Exception:
                        logging.exception("close_position failed for %s", pos)
                executed.append(item)
            else:
                logging.warning("Unknown proposed action: %s", act)
                executed.append(item)
        except Exception:
            logging.exception("Failed to process proposed item: %s", item)

    # archive executed items
    try:
        arch_path = os.path.join(BASE_DIR, "proposed_changes_executed.json")
        existing = []
        if os.path.exists(arch_path):
            try:
                with open(arch_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.extend(executed)
        with open(arch_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except Exception:
        logging.exception("Failed to archive executed proposed changes")

    # remove original file
    try:
        os.remove(path)
    except Exception:
        logging.exception("Failed to remove processed proposed_changes.json")


# ============================================================
# 🚀 Bot Loop
# ============================================================

def init_perf_log():
    PERF_LOG = os.path.join(BASE_DIR, "performance_log.csv")
    if not os.path.exists(PERF_LOG):
        with open(PERF_LOG, "w", encoding="utf-8") as f:
            f.write("timestamp,symbol,profile,signal,reason,indicators\n")
    return PERF_LOG


def append_perf(symbol, profile_name, signal, reason, indicators=None):
    PERF_LOG = init_perf_log()
    row = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "profile": profile_name,
        "signal": signal,
        "reason": reason,
        "indicators": indicators or {},
    }
    with open(PERF_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def run_starter_loop():
    mt5_ready = ensure_mt5_init()
    if not mt5_ready:
        logging.error("MT5 is required for live_trading. Exiting.")
        print("MT5 is required for live_trading. Exiting.")
        return
    profile = PROFILE_CLASSIC
    symbols = SYMBOLS_CLASSIC
    logging.info("Starting starter bot; live_trading=%s symbols=%s", LIVE_TRADING, symbols)
    try:
        while True:
            for s in symbols:
                try:
                    sig, reason, ind = analyze_symbol(s, profile, mt5_ready=mt5_ready)
                    logging.info("%s -> %s (%s)", s, sig, reason)
                    append_perf(s, "classic", sig, reason, ind)
                    if sig in ("BUY", "SELL"):
                        msg = f"{sig} {s} reason={reason}"
                        send_email_alert("Trading Alert", msg)
                        send_telegram_alert(msg)
                        # Execute trade if live_trading enabled
                        if config.get("live_trading", False):
                            res = execute_trade(s, sig, ind)
                            logging.info("Execution result: %s", res)
                    time.sleep(DELAY)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logging.exception("Error analyzing %s: %s", s, e)
                    time.sleep(1)
            logging.info("Cycle complete")
            # process any proposed changes created by an operator/UI
            try:
                process_proposed_changes()
            except Exception:
                logging.exception("process_proposed_changes failed")
            # If --once flag set, exit after single cycle
            if ONCE:
                logging.info("Once-mode enabled; exiting after one cycle")
                break
            logging.info("Sleeping %ss before next cycle", CHECK_INTERVAL)
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Stopping starter bot")


if __name__ == "__main__":
    run_starter_loop()
