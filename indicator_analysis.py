#!/usr/bin/env python3
"""Advanced Technical Analysis & SMC-based Indicator Interpretation.

This module provides detailed breakdown of trading indicators with:
- Individual indicator interpretation (Bullish/Bearish/Neutral)
- Summary table of all signals
- Trend strength scoring (0-10)
- Smart Money Concepts (SMC) bias detection
- Entry/SL/TP zone suggestions based on structure
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple


class IndicatorAnalyzer:
    """Analyze trading indicators with SMC logic and provide structured insights."""

    def __init__(self):
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.rsi_neutral_upper = 60
        self.rsi_neutral_lower = 40

    def analyze(self, indicators: Dict, current_price: float = None, mode: str = "regular") -> Dict:
        """Comprehensive indicator analysis.
        
        Args:
            indicators: Dict with keys: rsi, macd_hist, ema_fast, ema_slow, adx, atr, 
                       bb_upper, bb_mid, bb_lower
            current_price: Current market price (for zone calculation)
            mode: 'regular', 'scalp', or 'hft'
        
        Returns:
            Dict with: breakdown, summary_table, trend_score, smc_bias, zones, conclusion
        """
        # 1. Individual Indicator Breakdown
        breakdown = self._analyze_indicators(indicators)
        
        # 2. Summary Table
        summary_table = self._create_summary_table(breakdown)
        
        # 3. Trend Strength Score (0-10)
        trend_score = self._calculate_trend_strength(indicators, breakdown)
        
        # 4. SMC Bias Detection
        smc_bias = self._detect_smc_bias(indicators, breakdown)
        
        # 5. Entry/SL/TP Zones
        zones = self._calculate_zones(indicators, smc_bias, current_price)
        
        # 6. Overall Conclusion
        conclusion = self._generate_conclusion(breakdown, trend_score, smc_bias, mode)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "breakdown": breakdown,
            "summary_table": summary_table,
            "trend_strength_score": trend_score,
            "smc_bias": smc_bias,
            "zones": zones,
            "conclusion": conclusion,
            "raw_indicators": indicators,
        }

    def _analyze_indicators(self, ind: Dict) -> Dict:
        """Analyze each indicator individually."""
        breakdown = {}

        # RSI Analysis
        rsi = ind.get("rsi", 50)
        if rsi > self.rsi_overbought:
            rsi_signal = "Bearish"
            rsi_description = f"Overbought (RSI={rsi:.0f} > 70). Potential pullback or reversal."
        elif rsi < self.rsi_oversold:
            rsi_signal = "Bullish"
            rsi_description = f"Oversold (RSI={rsi:.0f} < 30). Potential bounce or reversal."
        elif rsi > self.rsi_neutral_upper:
            rsi_signal = "Neutral"
            rsi_description = f"Neutral-to-Bullish (RSI={rsi:.0f}). Momentum is upward but not extreme."
        elif rsi < self.rsi_neutral_lower:
            rsi_signal = "Neutral"
            rsi_description = f"Neutral-to-Bearish (RSI={rsi:.0f}). Momentum is downward but not extreme."
        else:
            rsi_signal = "Neutral"
            rsi_description = f"Neutral (RSI={rsi:.0f}). No clear momentum bias."
        breakdown["rsi"] = {
            "value": rsi,
            "signal": rsi_signal,
            "description": rsi_description,
        }

        # MACD Histogram Analysis
        macd_hist = ind.get("macd_hist", 0)
        if macd_hist > 0:
            macd_signal = "Bullish"
            macd_description = f"Positive histogram (MACD={macd_hist:.6f}). Bullish momentum, uptrend strength."
        elif macd_hist < 0:
            macd_signal = "Bearish"
            macd_description = f"Negative histogram (MACD={macd_hist:.6f}). Bearish momentum, downtrend strength."
        else:
            macd_signal = "Neutral"
            macd_description = "Neutral (MACD=0). Momentum is balanced."
        breakdown["macd"] = {
            "value": macd_hist,
            "signal": macd_signal,
            "description": macd_description,
        }

        # EMA Analysis
        ema_fast = ind.get("ema_fast", 0)
        ema_slow = ind.get("ema_slow", 0)
        if ema_fast > ema_slow:
            ema_signal = "Bullish"
            ema_description = f"EMA alignment bullish. Fast ({ema_fast:.5f}) > Slow ({ema_slow:.5f}). Uptrend confirmed."
        elif ema_fast < ema_slow:
            ema_signal = "Bearish"
            ema_description = f"EMA alignment bearish. Fast ({ema_fast:.5f}) < Slow ({ema_slow:.5f}). Downtrend confirmed."
        else:
            ema_signal = "Neutral"
            ema_description = f"EMA converging. Fast ≈ Slow. Trend change possible."
        breakdown["ema"] = {
            "value": f"Fast: {ema_fast:.5f}, Slow: {ema_slow:.5f}",
            "signal": ema_signal,
            "description": ema_description,
        }

        # ADX Analysis (Trend Strength)
        adx = ind.get("adx", 0)
        if adx > 25:
            adx_signal = "Strong Trend"
            adx_description = f"Strong trend detected (ADX={adx:.0f} > 25). Market has directional bias."
        elif adx > 20:
            adx_signal = "Developing Trend"
            adx_description = f"Trend is developing (ADX={adx:.0f} > 20). Momentum building."
        else:
            adx_signal = "Weak Trend"
            adx_description = f"Weak trend (ADX={adx:.0f} < 20). Market is choppy/range-bound."
        breakdown["adx"] = {
            "value": adx,
            "signal": adx_signal,
            "description": adx_description,
        }

        # ATR Analysis (Volatility)
        atr = ind.get("atr", 0)
        # ATR interpretation is context-dependent (pairs have different volatility levels)
        if atr > 0.005:  # threshold for 5-digit pairs like EURUSD
            atr_signal = "High Volatility"
            atr_description = f"High volatility (ATR={atr:.6f}). Larger moves expected. Wider SL/TP recommended."
        elif atr < 0.002:
            atr_signal = "Low Volatility"
            atr_description = f"Low volatility (ATR={atr:.6f}). Smaller moves, tighter range. Scalp-friendly."
        else:
            atr_signal = "Normal Volatility"
            atr_description = f"Normal volatility (ATR={atr:.6f}). Moderate movement expected."
        breakdown["atr"] = {
            "value": atr,
            "signal": atr_signal,
            "description": atr_description,
        }

        # Bollinger Bands Analysis
        bb_upper = ind.get("bb_upper", 0)
        bb_mid = ind.get("bb_mid", 0)
        bb_lower = ind.get("bb_lower", 0)
        
        # Assume current_price is approximately the mid value for this analysis
        # (in real use, you'd pass current price separately)
        price_est = bb_mid
        
        if price_est > (bb_mid + (bb_upper - bb_mid) * 0.8):
            bb_signal = "Overbought"
            bb_description = f"Price near upper band ({price_est:.5f} vs Upper: {bb_upper:.5f}). Potential pullback."
        elif price_est < (bb_mid - (bb_mid - bb_lower) * 0.8):
            bb_signal = "Oversold"
            bb_description = f"Price near lower band ({price_est:.5f} vs Lower: {bb_lower:.5f}). Potential bounce."
        else:
            bb_signal = "Neutral"
            bb_description = f"Price in neutral zone. Upper: {bb_upper:.5f}, Mid: {bb_mid:.5f}, Lower: {bb_lower:.5f}."
        
        bb_width = bb_upper - bb_lower
        breakdown["bollinger_bands"] = {
            "value": f"Upper: {bb_upper:.5f}, Mid: {bb_mid:.5f}, Lower: {bb_lower:.5f}, Width: {bb_width:.5f}",
            "signal": bb_signal,
            "description": bb_description,
        }

        return breakdown

    def _create_summary_table(self, breakdown: Dict) -> List[Dict]:
        """Create a summary table of all indicators."""
        table = [
            {
                "Indicator": "RSI",
                "Value": f"{breakdown['rsi']['value']:.0f}",
                "Signal": breakdown["rsi"]["signal"],
            },
            {
                "Indicator": "MACD Histogram",
                "Value": f"{breakdown['macd']['value']:.6f}",
                "Signal": breakdown["macd"]["signal"],
            },
            {
                "Indicator": "EMA (Fast > Slow?)",
                "Value": breakdown["ema"]["value"],
                "Signal": breakdown["ema"]["signal"],
            },
            {
                "Indicator": "ADX",
                "Value": f"{breakdown['adx']['value']:.0f}",
                "Signal": breakdown["adx"]["signal"],
            },
            {
                "Indicator": "ATR",
                "Value": f"{breakdown['atr']['value']:.6f}",
                "Signal": breakdown["atr"]["signal"],
            },
            {
                "Indicator": "Bollinger Bands",
                "Value": breakdown["bollinger_bands"]["value"],
                "Signal": breakdown["bollinger_bands"]["signal"],
            },
        ]
        return table

    def _calculate_trend_strength(self, ind: Dict, breakdown: Dict) -> int:
        """Calculate trend strength score (0-10)."""
        score = 0

        # EMA alignment (0-3 points)
        if breakdown["ema"]["signal"] != "Neutral":
            score += 3
        else:
            score += 1

        # MACD momentum (0-2 points)
        if breakdown["macd"]["signal"] != "Neutral":
            score += 2
        else:
            score += 0.5

        # ADX strength (0-3 points)
        adx = ind.get("adx", 0)
        if adx > 25:
            score += 3
        elif adx > 20:
            score += 2
        elif adx > 15:
            score += 1

        # Bollinger Band expansion (0-2 points)
        bb_upper = ind.get("bb_upper", 0)
        bb_lower = ind.get("bb_lower", 0)
        bb_width = bb_upper - bb_lower
        if bb_width > 0.01:  # Threshold for 5-digit pairs
            score += 2
        elif bb_width > 0.005:
            score += 1

        return min(10, max(0, round(score, 1)))

    def _detect_smc_bias(self, ind: Dict, breakdown: Dict) -> Dict:
        """Detect market structure bias using SMC principles."""
        ema_signal = breakdown["ema"]["signal"]
        macd_signal = breakdown["macd"]["signal"]
        adx_signal = breakdown["adx"]["signal"]
        rsi_signal = breakdown["rsi"]["signal"]

        # Determine Market Structure
        if ema_signal == "Bullish" and macd_signal == "Bullish":
            market_structure = "Bullish"
            structure_description = "Higher lows and higher highs pattern. Buyers in control."
        elif ema_signal == "Bearish" and macd_signal == "Bearish":
            market_structure = "Bearish"
            structure_description = "Lower highs and lower lows pattern. Sellers in control."
        else:
            market_structure = "Range-Bound"
            structure_description = "Conflicting signals. Market is consolidating or in range."

        # Determine Liquidity Direction
        rsi = ind.get("rsi", 50)
        if rsi < 30 and market_structure == "Bullish":
            liquidity_direction = "Buyside"
            liquidity_description = "Market is in discount zone (oversold) with bullish bias. Smart money often buys discounts."
        elif rsi > 70 and market_structure == "Bearish":
            liquidity_direction = "Sellside"
            liquidity_description = "Market is in premium zone (overbought) with bearish bias. Smart money often sells premiums."
        elif market_structure == "Bullish":
            liquidity_direction = "Buyside"
            liquidity_description = "Bullish structure suggests smart money buying."
        elif market_structure == "Bearish":
            liquidity_direction = "Sellside"
            liquidity_description = "Bearish structure suggests smart money selling."
        else:
            liquidity_direction = "Unclear"
            liquidity_description = "No clear SMC bias in consolidation."

        # Premium vs Discount Pricing
        bb_upper = ind.get("bb_upper", 0)
        bb_lower = ind.get("bb_lower", 0)
        bb_mid = ind.get("bb_mid", 0)
        price = bb_mid  # Approximation

        if price > bb_mid and market_structure == "Bullish":
            pricing = "Premium Zone (Buyside)"
            pricing_description = "Price in premium; bullish bias. Align with uptrend."
        elif price < bb_mid and market_structure == "Bearish":
            pricing = "Discount Zone (Sellside)"
            pricing_description = "Price in discount; bearish bias. Align with downtrend."
        elif price > bb_mid:
            pricing = "Premium Zone"
            pricing_description = "Price elevated. Potential sell zone or profit target."
        elif price < bb_mid:
            pricing = "Discount Zone"
            pricing_description = "Price depressed. Potential buy zone or entry area."
        else:
            pricing = "Neutral"
            pricing_description = "Price at mid-line. No clear premium/discount bias."

        return {
            "market_structure": market_structure,
            "market_structure_description": structure_description,
            "liquidity_direction": liquidity_direction,
            "liquidity_description": liquidity_description,
            "pricing_zone": pricing,
            "pricing_description": pricing_description,
        }

    def _calculate_zones(self, ind: Dict, smc_bias: Dict, current_price: float = None) -> Dict:
        """Calculate Entry, SL, TP zones based on SMC logic."""
        bb_upper = ind.get("bb_upper", 0)
        bb_lower = ind.get("bb_lower", 0)
        bb_mid = ind.get("bb_mid", 0)
        atr = ind.get("atr", 0)

        if current_price is None:
            current_price = bb_mid

        market_structure = smc_bias["market_structure"]
        liquidity_direction = smc_bias["liquidity_direction"]

        zones = {}

        # Entry Zone Logic
        if market_structure == "Bullish" and liquidity_direction == "Buyside":
            # Buy in discount
            entry_zone = f"Lower BB ({bb_lower:.5f}) to Mid ({bb_mid:.5f})"
            entry_description = "Discount zone. SMC principle: buy low. Entry on bounce from lower band."
            zones["entry"] = {"zone": entry_zone, "description": entry_description}
            
            # SL Zone (below discount)
            sl_zone = f"Below Lower BB ({bb_lower - atr:.5f})"
            sl_description = f"Below lower band or recent swing low. Risk: {atr * 2:.5f} pips."
            zones["sl"] = {"zone": sl_zone, "description": sl_description}
            
            # TP Zone (in premium)
            tp_zone = f"Upper BB ({bb_upper:.5f}) to resistance"
            tp_description = "Premium zone. SMC principle: sell high. Take profit at upper band or structure resistance."
            zones["tp"] = {"zone": tp_zone, "description": tp_description}

        elif market_structure == "Bearish" and liquidity_direction == "Sellside":
            # Sell in premium
            entry_zone = f"Mid ({bb_mid:.5f}) to Upper BB ({bb_upper:.5f})"
            entry_description = "Premium zone. SMC principle: sell high. Entry on pullback from upper band."
            zones["entry"] = {"zone": entry_zone, "description": entry_description}
            
            # SL Zone (above premium)
            sl_zone = f"Above Upper BB ({bb_upper + atr:.5f})"
            sl_description = f"Above upper band or recent swing high. Risk: {atr * 2:.5f} pips."
            zones["sl"] = {"zone": sl_zone, "description": sl_description}
            
            # TP Zone (in discount)
            tp_zone = f"Lower BB ({bb_lower:.5f}) to support"
            tp_description = "Discount zone. SMC principle: buy low. Take profit at lower band or structure support."
            zones["tp"] = {"zone": tp_zone, "description": tp_description}

        else:
            # Range-bound or unclear bias
            entry_zone = f"Mid ({bb_mid:.5f}) ± {atr:.5f}"
            entry_description = "Neutral zone. Wait for structure confirmation or test extremes."
            zones["entry"] = {"zone": entry_zone, "description": entry_description}
            
            sl_zone = f"±{atr * 1.5:.5f} from entry"
            sl_description = "Place SL beyond recent volatility."
            zones["sl"] = {"zone": sl_zone, "description": sl_description}
            
            tp_zone = f"Upper BB ({bb_upper:.5f}) or Lower BB ({bb_lower:.5f})"
            tp_description = "Target extremes or breakout direction."
            zones["tp"] = {"zone": tp_zone, "description": tp_description}

        return zones

    def _generate_conclusion(self, breakdown: Dict, trend_score: float, smc_bias: Dict, mode: str) -> Dict:
        """Generate overall conclusion."""
        ema_signal = breakdown["ema"]["signal"]
        macd_signal = breakdown["macd"]["signal"]
        market_structure = smc_bias["market_structure"]

        # Count bullish/bearish signals
        bullish_count = sum(1 for k, v in breakdown.items() if v.get("signal") == "Bullish")
        bearish_count = sum(1 for k, v in breakdown.items() if v.get("signal") == "Bearish")
        neutral_count = sum(1 for k, v in breakdown.items() if v.get("signal") == "Neutral" and k not in ["adx", "atr"])

        if bullish_count > bearish_count:
            overall_bias = "BULLISH"
            bias_color = "🟢"
        elif bearish_count > bullish_count:
            overall_bias = "BEARISH"
            bias_color = "🔴"
        else:
            overall_bias = "MIXED / WAIT"
            bias_color = "🟡"

        trend_strength = "Strong" if trend_score >= 7 else "Developing" if trend_score >= 4 else "Weak"
        confidence = "High" if trend_score >= 8 else "Medium" if trend_score >= 5 else "Low"

        # Mode-specific recommendations
        if mode == "scalp":
            recommendation = "Scalping Mode: Best used in high volatility with tight SL/TP. Entry window is narrow; high precision needed."
        elif mode == "hft":
            recommendation = "HFT Mode: Requires strong trend (ADX > 25) and high volatility. Avoid in choppy markets."
        else:
            recommendation = "Regular Mode: Standard risk/reward. Follow SMC structure and wait for confirmation."

        return {
            "overall_bias": overall_bias,
            "bias_emoji": bias_color,
            "confidence": confidence,
            "trend_strength": trend_strength,
            "trend_score": trend_score,
            "bullish_signals": bullish_count,
            "bearish_signals": bearish_count,
            "neutral_signals": neutral_count,
            "market_structure": market_structure,
            "mode_recommendation": recommendation,
            "summary": f"{bias_color} {overall_bias} | Trend: {trend_strength} ({trend_score}/10) | Confidence: {confidence}"
        }

    def format_report(self, analysis: Dict) -> str:
        """Format analysis as readable markdown report."""
        report = []
        report.append("=" * 80)
        report.append("🔍 ADVANCED TECHNICAL ANALYSIS & SMC BIAS REPORT")
        report.append("=" * 80)
        report.append(f"⏱️  Timestamp: {analysis['timestamp']}")
        report.append(f"📊 Mode: {analysis['mode'].upper()}")
        report.append("")

        # Conclusion (prominent)
        conclusion = analysis["conclusion"]
        report.append("─" * 80)
        report.append(f"{conclusion['bias_emoji']} CONCLUSION: {conclusion['overall_bias']}")
        report.append("─" * 80)
        report.append(f"Trend Strength: {conclusion['trend_strength']} ({conclusion['trend_score']:.1f}/10)")
        report.append(f"Confidence: {conclusion['confidence']}")
        report.append(f"Market Structure: {conclusion['market_structure']}")
        report.append(f"Bullish Signals: {conclusion['bullish_signals']} | Bearish: {conclusion['bearish_signals']} | Neutral: {conclusion['neutral_signals']}")
        report.append(f"Recommendation ({analysis['mode'].upper()}): {conclusion['mode_recommendation']}")
        report.append("")

        # 1. Indicator Breakdown
        report.append("─" * 80)
        report.append("1️⃣  INDICATOR BREAKDOWN")
        report.append("─" * 80)
        for indicator, data in analysis["breakdown"].items():
            report.append(f"\n📍 {indicator.upper()}: {data['signal']}")
            report.append(f"   Value: {data['value']}")
            report.append(f"   → {data['description']}")
        report.append("")

        # 2. Summary Table
        report.append("─" * 80)
        report.append("2️⃣  SUMMARY TABLE")
        report.append("─" * 80)
        report.append("")
        report.append("| Indicator | Value | Signal |")
        report.append("|-----------|-------|--------|")
        for row in analysis["summary_table"]:
            report.append(f"| {row['Indicator']} | {row['Value']} | {row['Signal']} |")
        report.append("")

        # 3. Trend Strength Score
        report.append("─" * 80)
        report.append("3️⃣  TREND STRENGTH SCORE")
        report.append("─" * 80)
        score = analysis["trend_strength_score"]
        bar = "█" * int(score) + "░" * (10 - int(score))
        report.append(f"Score: {score:.1f}/10  [{bar}]")
        if score >= 7:
            report.append("📈 Strong trend detected. Market has clear directional bias.")
        elif score >= 4:
            report.append("📊 Developing trend. Momentum is building.")
        else:
            report.append("📉 Weak trend. Market is choppy/consolidating.")
        report.append("")

        # 4. SMC Bias
        report.append("─" * 80)
        report.append("4️⃣  SMART MONEY CONCEPTS (SMC) BIAS")
        report.append("─" * 80)
        smc = analysis["smc_bias"]
        report.append(f"\n🏗️  Market Structure: {smc['market_structure']}")
        report.append(f"   {smc['market_structure_description']}")
        report.append(f"\n💧 Liquidity Direction: {smc['liquidity_direction']}")
        report.append(f"   {smc['liquidity_description']}")
        report.append(f"\n💰 Pricing Zone: {smc['pricing_zone']}")
        report.append(f"   {smc['pricing_description']}")
        report.append("")

        # 5. Entry/SL/TP Zones
        report.append("─" * 80)
        report.append("5️⃣  ENTRY, SL, TP ZONES (NOT FINANCIAL ADVICE)")
        report.append("─" * 80)
        zones = analysis["zones"]
        report.append(f"\n🟢 ENTRY ZONE: {zones['entry']['zone']}")
        report.append(f"   {zones['entry']['description']}")
        report.append(f"\n🔴 STOP LOSS ZONE: {zones['sl']['zone']}")
        report.append(f"   {zones['sl']['description']}")
        report.append(f"\n🟡 TAKE PROFIT ZONE: {zones['tp']['zone']}")
        report.append(f"   {zones['tp']['description']}")
        report.append("")

        report.append("=" * 80)
        report.append("⚠️  DISCLAIMER: This analysis is for educational purposes only.")
        report.append("    Do not rely solely on technical analysis for trading decisions.")
        report.append("    Always use proper risk management and position sizing.")
        report.append("=" * 80)

        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    # Example indicator data
    example_indicators = {
        "rsi": 65,
        "macd_hist": 0.00005,
        "ema_fast": 1.0850,
        "ema_slow": 1.0820,
        "adx": 28,
        "atr": 0.0045,
        "bb_upper": 1.0870,
        "bb_mid": 1.0835,
        "bb_lower": 1.0800,
    }

    analyzer = IndicatorAnalyzer()
    
    # Regular mode analysis
    analysis = analyzer.analyze(example_indicators, current_price=1.0845, mode="regular")
    print(analyzer.format_report(analysis))
    
    print("\n\n")
    
    # Scalping mode analysis
    analysis_scalp = analyzer.analyze(example_indicators, current_price=1.0845, mode="scalp")
    print(analyzer.format_report(analysis_scalp))
