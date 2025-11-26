# 🧪 TheBot - Real Trade Test Plan

## Overview

This document outlines a comprehensive testing procedure to validate TheBot's trading capabilities on a demo MT5 account before deploying to live or VPS environments.

---

## ✅ Pre-Test Checklist

### 1. Environment Setup

- [ ] MT5 terminal installed on your machine
- [ ] MT5 demo account created with your broker
- [ ] Python venv activated: `.venv\Scripts\Activate.ps1`
- [ ] All requirements installed: `pip install -r requirements.txt`
- [ ] `plyer` installed for desktop notifications
- [ ] `.env` file configured with:
  - [ ] `TELEGRAM_BOT_TOKEN` (optional but recommended)
  - [ ] `TELEGRAM_CHAT_ID` (optional but recommended)
  - [ ] `EMAIL_FROM`, `EMAIL_PASSWORD`, `EMAIL_TO` (optional)

### 2. MT5 Configuration

- [ ] Demo account logged in to MT5 terminal
- [ ] Market Watch symbols visible:
  - [ ] FX Vol 20 (or your configured symbols)
  - [ ] FX Vol 40
  - [ ] FX Vol 60
- [ ] MT5 terminal NOT minimized (to see alerts)
- [ ] Journal/Alerts tab visible in MT5

### 3. Bot Configuration (`config.yaml`)

- [ ] `live_trading: false` (start with false for safety)
- [ ] `demo_mode: true`
- [ ] `demo_credentials` populated with demo login details
- [ ] Risk settings reviewed:
  - [ ] `risk_percentage: 1` (start conservative)
  - [ ] `max_loss_percentage: 2`
- [ ] Symbols configured: `['FX Vol 20', 'FX Vol 40', 'FX Vol 60']` or your choice

---

## 🔍 Test Phase 1: Dry-Run Mode (No Real Orders)

### Objective

Verify the bot logic, indicators, and notifications without placing real trades.

### Steps

1. **Run bot in dry-run mode**

   ```powershell
   .venv\Scripts\python.exe TheBot.py --dry-run --once
   ```

2. **Verify output**
   - [ ] No errors or exceptions
   - [ ] All symbols analyzed
   - [ ] Signals generated (BUY/SELL/HOLD)
   - [ ] Log shows indicator values (RSI, MACD, ATR)
   - [ ] MT5 journal appears (check Alerts tab)

3. **Check desktop notifications** (if running on Windows)
   - [ ] Windows notification appears in action center
   - [ ] Sound plays (short beep = success signal)

4. **Expected log output**

   ```
   2025-11-26 10:00:00,123 [INFO] MT5 initialized
   2025-11-26 10:00:00,456 [INFO] FX Vol 20 -> HOLD (adx_low)
   2025-11-26 10:00:02,789 [INFO] Cycle complete
   ```

### Success Criteria

- ✅ No errors or crashes
- ✅ Signals generated for each symbol
- ✅ Notifications triggered (sound + desktop)
- ✅ Log file updated

---

## 🎯 Test Phase 2: Paper Trading Mode (Simulated Orders)

### Objective

Test the full trading workflow with simulated order execution (no real money at risk).

### Steps

1. **Update config.yaml**

   ```yaml
   live_trading: false          # Keep false for paper trading
   demo_mode: true
   paper_trade: true            # Enable simulated fills
   ```

2. **Run bot with once flag**

   ```powershell
   .venv\Scripts\python.exe TheBot.py --once
   ```

3. **Monitor for simulated trades**
   - [ ] Check logs for `[PAPER]` entries
   - [ ] Verify simulated order prices logged
   - [ ] Desktop notification appears: "Trade Executed"
   - [ ] Sound alert plays
   - [ ] MT5 journal shows alert

4. **Verify proposed changes**
   - [ ] `proposed_changes.json` created/updated
   - [ ] Entry contains action, symbol, signal, timestamp

### Success Criteria

- ✅ Paper trades simulated successfully
- ✅ All notification channels triggered
- ✅ Proposed changes logged
- ✅ No actual MT5 orders sent

---

## 🚀 Test Phase 3: Live Demo Trading (Real Orders on Demo Account)

### ⚠️ CRITICAL: Safety Precautions

Before proceeding, verify:

- [ ] You are using a **DEMO** account (NOT live money)
- [ ] Risk per trade is **1% or less** of demo balance
- [ ] Max loss per day is limited to **2-3%** of demo balance
- [ ] You are prepared to **manually close positions** if needed
- [ ] You have read the entire trading logic in `TheBot.py`

### Steps

1. **Enable live trading mode**

   ```yaml
   live_trading: true           # REAL ORDERS ON DEMO
   demo_mode: true
   paper_trade: false           # Disable paper mode
   ```

2. **Run a single cycle**

   ```powershell
   .venv\Scripts\python.exe TheBot.py --once
   ```

3. **Monitor in real-time**
   - [ ] Watch MT5 terminal for new orders
   - [ ] Desktop notification: "Trade Executed" or "Trade Failed"
   - [ ] Sound alert (success = beep, error = lower tone)
   - [ ] Check MT5 Alerts/Journal tab for order confirmation
   - [ ] Verify order ID matches log output

4. **Verify order details in MT5**
   - [ ] Open Positions tab
   - [ ] Confirm symbol, direction (BUY/SELL), entry price, SL, TP
   - [ ] Lot size matches bot calculation (1% risk)

5. **Monitor position**
   - [ ] Watch for SL or TP hit
   - [ ] Check closed position details
   - [ ] Verify P&L calculation

### Success Criteria

- ✅ Order placed and filled on MT5
- ✅ All alerts triggered (journal, desktop, sound)
- ✅ Order details correct (entry, SL, TP, lot)
- ✅ Position closed at SL or TP as expected

---

## 📊 Test Phase 4: Extended Demo Trading (24-Hour Run)

### Objective

Run the bot continuously and validate:

- Long-term stability
- Notification consistency
- Connection maintenance
- Error recovery

### Steps

1. **Prepare for long run**

   ```yaml
   live_trading: true
   check_interval: 60          # Check every 60 seconds
   symbol_delay: 2             # 2-second delay between symbols
   ```

2. **Start bot in background**

   ```powershell
   # Option A: Run in background (PowerShell)
   $job = Start-Job -ScriptBlock {
     cd C:\Users\user\Documents\TheBot.py
     .\.venv\Scripts\Activate.ps1
     python TheBot.py
   }
   
   # Or Option B: Use run_bot_24_7.ps1 script
   .\scripts\run_bot_24_7.ps1
   ```

3. **Monitor every 1-2 hours**
   - [ ] Check bot is still running: `Get-Process python`
   - [ ] Verify log file has recent entries
   - [ ] Check for errors: `Get-Content bot.log -Tail 20`
   - [ ] Confirm positions open/closed as expected
   - [ ] Verify notifications received (Telegram/email)

4. **Stress test: Simulate brief disconnection**
   - [ ] Restart MT5 terminal mid-run
   - [ ] Verify bot attempts reconnection
   - [ ] Check logs for reconnection messages
   - [ ] Confirm trading resumes after reconnection

5. **Manual intervention drill**
   - [ ] Manually close a position in MT5
   - [ ] Verify bot detects closed position
   - [ ] Confirm bot continues to trade other symbols

### Success Criteria

- ✅ Bot runs for 24+ hours without crash
- ✅ Reconnection logic works
- ✅ Multiple trades executed successfully
- ✅ All notifications sent consistently
- ✅ Error recovery functioning

---

## 🔐 Test Phase 5: Risk Management Validation

### Objective

Verify risk controls are working correctly.

### Steps

1. **Verify lot sizing**
   - [ ] Calculate expected lot: `(balance * 0.01) / (entry - SL)`
   - [ ] Compare with bot's executed lot
   - [ ] Verify they match (within 0.01 lot rounding)

2. **Check stop loss effectiveness**
   - [ ] Place manual BUY order
   - [ ] Set SL below entry
   - [ ] Wait for SL to be hit
   - [ ] Verify closed at SL price (allow ±5 pips for slippage)
   - [ ] Check P&L = -(SL distance) *lot* point value

3. **Validate daily loss limit**
   - [ ] Simulate losing trades
   - [ ] Verify bot stops trading after `max_loss_percentage` hit
   - [ ] Check for warning alert in logs

4. **Test maximum drawdown**
   - [ ] Monitor equity curve from `performance_log.csv`
   - [ ] Verify drawdown doesn't exceed configured limits

### Success Criteria

- ✅ Lot sizes calculated correctly
- ✅ SL exits at correct price
- ✅ P&L matches manual calculation
- ✅ Daily loss limit enforced

---

## 📱 Test Phase 6: Notification Validation

### Objective

Verify all notification channels work reliably.

### Steps

1. **MT5 Journal Alerts**
   - [ ] Open MT5 > Terminal > Alerts tab
   - [ ] Run bot: `.venv\Scripts\python.exe TheBot.py --once`
   - [ ] Verify alert appears: "Trade Executed: [SYMBOL] @ [PRICE]"

2. **Desktop Notifications** (Windows)
   - [ ] Run bot
   - [ ] Check Windows notification appears (top-right corner)
   - [ ] Message includes: symbol, signal, entry price

3. **Sound Alerts**
   - [ ] Success signal: "beep" (high-pitched, short)
   - [ ] Error signal: "lower tone" (low-pitched, longer)
   - [ ] Verify volume is audible

4. **Telegram Alerts** (if configured)
   - [ ] Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
   - [ ] Run bot: `.venv\Scripts\python.exe TheBot.py --once`
   - [ ] Check Telegram app for formatted message:

     ```
     ════════════════════════════════════════
     📊 TRADE ALERT
     ════════════════════════════════════════
     Signal: BUY [SYMBOL]
     Entry Price: 1.08500
     Stop Loss: 1.08400
     Take Profit: 1.08600
     Lot Size: 0.10
     Order #: 12345
     ════════════════════════════════════════
     ```

5. **Email Alerts** (if configured)
   - [ ] Set `EMAIL_FROM`, `EMAIL_PASSWORD`, `EMAIL_TO` in `.env`
   - [ ] Use Gmail app password (not account password)
   - [ ] Run bot
   - [ ] Check email inbox for HTML-formatted alert

### Success Criteria

- ✅ All notification channels triggered
- ✅ Messages contain complete trade info
- ✅ Notifications received within 5 seconds
- ✅ No failed deliveries

---

## 🐛 Debugging Checklist

If tests fail, check:

### No orders placed

```powershell
# 1. Check if live_trading is enabled
Get-Content config.yaml | Select-String "live_trading"

# 2. Check MT5 connection
python -c "import MetaTrader5 as mt5; print(mt5.initialize())"

# 3. Check symbol availability
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.symbol_info('FX Vol 20'))"

# 4. Review bot logs
Get-Content bot.log -Tail 50
```

### Notifications not received

```powershell
# Check Telegram config
$env:TELEGRAM_BOT_TOKEN
$env:TELEGRAM_CHAT_ID

# Test Telegram manually
curl -X POST "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/sendMessage" `
  -d "chat_id=$env:TELEGRAM_CHAT_ID&text=test"

# Check Email config
$env:EMAIL_FROM
$env:EMAIL_PASSWORD
```

### MT5 connection lost

```powershell
# Restart MT5 terminal
# Check MT5 logs: C:\Users\[username]\AppData\Roaming\MetaQuotes\Terminal\[ID]\logs\

# Verify reconnection in bot logs
Get-Content bot.log | Select-String "reconnect"
```

---

## 📋 Test Completion Checklist

After completing all phases, verify:

- [ ] Dry-run mode: ✅ No errors
- [ ] Paper trading: ✅ Simulated fills work
- [ ] Demo trading: ✅ Real orders placed successfully
- [ ] 24-hour run: ✅ Stable operation
- [ ] Risk management: ✅ SL/TP working
- [ ] Notifications: ✅ All channels working
- [ ] Debugging: ✅ Log analysis correct

---

## 🎬 Ready for VPS Deployment

Once all tests pass:

1. **Document demo results**
   - [ ] Save performance_log.csv
   - [ ] Screenshot successful trades
   - [ ] Note any issues and fixes

2. **Prepare for VPS**
   - [ ] Follow `VPS_DEPLOYMENT.md`
   - [ ] Set up Windows VPS
   - [ ] Configure Task Scheduler / NSSM
   - [ ] Enable monitoring/alerts

3. **Pre-VPS safety checklist**
   - [ ] Risk percentage is conservative (1%)
   - [ ] Max daily loss is small (2-3%)
   - [ ] All notifications configured
   - [ ] Emergency stop procedure documented
   - [ ] Manual trade closure tested

---

## 📞 Troubleshooting

### "ModuleNotFoundError: No module named 'MetaTrader5'"

```powershell
pip install MetaTrader5
```

### "Symbol not found on MT5"

- Check MT5 Market Watch (Ctrl+M)
- Add symbol or use configured aliases in `config.yaml`
- Check `symbol_aliases` mapping

### "Order rejected: insufficient balance"

- Increase demo account balance
- Reduce risk percentage in config
- Check lot size calculation: `echo (balance * 0.01) / (entry - sl)`

### "Telegram/Email not sending"

- Verify `.env` file exists
- Check credentials are correct
- For Gmail: use app password, not account password
- For Telegram: verify bot token and chat ID

---

**Last Updated**: 2025-11-26  
**Version**: 1.0  
**Status**: Ready for Testing
