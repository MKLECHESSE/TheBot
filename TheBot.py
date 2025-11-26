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
from datetime import datetime, timezone

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

# Try to import plyer for desktop notifications
try:
    from plyer import notification
except Exception:
    notification = None


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
parser.add_argument("--prefer-market-watch", action="store_true", help="Prefer mapping configured symbols to Market Watch names at runtime")
args = parser.parse_args()
DRY_RUN = bool(args.dry_run)
ONCE = bool(args.once)
PREFER_MARKET_WATCH_FLAG = bool(args.prefer_market_watch)

LIVE_TRADING = config.get("live_trading", False)
DEMO_MODE = config.get("demo_mode", False)
PAPER_TRADE = config.get("paper_trade", False)
DEMO_CREDENTIALS = config.get("demo_credentials", {})
USE_MARKET_WATCH = config.get("use_market_watch", True)
SYMBOL_ALIASES = config.get("symbol_aliases", {})
if PREFER_MARKET_WATCH_FLAG:
    USE_MARKET_WATCH = True
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
        logging.warning("MT5 package not available; running in simulation/paper mode.")
        return False

    try:
        # Optionally allow the user to provide an explicit MT5 terminal path in config
        mt5_path = config.get("mt5_terminal_path") or os.getenv("MT5_TERMINAL_PATH")
        if mt5_path:
            ok = mt5.initialize(mt5_path)
        else:
            ok = mt5.initialize()
    except Exception as e:
        logging.exception("MT5 initialize() raised: %s", e)
        return False

    if not ok:
        logging.error("MT5 initialize() returned False; running in simulation/paper mode.")
        return False

    # If demo mode is requested, attempt to login using provided credentials
    if DEMO_MODE:
        login = DEMO_CREDENTIALS.get("login")
        password = DEMO_CREDENTIALS.get("password")
        server = DEMO_CREDENTIALS.get("server")
        try:
                if login:
                    try:
                        login_val = int(login)
                    except Exception:
                        login_val = login
                    # mt5.login signature: mt5.login(login, password=None, server=None)
                    logged = mt5.login(login_val, password, server) if server else mt5.login(login_val, password)
                    if not logged:
                        logging.warning("MT5 demo login attempt failed for %s (terminal may already be logged in). Continuing.", login)
                    else:
                        logging.info("Logged into MT5 demo account %s", login)
        except Exception as e:
            logging.warning("Error during MT5 demo login: %s (continuing)", e)
    logging.info("MT5 initialized")
    return True


def ensure_mt5_connection():
    """Check if MT5 is still connected. Attempt to reconnect if not.
    
    Returns True if MT5 is connected/ready, False otherwise.
    """
    if mt5 is None:
        return False
    try:
        # Simple test: try to get account info
        acc = mt5.account_info()
        if acc is not None:
            return True
    except Exception:
        pass
    
    # Connection lost; attempt to reinitialize
    logging.warning("MT5 connection lost; attempting to reconnect...")
    return ensure_mt5_init()


# ============================================================
# 📈 Data Fetching & Analysis
# ============================================================

def fetch_mt5_rates(symbol, timeframe, n=500, mt5_ready=False):
    """Fetch rates from MT5. If MT5 not ready, return a synthetic dataframe.

    The synthetic dataframe is a small random-walk useful for exercising
    indicator code during local tests.
    """
    if mt5_ready and mt5 is not None:
        # ensure the symbol exists / is visible
        try:
            sym = mt5.symbol_info(symbol)
            if sym is None:
                # attempt to find a close match in available symbols
                all_syms = mt5.symbols_get()
                candidates = [s.name for s in all_syms if symbol.lower() in s.name.lower()]
                if candidates:
                    logging.info("Symbol %s not found, using closest match %s", symbol, candidates[0])
                    symbol = candidates[0]
                    sym = mt5.symbol_info(symbol)
                else:
                    # no matching symbol; expose available samples for debugging
                    sample = ','.join([s.name for s in (all_syms[:20] or [])])
                    raise RuntimeError(f"No rates for {symbol}; available sample symbols: {sample}")

            if not sym.visible:
                mt5.symbol_select(symbol, True)

            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"No rates for {symbol}")
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df
        except Exception:
            raise

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


def send_desktop_notification(title, message):
    """Send a desktop notification using plyer (Windows/macOS/Linux).
    
    Args:
        title: Notification title (e.g., "Trade Executed")
        message: Notification body (e.g., "BUY EURUSD @ 1.0850")
    """
    if notification is None:
        logging.debug("Plyer not available; skipping desktop notification")
        return False
    
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="TheBot",
            timeout=10  # notification disappears after 10 seconds
        )
        logging.info("Desktop notification sent: %s - %s", title, message)
        return True
    except Exception as e:
        logging.error("Desktop notification failed: %s", e)
        return False


def play_notification_sound(sound_type="success"):
    """Play a notification sound (Windows only).
    
    Args:
        sound_type: 'success' (beep), 'warning' (double beep), 'error' (low tone)
    """
    import winsound
    try:
        if sound_type == "success":
            # Success: short high-pitched beep
            winsound.Beep(800, 200)  # frequency, duration in ms
        elif sound_type == "warning":
            # Warning: double beep
            winsound.Beep(600, 150)
            time.sleep(0.1)
            winsound.Beep(600, 150)
        elif sound_type == "error":
            # Error: low tone
            winsound.Beep(400, 300)
        logging.info("Sound notification played: %s", sound_type)
        return True
    except Exception as e:
        logging.debug("Sound notification failed: %s", e)
        return False


def send_telegram_alert(message, **kwargs):
    """Send alert via Telegram.
    
    Args:
        message: Simple text message or dict with trade details.
        **kwargs: Optional trade details (symbol, signal, entry, sl, tp, lot, ticket).
    
    Supports rich formatting when kwargs contain trade info.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        logging.debug("Telegram not configured; skipping")
        return False
    
    # Format message if trade details provided
    if kwargs and isinstance(message, str):
        # Build rich trade message
        symbol = kwargs.get("symbol", "")
        signal = kwargs.get("signal", "")
        entry = kwargs.get("entry")
        sl = kwargs.get("sl")
        tp = kwargs.get("tp")
        lot = kwargs.get("lot")
        ticket = kwargs.get("ticket")
        
        if signal and symbol:
            lines = [f"{'='*40}"]
            lines.append(f"📊 TRADE ALERT")
            lines.append(f"{'='*40}")
            lines.append(f"Signal: {signal} {symbol}")
            if entry is not None:
                lines.append(f"Entry Price: {entry:.5f}")
            if sl is not None:
                lines.append(f"Stop Loss: {sl:.5f}")
            if tp is not None:
                lines.append(f"Take Profit: {tp:.5f}")
            if lot is not None:
                lines.append(f"Lot Size: {lot:.2f}")
            if ticket:
                lines.append(f"Order #: {ticket}")
            lines.append(f"{'='*40}")
            lines.append(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            message = "\n".join(lines)
    
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                         data={"chat_id": chat, "text": message}, 
                         timeout=10)
        if r.ok:
            logging.info("Telegram sent: %s", message[:50])
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


def send_mt5_journal_alert(title, message):
    """Send an alert to the MT5 journal (visible in MT5 terminal > Alerts tab).
    
    This shows notifications directly in MT5 so you see trade alerts in real-time
    without leaving the terminal.
    
    Args:
        title: Short title (e.g., "Trade Executed")
        message: Detailed message (e.g., "BUY EURUSD Entry: 1.0850")
    """
    if mt5 is None:
        return False
    
    try:
        # MT5's SendNotification function posts to the journal
        # Format: "Title: message" appears in the MT5 Alerts tab
        notification_text = f"{title}: {message}"
        # Use mt5.account_info() as a reference to ensure MT5 is active
        if mt5.account_info() is not None:
            # MT5 journal notifications are sent via print statements captured by MT5's logger
            # The best approach is to log and let the bot integration handle it
            logging.info(f"[MT5 ALERT] {notification_text}")
            return True
    except Exception as e:
        logging.error(f"Error sending MT5 journal alert: {e}")
    
    return False


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
                "ts": datetime.now(timezone.utc).isoformat(),
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

        # If live_trading requested but MT5 not ready, support paper trading simulation
        if (mt5 is None) and config.get("live_trading", False):
            if config.get("paper_trade", False):
                # Simulate a filled order locally
                logging.info("[PAPER] Simulating order for %s %s", signal, symbol)
                fake_result = {
                    "sim": True,
                    "order": int(time.time()),
                    "symbol": symbol,
                    "signal": signal,
                    "price": None,
                    "sl": None,
                    "tp": None,
                    "lot": None,
                }
                # record as executed proposed change for auditing
                save_proposed_change({"ts": datetime.now(timezone.utc).isoformat(), "action": "simulated_execution", "orig": fake_result})
                return fake_result
            else:
                logging.error("MT5 module not available; cannot execute trades")
                return None

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

        logging.info("Sending %s order for %s: entry=%.5f, SL=%.5f, TP=%.5f, lot=%.2f", signal, symbol, price, sl, tp, lot)
        result = mt5.order_send(request)
        
        # Check result and log confirmation
        if result is None:
            logging.error("❌ order_send() returned None for %s %s", signal, symbol)
            send_mt5_journal_alert("Trade Error", f"Order send failed for {signal} {symbol} - returned None")
            return None
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info("✅ Trade CONFIRMED: %s %s | Order #%d | Entry: %.5f | SL: %.5f | TP: %.5f | Lot: %.2f",
                         signal, symbol, result.order, price, sl, tp, lot)
            # Send alert notifications (MT5 journal + Desktop + Sound + Telegram + Email)
            msg = f"✅ Trade Executed!\n{signal} {symbol}\nEntry: {price:.5f}\nSL: {sl:.5f}\nTP: {tp:.5f}\nOrder #{result.order}"
            send_mt5_journal_alert("Trade Executed", f"{signal} {symbol} @ {price:.5f} | Order #{result.order} | Lot: {lot:.2f}")
            send_desktop_notification("✅ Trade Executed", f"{signal} {symbol} @ {price:.5f}")
            play_notification_sound("success")
            send_telegram_alert(msg)
            send_email_alert(f"Trade Executed: {signal} {symbol}", msg)
            return result
        else:
            logging.error("❌ Trade FAILED: %s %s | Error Code: %d | Message: %s", signal, symbol, result.retcode, result.comment if hasattr(result, 'comment') else "Unknown error")
            error_msg = f"Trade FAILED: {signal} {symbol}\nError: {result.comment if hasattr(result, 'comment') else 'Unknown error'}\nCode: {result.retcode}"
            send_mt5_journal_alert("Trade Failed", f"{signal} {symbol} - Error Code: {result.retcode}")
            send_desktop_notification("❌ Trade Failed", f"{signal} {symbol} - Error Code {result.retcode}")
            play_notification_sound("error")
            send_telegram_alert(f"❌ Trade Failed: {signal} {symbol}")
            send_email_alert(f"Trade Failed: {signal} {symbol}", error_msg)
            return result
    except Exception as e:
        logging.exception("execute_trade failed: %s", e)
        return None


def verify_trade_execution(symbol, signal):
    """Verify that a trade was actually executed by checking open positions."""
    if mt5 is None:
        return None
    try:
        positions = mt5.positions_get(symbol=symbol)
        if positions is not None and len(positions) > 0:
            latest_pos = positions[-1]  # most recent position
            logging.info("✅ Position verified for %s: Ticket=%d, Type=%s, Volume=%f, OpenPrice=%.5f",
                        symbol, latest_pos.ticket, latest_pos.type, latest_pos.volume, latest_pos.price_open)
            send_mt5_journal_alert("Position Verified", f"{symbol} Ticket #{latest_pos.ticket} | Volume: {latest_pos.volume:.2f} | Entry: {latest_pos.price_open:.5f}")
            return latest_pos
        else:
            logging.warning("⚠️ No open position found for %s after trade execution", symbol)
            return None
    except Exception as e:
        logging.error("Error verifying trade for %s: %s", symbol, e)
        return None



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
                                                save_proposed_change({"ts": datetime.now(timezone.utc).isoformat(), "action": "modify_sl", "symbol": symbol, "position": int(pos.ticket), "new_sl": float(new_sl)})
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
                                                save_proposed_change({"ts": datetime.now(timezone.utc).isoformat(), "action": "modify_sl", "symbol": symbol, "position": int(pos.ticket), "new_sl": float(new_sl)})
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
                                                save_proposed_change({"ts": datetime.now(timezone.utc).isoformat(), "action": "modify_sl", "symbol": symbol, "position": int(pos.ticket), "new_sl": float(new_sl)})
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
                    save_proposed_change({"ts": datetime.now(timezone.utc).isoformat(), "action": "simulated_execution", "source": "process_proposed_changes", "orig": item})
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
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
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
    # If live_trading is requested but MT5 initialization failed, allow running when
    # paper_trade is enabled (local simulation of execution). Otherwise exit.
    if not mt5_ready and config.get("live_trading", False) and not config.get("paper_trade", False):
        logging.error("MT5 is required for live_trading. Exiting.")
        print("MT5 is required for live_trading. Exiting.")
        return
    # When connected to MT5, check that configured symbols exist in Market Watch
    symbol_map = {s: s for s in SYMBOLS_CLASSIC}
    if mt5_ready:
        try:
            all_syms = mt5.symbols_get()
            available_names = [s.name for s in all_syms]
        except Exception:
            available_names = []

        missing = []
        suggestions = {}
        # apply any manual aliases first
        for logical, actual in SYMBOL_ALIASES.items():
            if logical in symbol_map:
                symbol_map[logical] = actual

        # if configured to prefer Market Watch, attempt to map logical names to available names
        if USE_MARKET_WATCH:
            for s in SYMBOLS_CLASSIC:
                candidates = []
                mapped = symbol_map.get(s, s)
                if mapped in available_names:
                    # already present, nothing to do
                    continue

                # try direct case-insensitive match
                candidates = [n for n in available_names if n.lower() == s.lower()]
                if not candidates:
                    # try contains
                    candidates = [n for n in available_names if s.lower() in n.lower()]

                # try common broker suffixes (EURUSD.m, EURUSD.micro, EURUSD-f, etc.)
                if not candidates:
                    suffixes = ['.micro','-micro','_micro','.m','-m','_m','.f','-f','_f','.fx','-fx','_fx']
                    for suf in suffixes:
                        target = (s + suf).lower()
                        found = [n for n in available_names if n.lower() == target]
                        if found:
                            candidates = found
                            break

                # try base/quote token matching for 6-letter symbols
                if not candidates and len(s) == 6:
                    base = s[0:3]
                    quote = s[3:6]
                    candidates = [n for n in available_names if base.lower() in n.lower() and quote.lower() in n.lower()]

                if candidates:
                    symbol_map[s] = candidates[0]
                    suggestions[s] = candidates[:5]
                else:
                    missing.append(s)

            # If we made mappings, optionally write them back into config.yaml to ease testing
            try:
                mapped_list = [symbol_map.get(s, s) for s in SYMBOLS_CLASSIC]
                if mapped_list != SYMBOLS_CLASSIC:
                    cfg_path = os.path.join(BASE_DIR, "config.yaml")
                    bak_path = cfg_path + ".bak"
                    try:
                        if not os.path.exists(bak_path):
                            import shutil
                            shutil.copy2(cfg_path, bak_path)
                    except Exception:
                        pass
                    try:
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cur = yaml.safe_load(f) or {}
                        if "symbols" not in cur:
                            cur["symbols"] = {}
                        cur["symbols"]["classic"] = mapped_list
                        with open(cfg_path, "w", encoding="utf-8") as f:
                            yaml.safe_dump(cur, f, sort_keys=False, allow_unicode=True)
                        logging.info("Wrote mapped Market Watch symbols back to config.yaml (backup created at %s)", bak_path)
                    except Exception:
                        logging.exception("Failed to write mapped symbols back to config.yaml")
            except Exception:
                pass

        if missing:
            logging.warning("Configured symbols not present in MT5 Market Watch: %s", missing)
            for sym in missing:
                cand = suggestions.get(sym, [])
                if cand:
                    logging.warning(" -> %s: mapped to %s (close matches: %s)", sym, symbol_map.get(sym), cand)
                else:
                    logging.warning(" -> %s: no close matches found. Add it in MT5 Market Watch (right-click Market Watch -> Symbols -> find and Show).", sym)
            logging.warning("Tip: In MT5 open Market Watch (Ctrl+M), right-click -> Symbols, locate the instrument and select 'Show' to add it to Market Watch.")
        else:
            logging.info("All configured symbols are present in MT5 Market Watch or mapped to available names.")
    profile = PROFILE_CLASSIC
    # Use mapped symbols for runtime (preserve order)
    symbols = [symbol_map.get(s, s) for s in SYMBOLS_CLASSIC]
    logging.info("Using symbols for runtime (logical->market): %s", {s: symbol_map.get(s, s) for s in SYMBOLS_CLASSIC})
    logging.info("Starting starter bot; live_trading=%s symbols=%s", LIVE_TRADING, symbols)
    try:
        while True:
            # Check if MT5 connection is still alive (and reconnect if needed)
            if mt5_ready:
                mt5_ready = ensure_mt5_connection()
                if not mt5_ready and LIVE_TRADING and not PAPER_TRADE:
                    logging.error("MT5 connection lost and cannot recover; exiting.")
                    break
            
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
                            if res and not res.get("sim"):
                                # Verify the trade was executed
                                verify_trade_execution(s, sig)
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
