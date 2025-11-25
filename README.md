# TheBot ÔÇö Setup & Safety

This project is a Python trading bot designed to run with MetaTrader 5 (MT5). Follow these steps to prepare your environment safely.

## Requirements
- Windows (MetaTrader5 Python package requires Windows and matching bitness with the MT5 terminal)
- Python 3.8+ (preferably 64-bit if your MT5 terminal is 64-bit)
- A virtual environment for isolation

## Quick setup (PowerShell)
```powershell
# 1. Create + activate venv (if you don't have one)
python -m venv .venv
& .\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install -r .\requirements.txt

# 3. Verify imports
python .\check_imports.py

# 4. Optional: run the bot in demo mode (ensure config.yaml sets live_trading: false)
python .\TheBot.py
```

## Troubleshooting
- If `MetaTrader5` import fails:
  - Ensure you're on Windows and Python bitness matches the MT5 terminal (both 64-bit or both 32-bit).
  - Install with: `python -m pip install MetaTrader5`
  - If installation fails, check compiler/toolchain/messages from pip and consult the package docs.

- If Pylance (VS Code) marks imports as unresolved:
  - Confirm VS Code uses the same interpreter as your venv (bottom-right status bar).
  - Restart the Python Language Server (Command Palette ÔåÆ "Python: Restart Language Server").
  - Add site-packages to `python.analysis.extraPaths` if necessary.

## Safety notes
- Default config should use `live_trading: false` while testing.
- Review `config.yaml` before enabling live trading (check `risk_percentage`, `max_loss_percentage`, `symbols`).
- Start with a demo or small account and monitor behavior closely.

## How I can help next
- Run the import check in your environment and paste the output here.
- Add a safety wrapper to prevent accidental `LIVE_TRADING` in the code.
- Help configure VS Code settings if Pylance still flags unresolved imports.

---

Remote README:

# TheBot
Trading bot platform-streamlit
