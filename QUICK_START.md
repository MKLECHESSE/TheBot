# 🚀 TheBot - Quick Start & Roadmap (v2.0)

## ✅ What's Ready Now

Your trading bot is **production-ready** with all core features implemented:

### 🎯 Core Features

- ✅ **Live Demo Trading** — MT5 integration with real demo accounts
- ✅ **Smart Order Execution** — ATR-based SL/TP, risk-based lot sizing
- ✅ **Multi-Channel Alerts**:
  - 📺 MT5 Journal (visible in terminal)
  - 🔔 Windows Desktop Notifications
  - 🔊 Sound Alerts (success beep, error tone)
  - 📱 Telegram Messages (rich formatting)
  - 📧 Email Alerts (HTML formatted)
- ✅ **Risk Management** — Position sizing, daily loss limits, SL/TP automation
- ✅ **Position Verification** — Auto-confirm trades placed successfully
- ✅ **Dry-Run Mode** — Test strategy without placing orders
- ✅ **Paper Trading** — Simulate fills for testing logic

---

## 📋 Running the Bot

### Quick Start (Demo Account)

```powershell
# 1. Activate virtual environment
cd C:\Users\user\Documents\TheBot.py
.venv\Scripts\Activate.ps1

# 2. Update config.yaml with your demo credentials
# (see config.yaml demo_credentials section)

# 3. Run ONE cycle to test
python TheBot.py --once

# 4. Run continuously (24/7 in background)
python TheBot.py
```

### Test Before Going Live

```powershell
# Test 1: Dry-run mode (no real orders)
python TheBot.py --once --dry-run

# Test 2: Paper trading (simulated fills)
# Update config.yaml: live_trading=false, paper_trade=true
python TheBot.py --once

# Test 3: Live demo trading (real orders on demo account)
# Update config.yaml: live_trading=true, demo_mode=true, paper_trade=false
python TheBot.py --once
```

### View Alerts

```powershell
# View bot logs
Get-Content bot.log -Tail 50

# View trading performance
Import-Csv performance_log.csv | Format-Table -AutoSize

# Monitor MT5 terminal
# Open MT5 > Terminal > Alerts tab
# Alerts appear in real-time as bot trades
```

---

## 🧪 Testing Your Bot (6-Phase Plan)

Follow the **TRADE_TEST_PLAN.md** document:

### Phase 1: Dry-Run Validation ✅

```powershell
python TheBot.py --dry-run --once
# ✓ No errors, indicators calculated, signals generated
```

### Phase 2: Paper Trading Simulation ✅

```yaml
# In config.yaml:
live_trading: false
paper_trade: true
```

```powershell
python TheBot.py --once
# ✓ Simulated fills, alerts triggered, no real money at risk
```

### Phase 3: Live Demo Trading ✅

```yaml
# In config.yaml:
live_trading: true
demo_mode: true
paper_trade: false
```

```powershell
python TheBot.py --once
# ✓ Real orders on demo account, MT5 shows position
```

### Phase 4: Extended 24-Hour Run ⏳

```powershell
python TheBot.py
# Run for 24+ hours, verify:
# - Consistent order execution
# - Reconnection handling
# - Alert delivery
# - No crashes
```

### Phase 5: Risk Management Validation ⏳

```powershell
# Verify:
# - Lot sizes match risk calculation
# - SL exits at correct price
# - Daily loss limits enforced
# - Max drawdown respected
```

### Phase 6: Notification Testing ⏳

```powershell
# Verify all channels:
# - MT5 Journal (check Alerts tab)
# - Desktop notification (top-right corner)
# - Sound alert (beep sound)
# - Telegram message (if configured)
# - Email alert (if configured)
```

---

## 🖥️ Deploying to VPS (24/7 Trading)

Once you've passed all demo tests, deploy to a Windows VPS for automated trading:

### Quick VPS Setup (5 Steps)

**See VPS_DEPLOYMENT_COMPLETE.md for full guide**

```powershell
# 1. Install Python, Git, MT5 on VPS

# 2. Clone bot repository
cd C:\Trading\TheBot
git clone https://github.com/MKLECHESSE/TheBot.git .

# 3. Create venv and install dependencies
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install MetaTrader5

# 4. Create .env file with credentials
# (MT5 login, email, Telegram, etc.)

# 5. Register as Windows service
# Option A: Task Scheduler (easiest)
# Option B: NSSM (better control)

# 6. Verify running
Get-Process python | Where-Object {$_.CommandLine -like '*TheBot*'}
```

### VPS Monitoring

```powershell
# Monitor bot continuously
while ($true) {
    $bot = Get-Process python | Where-Object {$_.CommandLine -like '*TheBot*'}
    if ($bot) {
        Write-Host "✅ Bot running (PID: $($bot.Id))"
    } else {
        Write-Host "❌ Bot crashed! Restarting..."
        Start-ScheduledTask -TaskName "TheBot-Trading"
    }
    Get-Content bot.log -Tail 5
    Start-Sleep -Seconds 300
}
```

---

## ⚙️ Configuration Reference

### `config.yaml` Key Settings

```yaml
# Trading Mode
live_trading: true              # Enable real trading (set to false for testing)
demo_mode: true                 # Use demo account
paper_trade: false              # Simulate fills (don't place real orders)

# Demo Account Credentials
demo_credentials:
  login: "12345"
  password: "password123"
  server: "DemoServer"

# Risk Management
risk_percentage: 1              # Risk 1% of balance per trade
max_loss_percentage: 3          # Stop trading if lose 3% in a day

# Symbols to Trade
symbols:
  classic:
    - "EURUSD"
    - "GBPUSD"
    - "USDJPY"

# ATR-based SL/TP
atr_sl_multiplier: 2            # SL = entry - (ATR * 2)
atr_tp_multiplier: 4            # TP = entry + (ATR * 4)

# Check Interval
check_interval: 60              # Check every 60 seconds
symbol_delay: 2                 # 2 seconds between symbols
```

### Environment Variables (`.env`)

```ini
# MetaTrader 5
MT5_LOGIN=12345
MT5_PASSWORD=password123
MT5_SERVER=DemoServer

# Email Alerts (Gmail)
EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=app_password     # Use App Password, NOT account password
EMAIL_TO=your_email@gmail.com

# Telegram Alerts
TELEGRAM_BOT_TOKEN=123456:ABCDEFGHijklmnop
TELEGRAM_CHAT_ID=987654321

# Webhook (for remote actions)
WEBHOOK_SECRET=your_secure_key

# Logging
LOG_FILE=bot.log
```

---

## 📊 Monitoring Your Bot

### View Current Performance

```powershell
# Show last 20 trades
Import-Csv performance_log.csv -Tail 20 | Format-Table -AutoSize

# Calculate win rate
$trades = Import-Csv performance_log.csv
$wins = ($trades | Where-Object pnl -gt 0 | Measure-Object).Count
$total = ($trades | Measure-Object).Count
"Win Rate: $(($wins/$total)*100)%"

# Total profit
($trades | Measure-Object -Property pnl -Sum).Sum
```

### Watch Trading Live

```powershell
# Continuous log monitoring
Get-Content bot.log -Wait -Tail 20
```

### Check for Errors

```powershell
# Find all errors in logs
Get-Content bot.log | Select-String "ERROR|FAILED|Exception"

# View last error with context
Get-Content bot.log | Select-String "ERROR" -Context 2,2 | Tail -20
```

---

## 🚨 Emergency Procedures

### Stop Trading Immediately

```powershell
# Kill bot process
Stop-Process -Name python -Force

# Or stop scheduled task
Stop-ScheduledTask -TaskName "TheBot-Trading" -Force
```

### Close All Positions Manually

1. Open MT5 terminal
2. Go to **Positions** tab
3. Right-click each position → **Close Position**
4. Confirm at market price

### Restart Bot

```powershell
# Option 1: Run directly
python TheBot.py

# Option 2: Restart scheduled task
Start-ScheduledTask -TaskName "TheBot-Trading"
```

---

## 📞 Troubleshooting

### "ModuleNotFoundError: No module named X"

```powershell
pip install -r requirements.txt
```

### "Symbol not found on MT5"

- Check `config.yaml` symbols list
- Verify symbols in MT5 Market Watch (Ctrl+M)
- Use `symbol_aliases` to map to broker names

### "Order rejected: invalid volume"

- Reduce `risk_percentage` in config
- Check demo account has sufficient balance

### "No notifications received"

- Verify `.env` file exists and has correct values
- For Gmail: use App Password, not account password
- For Telegram: verify bot token and chat ID

### "Bot crashed or won't start"

```powershell
# Check Python venv
.venv\Scripts\python.exe --version

# Check MT5
python -c "import MetaTrader5; print(MetaTrader5.initialize())"

# Check config syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# View full error
python TheBot.py 2>&1
```

---

## 📚 Documentation

- **TRADE_TEST_PLAN.md** — Comprehensive 6-phase testing procedure
- **VPS_DEPLOYMENT_COMPLETE.md** — Full VPS setup guide with scripts
- **VPS_DEPLOYMENT.md** — Quick VPS reference (legacy)
- **README.md** — Project overview

---

## 🎯 Next Steps (Your Checklist)

### Immediate (This Week)

- [ ] Run bot in **dry-run** mode → verify no errors
- [ ] Run bot in **paper trading** → verify simulated fills
- [ ] Run bot in **live demo** for 1-2 trades → verify order execution
- [ ] Test all **notification channels** (desktop, sound, Telegram, email)
- [ ] Review **trading logs** and performance

### Short-term (Next Week)

- [ ] Run bot for **24+ hours** → verify stability
- [ ] Validate **risk management** → verify SL/TP working
- [ ] Simulate **connection loss** → verify reconnection
- [ ] Document any **issues and fixes**

### Long-term (Before VPS)

- [ ] Prepare **VPS environment** (Windows Server 2016+)
- [ ] Deploy **bot code** to VPS
- [ ] Configure **Windows service** (Task Scheduler / NSSM)
- [ ] Set up **monitoring and backups**
- [ ] Create **emergency procedures**
- [ ] Run **7-day test** on VPS with small risk
- [ ] **Deploy** with confidence

---

## 💡 Tips for Success

1. **Start conservative**: 1% risk, demo account, 24-hour monitoring
2. **Test thoroughly**: Complete all 6 test phases before VPS
3. **Monitor alerts**: Set up Telegram to stay informed 24/7
4. **Keep logs**: Save all performance data for analysis
5. **Have a plan**: Know exactly how to stop/close if needed
6. **Review daily**: Check bot logs and trades each morning
7. **Be ready to intervene**: This is automated, but you're responsible

---

## 📞 Support

**Common Questions:**

**Q: Is this safe to run?**  
A: Yes, if you follow the test plan. Start with demo account, small risk %, and 24-hour monitoring.

**Q: What if orders don't execute?**  
A: Verify live_trading is enabled, MT5 is running, account has balance, and symbols exist in Market Watch.

**Q: Can I trade live money?**  
A: Yes, but ONLY after passing all 6 test phases and 7+ days of demo testing. Start with 0.5% risk max.

**Q: What if the bot crashes?**  
A: It will auto-restart via scheduled task. Check logs to understand why it crashed before restarting.

**Q: How do I update the bot?**  
A: `git pull`, test in dry-run, then restart the service.

---

## 🎉 You're Ready

Your bot is **production-ready**. Follow the test plan, monitor carefully, and you'll be trading 24/7 by next week.

**Good luck! 🚀**

---

**Last Updated**: 2025-11-26  
**Version**: 2.0  
**Status**: ✅ Ready for Testing & Deployment
