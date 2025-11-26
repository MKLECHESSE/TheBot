# 🖥️ TheBot - Complete VPS Deployment Guide (Windows)

This guide covers end-to-end setup of TheBot on a Windows VPS for 24/7 automated trading.

---

## 📋 Prerequisites

- **Windows Server 2016 or later** (or Windows 10/11 Pro for testing)
- **Python 3.11+**
- **Git**
- **MetaTrader 5** (with trading account)
- **Administrator access**
- **Internet connection** (static IP recommended)

---

## 🔧 Phase 1: VPS Environment Setup

### Step 1.1: Prepare Windows VPS

```powershell
# Run as Administrator

# Enable Windows updates
sconfig

# Install Windows Update Orchestrator Service (auto-updates)
Start-Service wuauserv

# Disable unnecessary services for better performance
Disable-NetAdapterBinding -Name "Ethernet" -ComponentID ms_tcpip6

# Set timezone to UTC (for consistent logging)
Set-TimeZone -Id "UTC"
```

### Step 1.2: Install Python

```powershell
# Download Python 3.12
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" -OutFile "C:\python-installer.exe"

# Install
C:\python-installer.exe /quiet InstallAllUsers=1 PrependPath=1

# Verify
python --version
pip --version

# Clean up
Remove-Item "C:\python-installer.exe"
```

### Step 1.3: Install Git

```powershell
# Using Windows Package Manager
winget install Git.Git

# Or download from https://git-scm.com/download/win
# and run installer with /SILENT flag

# Verify
git --version
```

### Step 1.4: Install MetaTrader 5

```powershell
# Download from your broker's website
# Example: https://download.mql5.com/mt5setup.exe

# Run installer (may require manual steps)
# C:\mt5setup.exe

# After installation, configure:
# 1. Open MT5
# 2. Login with demo/live credentials
# 3. Add desired instruments to Market Watch
# 4. Test connection and sync
# 5. **IMPORTANT**: Keep MT5 running in background
```

---

## 📦 Phase 2: Deploy TheBot Code

### Step 2.1: Clone Repository

```powershell
# Create trading directory
New-Item -ItemType Directory -Force -Path "C:\Trading\TheBot"
cd C:\Trading\TheBot

# Clone from GitHub
git clone https://github.com/MKLECHESSE/TheBot.git .

# Verify files
Get-ChildItem

# Should show: TheBot.py, config.yaml, requirements.txt, etc.
```

### Step 2.2: Create Python Virtual Environment

```powershell
# Create venv
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install MT5 (Windows only)
pip install MetaTrader5

# Deactivate venv (for now)
deactivate
```

---

## 🔐 Phase 3: Configuration & Secrets

### Step 3.1: Create `.env` file

```powershell
# Create environment file
$env_content = @"
# MetaTrader 5 Demo/Live Credentials
MT5_LOGIN=your_login_number
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server

# Email Alerts (Gmail)
EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO=your_email@gmail.com

# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Webhook (for remote actions)
WEBHOOK_SECRET=your_secure_random_key

# Logging
LOG_FILE=C:\Trading\TheBot\bot.log
"@

# Write to .env
$env_content | Out-File -FilePath "C:\Trading\TheBot\.env" -Encoding UTF8

# Verify (but DON'T display passwords)
"✅ .env file created at C:\Trading\TheBot\.env"
```

**Important Notes:**

- For Gmail: Use [App Password](https://support.google.com/accounts/answer/185833), NOT your account password
- For Telegram: Create bot via @BotFather, get token, send message to bot, get chat ID via `https://api.telegram.org/botYOUR_TOKEN/getUpdates`

### Step 3.2: Update `config.yaml`

```yaml
# Key settings for VPS deployment

live_trading: true              # Enable real trading
demo_mode: true                 # Use demo credentials
paper_trade: false              # Real orders (not paper)

demo_credentials:
  login: "your_demo_login"
  password: "your_demo_password"
  server: "DemoServerName"

symbols:
  classic:
    - "EURUSD"
    - "GBPUSD"
    - "USDJPY"

risk_percentage: 1              # 1% risk per trade
max_loss_percentage: 3          # 3% max daily loss

check_interval: 60              # Check every 60 seconds
symbol_delay: 2                 # Delay between symbols

atr_sl_multiplier: 2
atr_tp_multiplier: 4

magic_number: 123456            # Unique order identifier
```

### Step 3.3: Secure File Permissions

```powershell
# Restrict .env to Administrator only
icacls "C:\Trading\TheBot\.env" /inheritance:r /grant:r "${env:USERNAME}:F"

# Restrict config.yaml (read-only for bot user)
icacls "C:\Trading\TheBot\config.yaml" /inheritance:r /grant:r "${env:USERNAME}:F"

# Create log directory with proper permissions
New-Item -ItemType Directory -Force -Path "C:\Trading\TheBot\logs"
icacls "C:\Trading\TheBot\logs" /inheritance:r /grant:r "${env:USERNAME}:F"
```

---

## ⚙️ Phase 4: Deploy as Windows Service

### Option A: Using Task Scheduler (Recommended for Beginners)

```powershell
# Run as Administrator

# Create task to run bot at startup
$TaskName = "TheBot-Trading"
$TaskPath = "C:\Trading\TheBot"
$PythonExe = "$TaskPath\.venv\Scripts\python.exe"
$ScriptPath = "$TaskPath\TheBot.py"

# Create action
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $ScriptPath -WorkingDirectory $TaskPath

# Create trigger (at startup, repeat every 1 minute if failed)
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create settings (run with highest privileges, restart on failure)
$Settings = New-ScheduledTaskSettingsSet `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries `
    -DontStopOnIdleEnd

# Register task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Force

# Verify
Get-ScheduledTask -TaskName $TaskName | Select-Object State, Status

# Start task manually
Start-ScheduledTask -TaskName $TaskName

# View task history
Get-ScheduledTaskInfo -TaskName $TaskName
```

### Option B: Using NSSM (Advanced - Better Control)

```powershell
# Download NSSM
$NSSmURL = "https://nssm.cc/download/nssm-2.24-101-g897c7f7.zip"
Invoke-WebRequest -Uri $NSSmURL -OutFile "C:\nssm.zip"

# Extract
Expand-Archive -Path "C:\nssm.zip" -DestinationPath "C:\nssm" -Force

# Install service
$nssm = "C:\nssm\nssm-2.24-101-g897c7f7\win64\nssm.exe"
$python = "C:\Trading\TheBot\.venv\Scripts\python.exe"
$script = "C:\Trading\TheBot\TheBot.py"

& $nssm install TheBot $python $script

# Configure service
& $nssm set TheBot AppDirectory "C:\Trading\TheBot"
& $nssm set TheBot AppStdout "C:\Trading\TheBot\logs\stdout.log"
& $nssm set TheBot AppStderr "C:\Trading\TheBot\logs\stderr.log"
& $nssm set TheBot AppExit Default Restart

# Start service
Start-Service TheBot

# Check status
Get-Service TheBot

# View logs
Get-Content "C:\Trading\TheBot\logs\stdout.log" -Tail 50
```

---

## 📊 Phase 5: Monitoring & Maintenance

### Step 5.1: Set Up Log Monitoring

```powershell
# Create monitoring script
$MonitorScript = @"
# Monitor bot process and logs
while (`$true) {
    # Check bot is running
    `$bot_running = Get-Process python -ErrorAction SilentlyContinue | 
        Where-Object {`$_.CommandLine -like '*TheBot*'}
    
    if (`$null -eq `$bot_running) {
        Write-Host "❌ Bot not running! Restarting..." -ForegroundColor Red
        Start-ScheduledTask -TaskName "TheBot-Trading"
        Start-Sleep -Seconds 10
    } else {
        Write-Host "✅ Bot running (PID: `$($bot_running.Id))" -ForegroundColor Green
    }
    
    # Check recent log activity
    `$log_path = "C:\Trading\TheBot\bot.log"
    if (Test-Path `$log_path) {
        `$recent = Get-Content `$log_path -Tail 5
        Write-Host "Recent logs:"
        `$recent | ForEach-Object { Write-Host "  $_" }
    }
    
    # Sleep 5 minutes
    Start-Sleep -Seconds 300
}
"@

# Save monitoring script
$MonitorScript | Out-File -FilePath "C:\Trading\TheBot\monitor_bot.ps1" -Encoding UTF8

# Run monitoring in background
$job = Start-Job -FilePath "C:\Trading\TheBot\monitor_bot.ps1" -Name "BotMonitor"
```

### Step 5.2: Create Backup Script

```powershell
# Create daily backup of config, logs, and performance data
$BackupScript = @"
# Backup bot data daily
`$backup_dir = "C:\Trading\Backups\$(Get-Date -Format 'yyyy-MM-dd')"
New-Item -ItemType Directory -Force -Path `$backup_dir

# Backup important files
Copy-Item "C:\Trading\TheBot\config.yaml" -Destination `$backup_dir
Copy-Item "C:\Trading\TheBot\performance_log.csv" -Destination `$backup_dir
Copy-Item "C:\Trading\TheBot\bot.log" -Destination "`$backup_dir\bot.log.$(Get-Date -Format 'HHmmss')"

# Compress backup
Compress-Archive -Path `$backup_dir -DestinationPath "`$backup_dir.zip" -Force

Write-Host "Backup created: `$backup_dir"
"@

$BackupScript | Out-File -FilePath "C:\Trading\TheBot\backup_daily.ps1" -Encoding UTF8

# Schedule daily backup at 23:00
$BackupAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\Trading\TheBot\backup_daily.ps1"
$BackupTrigger = New-ScheduledTaskTrigger -Daily -At 23:00
Register-ScheduledTask -TaskName "TheBot-DailyBackup" -Action $BackupAction -Trigger $BackupTrigger -RunLevel Highest -Force
```

### Step 5.3: Monitor via Telegram (Heartbeat)

Add to `config.yaml`:

```yaml
enable_heartbeat: true          # Send periodic status updates
heartbeat_interval_minutes: 60  # Every hour
```

Then add to `TheBot.py` main loop:

```python
# Check heartbeat flag
if config.get("enable_heartbeat"):
    elapsed = (datetime.now(timezone.utc) - last_heartbeat).total_seconds()
    if elapsed > config.get("heartbeat_interval_minutes", 60) * 60:
        acc = mt5.account_info()
        balance = acc.balance if acc else 0
        equity = acc.equity if acc else 0
        send_telegram_alert(f"🤖 Heartbeat: Balance ${balance:.2f} | Equity ${equity:.2f}")
        last_heartbeat = datetime.now(timezone.utc)
```

---

## 🚨 Phase 6: Emergency Procedures

### Emergency Stop Script

```powershell
# Create emergency stop
$EmergencyStop = @"
# Immediately stop trading and close all positions

`$task_name = "TheBot-Trading"

# Stop scheduled task
Stop-ScheduledTask -TaskName `$task_name -Force

# Kill any running bot process
Stop-Process -Name python -Force -ErrorAction SilentlyContinue

# Send alert
Write-Host "❌ EMERGENCY STOP ACTIVATED" -ForegroundColor Red
Write-Host "All trading halted. Check MT5 for open positions."
"@

$EmergencyStop | Out-File -FilePath "C:\Trading\TheBot\emergency_stop.ps1" -Encoding UTF8

# Create desktop shortcut for quick access
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut("$env:USERPROFILE\Desktop\STOP_BOT.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-File C:\Trading\TheBot\emergency_stop.ps1"
$Shortcut.Description = "EMERGENCY: Stop TheBot trading immediately"
$Shortcut.Save()
```

### Manual Position Closure Checklist

If the bot becomes unresponsive:

```powershell
# 1. Open MT5 terminal
# 2. Navigate to "Positions" tab
# 3. For each open position:
#    - Right-click > "Close Position"
#    - Confirm at market price
# 4. Verify all positions closed
# 5. Take screenshot of closed trades
# 6. Review logs to understand what happened
# 7. Do NOT restart bot until root cause identified
```

---

## 🔍 Phase 7: Verification & Troubleshooting

### Verify Installation

```powershell
# Check Python and venv
C:\Trading\TheBot\.venv\Scripts\python.exe --version

# Check MT5 connection
C:\Trading\TheBot\.venv\Scripts\python.exe -c `
    "import MetaTrader5 as mt5; print('MT5 initialized:', mt5.initialize())"

# Check bot runs
C:\Trading\TheBot\.venv\Scripts\python.exe C:\Trading\TheBot\TheBot.py --once --dry-run

# Check logs
Get-Content C:\Trading\TheBot\bot.log -Tail 30
```

### Common Issues

#### Issue: "Python not found"

```powershell
# Add Python to PATH manually
[Environment]::SetEnvironmentVariable(
    "Path",
    "$env:Path;C:\Python312",
    "Machine"
)

# Reload environment
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

#### Issue: "MT5 connection failed"

```powershell
# 1. Ensure MT5 terminal is running
Get-Process | Where-Object Name -like "*mt*"

# 2. Check MT5 is logged in (manual check required)

# 3. Restart MT5
Stop-Process -Name "terminal*" -Force
Start-Sleep -Seconds 5
# Launch MT5 manually from Start menu

# 4. Check logs
Get-Content "C:\Program Files\MetaTrader 5\logs\*.log" -Tail 50
```

#### Issue: "Insufficient balance for trade"

```powershell
# 1. Check demo account balance in MT5
# 2. Reduce risk_percentage in config.yaml
# 3. Or request demo account credit from broker
```

#### Issue: "Task not running automatically"

```powershell
# Check task properties
Get-ScheduledTask -TaskName "TheBot-Trading" | Get-ScheduledTaskInfo

# View task history for failures
Get-ScheduledTask -TaskName "TheBot-Trading" | Get-ScheduledTaskInfo | 
    Select-Object LastRunTime, LastTaskResult

# Re-run task manually
Start-ScheduledTask -TaskName "TheBot-Trading"

# Check event logs for errors
Get-EventLog System -Source TaskScheduler -Newest 20 | 
    Where-Object {$_.EventID -eq 201}
```

---

## 📈 Phase 8: Performance Monitoring

### Track Trading Metrics

```powershell
# View performance log
$perf_log = Import-Csv "C:\Trading\TheBot\performance_log.csv"

# Calculate statistics
$perf_log | Measure-Object -Property pnl -Sum -Average -Maximum -Minimum | 
    Format-List

# Count trades by signal
$perf_log | Group-Object signal | Select-Object Name, Count

# Check for errors
Get-Content "C:\Trading\TheBot\bot.log" | 
    Select-String "ERROR|FAILED" | 
    Measure-Object

# Send weekly report
$report = @"
📊 TheBot Weekly Report
=============================
Total Trades: $(($perf_log | Measure-Object).Count)
Total P&L: $($perf_log | Measure-Object -Property pnl -Sum).Sum
Win Rate: %
Max Drawdown: %
=============================
"@

# Save and email report
$report | Out-File "C:\Trading\Reports\weekly_report_$(Get-Date -Format 'yyyy-MM-dd').txt"
```

---

## ✅ Deployment Checklist

Before running 24/7:

- [ ] Python 3.11+ installed
- [ ] Git repository cloned
- [ ] Virtual environment created and activated
- [ ] All requirements installed
- [ ] `.env` file created with credentials
- [ ] `config.yaml` updated for VPS settings
- [ ] MT5 terminal running and logged in
- [ ] Task Scheduler or NSSM service created
- [ ] Monitoring script set up
- [ ] Backup script scheduled
- [ ] Emergency stop script created
- [ ] Tested dry-run on VPS
- [ ] Tested paper trading
- [ ] Tested live trading (1-2 trades)
- [ ] Logs rotating properly
- [ ] All notifications working
- [ ] Risk settings conservative
- [ ] Manual position closure procedure documented

---

## 🎯 Success Criteria

After 7 days of VPS operation:

✅ Zero crashes or unexpected restarts  
✅ Consistent order execution  
✅ All alerts delivered  
✅ P&L tracked accurately  
✅ No reconnection issues  
✅ Backups created daily  
✅ Logs clean and rotated  
✅ Performance stable  

---

## 📞 Support & Troubleshooting

For issues, check:

1. `C:\Trading\TheBot\bot.log` — Application logs
2. Windows Event Viewer — System/Application errors
3. `C:\Trading\TheBot\performance_log.csv` — Trade history
4. MT5 Alerts/Journal — Order confirmations

---

**Last Updated**: 2025-11-26  
**Version**: 2.0  
**Status**: Production Ready
