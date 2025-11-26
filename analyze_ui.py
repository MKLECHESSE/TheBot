#!/usr/bin/env python3
"""
Interactive Indicator Analysis - Simple Web Interface
Run this to get a local web UI for analysis
"""

import streamlit as st
import json
from indicator_analysis import IndicatorAnalyzer

st.set_page_config(page_title="Indicator Analysis Tool", layout="wide")

st.markdown("""
<style>
    body { background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%); }
    [data-testid="stMetric"] { 
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-left: 4px solid #ff006e;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔍 Advanced Indicator Analysis & SMC Bias")

# Sidebar for input method selection
st.sidebar.markdown("### Input Method")
input_method = st.sidebar.radio("Choose input method:", ["Manual Input", "JSON Paste", "Example Data"])

analyzer = IndicatorAnalyzer()

if input_method == "Manual Input":
    st.markdown("### Manual Indicator Input")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rsi = st.slider("RSI", 0, 100, 50, step=1)
        adx = st.slider("ADX", 0, 100, 20, step=1)
        atr = st.number_input("ATR", 0.0, 0.1, 0.005, step=0.0001, format="%.6f")
    
    with col2:
        macd_hist = st.number_input("MACD Histogram", -0.001, 0.001, 0.00005, step=0.00001, format="%.6f")
        ema_fast = st.number_input("EMA Fast", 0.0, 10.0, 1.0850, step=0.0001, format="%.5f")
        ema_slow = st.number_input("EMA Slow", 0.0, 10.0, 1.0820, step=0.0001, format="%.5f")
    
    with col3:
        bb_upper = st.number_input("BB Upper", 0.0, 10.0, 1.0870, step=0.0001, format="%.5f")
        bb_mid = st.number_input("BB Mid", 0.0, 10.0, 1.0835, step=0.0001, format="%.5f")
        bb_lower = st.number_input("BB Lower", 0.0, 10.0, 1.0800, step=0.0001, format="%.5f")
    
    indicators = {
        "rsi": rsi,
        "macd_hist": macd_hist,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "adx": adx,
        "atr": atr,
        "bb_upper": bb_upper,
        "bb_mid": bb_mid,
        "bb_lower": bb_lower,
    }

elif input_method == "JSON Paste":
    st.markdown("### Paste JSON Data")
    json_input = st.text_area("JSON format:", value='{"rsi":65,"macd_hist":0.00005,"ema_fast":1.0850,"ema_slow":1.0820,"adx":28,"atr":0.0045,"bb_upper":1.0870,"bb_mid":1.0835,"bb_lower":1.0800}', height=100)
    
    try:
        indicators = json.loads(json_input)
    except:
        st.error("Invalid JSON format")
        indicators = None

else:  # Example Data
    st.markdown("### Using Example Data (Bullish Setup)")
    indicators = {
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
    st.info("📊 Using example bullish setup data")

# Mode selection
mode_col1, mode_col2, mode_col3 = st.columns(3)
with mode_col1:
    mode = st.radio("Analysis Mode:", ["regular", "scalp", "hft"], horizontal=True)
with mode_col2:
    current_price = st.number_input("Current Price (optional):", value=1.0845, step=0.0001, format="%.5f")

if indicators:
    # Run analysis
    analysis = analyzer.analyze(indicators, current_price=current_price, mode=mode)
    
    # ============ CONCLUSION (PROMINENT) ============
    conclusion = analysis["conclusion"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Bias", f"{conclusion['bias_emoji']} {conclusion['overall_bias']}")
    with col2:
        st.metric("🎯 Confidence", conclusion['confidence'])
    with col3:
        st.metric("⚡ Trend Strength", f"{conclusion['trend_score']:.1f}/10")
    with col4:
        st.metric("🏗️ Market Structure", conclusion['market_structure'])
    
    st.markdown("---")
    
    # ============ TABBED ANALYSIS ============
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Breakdown", "📋 Table", "⚡ Trend", "💰 SMC", "🎯 Zones"])
    
    with tab1:
        st.subheader("Indicator Breakdown")
        for indicator, data in analysis["breakdown"].items():
            with st.expander(f"**{indicator.upper()}** — {data['signal']}", expanded=False):
                st.write(f"**Value:** `{data['value']}`")
                st.write(f"**Interpretation:** {data['description']}")
    
    with tab2:
        st.subheader("Summary Table")
        df_table = st.dataframe(analysis["summary_table"], use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("Trend Strength Score")
        score = analysis["trend_strength_score"]
        st.progress(score / 10.0)
        st.metric("Score", f"{score:.1f}/10")
        
        if score >= 7:
            st.success("📈 **Strong trend detected.** Market has clear directional bias.")
        elif score >= 4:
            st.info("📊 **Developing trend.** Momentum is building.")
        else:
            st.warning("📉 **Weak trend.** Market is choppy/consolidating.")
    
    with tab4:
        st.subheader("Smart Money Concepts (SMC) Bias")
        smc = analysis["smc_bias"]
        
        st.markdown(f"#### 🏗️ Market Structure: **{smc['market_structure']}**")
        st.write(smc['market_structure_description'])
        
        st.markdown(f"#### 💧 Liquidity Direction: **{smc['liquidity_direction']}**")
        st.write(smc['liquidity_description'])
        
        st.markdown(f"#### 💰 Pricing Zone: **{smc['pricing_zone']}**")
        st.write(smc['pricing_description'])
    
    with tab5:
        st.subheader("Entry, SL, TP Zones (NOT FINANCIAL ADVICE)")
        zones = analysis["zones"]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success("### 🟢 ENTRY ZONE")
            st.write(f"**Zone:** `{zones['entry']['zone']}`")
            st.caption(zones['entry']['description'])
        
        with col2:
            st.error("### 🔴 STOP LOSS ZONE")
            st.write(f"**Zone:** `{zones['sl']['zone']}`")
            st.caption(zones['sl']['description'])
        
        with col3:
            st.warning("### 🟡 TAKE PROFIT ZONE")
            st.write(f"**Zone:** `{zones['tp']['zone']}`")
            st.caption(zones['tp']['description'])
    
    # ============ FULL REPORT ============
    with st.expander("📄 View Full Analysis Report"):
        report_text = analyzer.format_report(analysis)
        st.code(report_text, language="text")
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download Report",
                data=report_text,
                file_name=f"analysis_{mode}_{analysis['timestamp'][:10]}.txt",
                mime="text/plain"
            )
        with col2:
            st.download_button(
                "📊 Download JSON",
                data=json.dumps(analysis, indent=2),
                file_name=f"analysis_{mode}_{analysis['timestamp'][:10]}.json",
                mime="application/json"
            )

st.markdown("---")
st.markdown("""
### 📚 How to Use

1. **Select Input Method:** Manual, JSON paste, or example data
2. **Choose Analysis Mode:** Regular, Scalp, or HFT (adjusts recommendations)
3. **View Results:** Breakdown, summary table, trend score, SMC bias, entry/SL/TP zones
4. **Download Report:** Save as TXT or JSON for records

### ⚠️ Disclaimer
This analysis is **educational only**. Technical indicators are tools, not guarantees.
Always use proper risk management and position sizing. Do your own research.

---
""")
