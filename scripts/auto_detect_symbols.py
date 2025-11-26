#!/usr/bin/env python3
"""Auto-detect Market Watch symbols and suggest config.yaml updates."""

import MetaTrader5 as mt5
import yaml
import sys

if not mt5.initialize():
    print("Failed to initialize MT5")
    sys.exit(1)

syms = mt5.symbols_get()
available_names = [s.name for s in syms]
print(f"Detected {len(available_names)} symbols in Market Watch:")
print(available_names)

# Read current config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

old_symbols = config.get("symbols", {}).get("classic", [])
print(f"\nCurrent symbols.classic: {old_symbols}")

# Suggest a small list of available symbols for quick testing
suggested = available_names[:10]  # first 10 available
print(f"\nSuggested symbols.classic (first 10 available):")
print(suggested)

# Option to auto-update
ans = input("\nAuto-update config.yaml symbols.classic? (y/n): ")
if ans.lower() == "y":
    config["symbols"]["classic"] = suggested
    with open("config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    print("Updated config.yaml")

mt5.shutdown()
