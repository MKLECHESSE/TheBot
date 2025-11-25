#!/usr/bin/env python3
"""Simple import checker for the trading bot environment.
Run this inside your project's virtual environment to verify required packages.
"""

modules = [
    "pandas",
    "numpy",
    "requests",
    "matplotlib",
    "yaml",
    "MetaTrader5",
]

for m in modules:
    try:
        mod = __import__(m)
        ver = getattr(mod, "__version__", None)
        if ver is None:
            print(f"{m}: OK (version not available)")
        else:
            print(f"{m}: OK (version={ver})")
    except Exception as e:
        print(f"{m}: ERROR -> {e}")
