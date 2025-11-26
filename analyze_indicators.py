#!/usr/bin/env python3
"""
Quick Indicator Analysis Tool - Paste JSON data and get instant breakdown
"""

import json
import sys
from indicator_analysis import IndicatorAnalyzer


def main():
    print("=" * 80)
    print("🔍 QUICK INDICATOR ANALYSIS TOOL")
    print("=" * 80)
    print("\nPaste indicator data in JSON format and press Enter twice:")
    print('Example: {"rsi":65,"macd_hist":0.00005,"ema_fast":1.0850,"ema_slow":1.0820,"adx":28,"atr":0.0045,"bb_upper":1.0870,"bb_mid":1.0835,"bb_lower":1.0800}')
    print("\n")
    
    # Read multi-line input
    lines = []
    while True:
        try:
            line = input()
            if line:
                lines.append(line)
            else:
                if lines:
                    break
                # Continue waiting if no data yet
        except EOFError:
            break
    
    data_str = "".join(lines)
    
    if not data_str.strip():
        print("❌ No data provided. Exiting.")
        return
    
    try:
        indicators = json.loads(data_str)
        
        # Validate required fields
        required = ["rsi", "macd_hist", "ema_fast", "ema_slow", "adx", "atr", "bb_upper", "bb_mid", "bb_lower"]
        missing = [k for k in required if k not in indicators]
        if missing:
            print(f"⚠️  Missing fields: {', '.join(missing)}")
            print("   These will use default values of 0.")
        
        # Get mode and price
        mode = indicators.pop("mode", "regular")
        current_price = indicators.pop("current_price", None)
        
        # Analyze
        analyzer = IndicatorAnalyzer()
        analysis = analyzer.analyze(indicators, current_price=current_price, mode=mode)
        
        # Print formatted report
        report = analyzer.format_report(analysis)
        print("\n")
        print(report)
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
