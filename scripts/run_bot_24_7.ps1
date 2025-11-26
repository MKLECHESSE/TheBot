# TheBot 24/7 Auto-Restart Script for Windows VPS
# This script runs TheBot continuously and automatically restarts on failure.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File "run_bot_24_7.ps1"

param(
    [string]$BotPath = "C:\Users\$env:USERNAME\Documents\TheBot.py",
    [int]$RestartDelaySeconds = 10,
    [string]$LogFile = "$BotPath\bot_24_7.log"
)

# Verify bot directory exists
if (-not (Test-Path $BotPath)) {
    Write-Host "Error: Bot path not found: $BotPath" -ForegroundColor Red
    exit 1
}

# Initialize log file
$LogFile = "$BotPath\bot_24_7.log"
"=== TheBot 24/7 Auto-Restart Script ===" | Out-File -FilePath $LogFile -Append
"Started at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $LogFile -Append

Write-Host "TheBot 24/7 Monitor Started" -ForegroundColor Green
Write-Host "Bot Path: $BotPath" -ForegroundColor Cyan
Write-Host "Log File: $LogFile" -ForegroundColor Cyan
Write-Host "Restart Delay: $RestartDelaySeconds seconds" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the bot gracefully." -ForegroundColor Yellow
Write-Host ""

# Initialize counters
$restartCount = 0
$lastStartTime = $null

# Main loop
while ($true) {
    try {
        $restartCount++
        $startTime = Get-Date
        $lastStartTime = $startTime
        
        $logMessage = "[$startTime] Starting TheBot (Restart #$restartCount)"
        Write-Host $logMessage -ForegroundColor Green
        $logMessage | Out-File -FilePath $LogFile -Append
        
        # Build command to run the bot
        $pythonExe = "$BotPath\.venv\Scripts\python.exe"
        $botScript = "$BotPath\TheBot.py"
        
        # Verify Python executable exists
        if (-not (Test-Path $pythonExe)) {
            $errorMsg = "Error: Python executable not found at $pythonExe"
            Write-Host $errorMsg -ForegroundColor Red
            $errorMsg | Out-File -FilePath $LogFile -Append
            exit 1
        }
        
        # Run the bot in the current process (will block until bot exits)
        & $pythonExe $botScript
        
        # If we reach here, the bot has exited
        $exitCode = $LASTEXITCODE
        $endTime = Get-Date
        $uptime = $endTime - $startTime
        
        $logMessage = "[$endTime] TheBot exited with code $exitCode after $($uptime.TotalSeconds) seconds"
        Write-Host $logMessage -ForegroundColor Yellow
        $logMessage | Out-File -FilePath $LogFile -Append
        
        # Check if bot crashed or normal exit
        if ($exitCode -ne 0) {
            $errorMsg = "⚠️  TheBot crashed! Restarting in $RestartDelaySeconds seconds..."
            Write-Host $errorMsg -ForegroundColor Red
            $errorMsg | Out-File -FilePath $LogFile -Append
            
            # Wait before restarting
            Start-Sleep -Seconds $RestartDelaySeconds
        } else {
            Write-Host "TheBot exited normally. Restarting..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
    catch {
        $errorMsg = "Error running bot: $_"
        Write-Host $errorMsg -ForegroundColor Red
        $errorMsg | Out-File -FilePath $LogFile -Append
        Write-Host "Restarting in $RestartDelaySeconds seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds $RestartDelaySeconds
    }
}
