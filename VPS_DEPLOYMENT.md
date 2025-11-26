# TheBot - VPS Deployment Guide (Windows)

This guide covers deploying and running TheBot 24/7 on a Windows Virtual Private Server (VPS).

## Prerequisites

- Windows Server 2016 or later
- Python 3.11+
- Git
- MetaTrader 5 installed on the VPS (requires a trading account)
- Administrator access to the VPS

## Step 1: Prepare the VPS

### 1.1 Install Python

```powershell
# Download and install Python 3.12 from https://www.python.org/downloads/
# Or use winget (Windows Package Manager)
winget install Python.Python.3.12
```

### 1.2 Install Git

```powershell
winget install Git.Git
```

### 1.3 Install MetaTrader 5

Download MetaTrader 5 from your broker's website and install on the VPS. Configure your trading account credentials.

## Step 2: Clone and Setup TheBot

```powershell
# Navigate to a working directory
cd C:\Trading

# Clone the repository
git clone https://github.com/MKLECHESSE/TheBot.git
cd TheBot

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install MetaTrader5
```

## Step 3: Configure TheBot

### 3.1 Set Environment Variables

Create a `.env` file in the bot directory with your broker details and alert credentials:

```ini
# MetaTrader 5
MT5_LOGIN=your_demo_login
MT5_PASSWORD=your_demo_password
MT5_SERVER=DemoServerName

# Email Alerts (Gmail recommended)
EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO=recipient@example.com

# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Webhook (for remote actions)
WEBHOOK_SECRET=your_secret_key
```

**Note**: For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your account password.

### 3.2 Update config.yaml

Edit `config.yaml` to configure:

```yaml
live_trading: true
demo_mode: true
paper_trade: false

demo_credentials:
  login: "your_demo_login"
  password: "your_demo_password"
  server: "DemoServerName"

# Your trading symbols
symbols:
  classic:
    - "EURUSD"
    - "GBPUSD"
    - "USDJPY"

# Risk settings
risk_percentage: 1
max_loss_percentage: 2
```

## Step 4: Run TheBot as a Windows Service

### 4.1 Option A: Using Windows Task Scheduler (Recommended)

This approach is simpler and doesn't require additional software.

1. Open Windows Task Scheduler
2. Create a new task:
   - **Name**: TheBot Trading Bot
   - **Trigger**: On startup / Recurring daily at 8:00 AM
   - **Action**:

    ```text
    Program/script: C:\Trading\TheBot\.venv\Scripts\python.exe
    Add arguments: C:\Trading\TheBot\TheBot.py
    Start in: C:\Trading\TheBot
    ```

   - **Conditions**: Configure to run on power-on, don't stop on battery
   - **Settings**: Allow task to run on demand, run with highest privileges

### 4.2 Option B: Using NSSM (Non-Sucking Service Manager)

```powershell
# Download and install NSSM
# From: https://nssm.cc/download

# Register TheBot as a Windows Service
nssm install TheBot C:\Trading\TheBot\.venv\Scripts\python.exe C:\Trading\TheBot\TheBot.py

# Start the service
nssm start TheBot

# View service logs
nssm get TheBot AppDirectory
nssm get TheBot AppStdout
```

### 4.3 Option C: Using PowerShell Script with Auto-Restart

Use the provided `scripts/run_bot_24_7.ps1` script:

```powershell
# Run in PowerShell as Administrator
.\'scripts\run_bot_24_7.ps1'
```

This script will:

- Monitor the bot process
- Automatically restart on failure
- Log output to a file
- Run indefinitely

## Step 5: Monitor and Maintain

### 5.1 View Logs

```powershell
# Check bot logs
Get-Content C:\Trading\TheBot\bot.log -Tail 100

# Check task scheduler history
Get-EventLog System | Where-Object {$_.EventID -eq 200}
```

### 5.2 Enable Email & Telegram Alerts

Set up Gmail App Password and Telegram bot token in `.env` to receive trade notifications.

### 5.3 Remote Access with Webhook

If you want to send trade actions remotely:

1. Expose the bot's webhook server (using ngrok or a proxy)
2. Set `WEBHOOK_SECRET` in `.env`
3. Send signed POST requests from your dashboard or external system

Example webhook request:

```bash
curl -X POST http://your-vps-ip:8080/webhook \
  -H "X-Signature: hmac_sha256_signature_here" \
  -d '{"action":"order_send","symbol":"EURUSD","signal":"BUY"}'
```

## Step 6: Performance Monitoring

### 6.1 Check Running Processes

```powershell
Get-Process python | Where-Object {$_.CommandLine -like '*TheBot*'}
```

### 6.2 Monitor Trades

Check the performance log:

```powershell
Get-Content C:\Trading\TheBot\performance_log.csv -Tail 20
```

### 6.3 System Health

Monitor VPS resources (CPU, Memory, Disk):

```powershell
Get-ComputerInfo
Get-Disk
```

## Troubleshooting

### Bot Won't Start

1. Verify Python installation:

   ```powershell
   python --version
   ```

2. Check MetaTrader 5 is running and logged in

3. Verify `.env` file exists with correct credentials

4. Check logs in `bot.log`

### Email/Telegram Alerts Not Sending

1. Verify environment variables are set correctly
2. Check firewall allows outbound HTTPS (ports 465, 587)
3. Test email with: `python -c "from dotenv import load_dotenv; import smtplib; ..."`

### MT5 Connection Lost

The bot attempts to reconnect automatically. If reconnection fails:

1. Restart MetaTrader 5 on the VPS
2. Verify internet connectivity
3. Check broker server status

## Security Recommendations

1. **Use a dedicated VPS** for trading (not shared infrastructure)
2. **Secure your `.env` file** - use restrictive file permissions
3. **Enable firewall** - only allow necessary ports (3389 for RDP if needed)
4. **Rotate credentials regularly** - update MT5 password, API keys
5. **Backup your config** - keep a backup of `config.yaml` and `.env`
6. **Use strong passwords** - especially for email and Telegram bot accounts
7. **Monitor logs regularly** - check for unauthorized access attempts

## Maintenance Schedule

- **Daily**: Check bot logs and recent trades
- **Weekly**: Verify alerts are functioning (test email/Telegram)
- **Monthly**: Review performance, optimize parameters
- **Quarterly**: Update bot code, test new features

## Support

For issues, check:

- Bot logs: `bot.log`
- Performance log: `performance_log.csv`
- GitHub issues: <https://github.com/MKLECHESSE/TheBot/issues>

---

**Last Updated**: 2025-11-26
