#!/usr/bin/env python3
"""Streamlit dashboard for TheBot performance and backtest results — Enhanced for live trading.

Run locally:
    .\.venv\Scripts\Activate.ps1
    pip install streamlit plotly pandas
    streamlit run dashboard.py

The dashboard reads `performance_log.csv` (JSON-per-line rows) and
`backtest_results.json` (from `backtest_engine.py --output`) if present.
"""
import os
import json
import pandas as pd
try:
    import streamlit as st
except Exception:
    print("Streamlit is not installed in the current environment.\nInstall with: pip install streamlit plotly")
    raise

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:
    print("Plotly is not installed in the current environment.\nInstall with: pip install plotly")
    raise
from datetime import datetime

BASE_DIR = os.path.dirname(__file__) or "."
PERF_LOG = os.path.join(BASE_DIR, "performance_log.csv")
BACKTEST_JSON = os.path.join(BASE_DIR, "backtest_results.json")

st.set_page_config(page_title="TheBot Dashboard", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    .big-metric { font-size: 2em; font-weight: bold; }
    .status-live { color: #00ff00; font-weight: bold; }
    .status-paused { color: #ffaa00; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 TheBot — Performance Dashboard")

# Sidebar
st.sidebar.header("📊 Dashboard Controls")
use_perf = st.sidebar.checkbox("📝 Load performance_log.csv", value=True)
use_backtest = st.sidebar.checkbox("📊 Load backtest_results.json", value=True)
show_raw_data = st.sidebar.checkbox("Show Raw Data", value=False)

@st.cache_data
def load_perf_log(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        lines = open(path, "r", encoding="utf-8").read().splitlines()
        if lines and lines[0].startswith("timestamp"):
            lines = lines[1:]
        rows = [json.loads(l) for l in lines if l.strip()]
        df = pd.DataFrame(rows)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception:
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()

@st.cache_data
def load_backtest(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

perf_df = load_perf_log(PERF_LOG) if use_perf else pd.DataFrame()
backtest = load_backtest(BACKTEST_JSON) if use_backtest else None

# === TOP STATUS METRICS ===
if not perf_df.empty:
    st.markdown("---")
    latest_signal = perf_df.iloc[-1] if len(perf_df) > 0 else None
    total_pnl = float(perf_df["pnl"].fillna(0).sum()) if "pnl" in perf_df.columns else 0.0
    total_trades = len(perf_df[perf_df["signal"].isin(["BUY", "SELL"])]) if "signal" in perf_df.columns else 0
    win_count = len(perf_df[(perf_df["signal"].isin(["BUY", "SELL"])) & (perf_df["pnl"].fillna(0) > 0)]) if "pnl" in perf_df.columns else 0
    
    metric_cols = st.columns(5)
    
    with metric_cols[0]:
        pnl_color = "green" if total_pnl >= 0 else "red"
        st.metric("💰 Total PnL", f"${total_pnl:,.2f}", delta=f"{'Profit' if total_pnl > 0 else 'Loss'}", delta_color="normal" if total_pnl >= 0 else "inverse")
    
    with metric_cols[1]:
        st.metric("📊 Total Trades", total_trades)
    
    with metric_cols[2]:
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        st.metric("🎯 Win Rate", f"{win_rate:.1f}%", delta=f"{win_count}W / {total_trades-win_count}L")
    
    with metric_cols[3]:
        latest_time = latest_signal["timestamp"] if "timestamp" in latest_signal and pd.notna(latest_signal["timestamp"]) else "N/A"
        time_str = str(latest_time)[-19:-5] if latest_time != "N/A" else "N/A"
        st.metric("⏰ Last Signal", time_str)
    
    with metric_cols[4]:
        latest_sym = latest_signal["symbol"] if "symbol" in latest_signal else "N/A"
        st.metric("📌 Last Symbol", latest_sym)
else:
    st.warning("⚠️ No performance data yet. Run TheBot to populate performance_log.csv")

st.markdown("---")

# === MAIN CONTENT ===
col1, col2 = st.columns((2, 1))

with col1:
    st.subheader("📈 Equity Curve & Performance")
    
    if not perf_df.empty:
        df = perf_df.copy()
        df = df.sort_values("timestamp")
        
        if "pnl" in df.columns:
            df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
            df["equity"] = 10000.0 + df["pnl"].cumsum()
            
            # Equity curve with Plotly
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(
                x=df["timestamp"], y=df["equity"],
                mode='lines+markers', name='Equity',
                line=dict(color='#00ff00', width=2),
                marker=dict(size=4),
                fill='tozeroy', fillcolor='rgba(0,255,0,0.1)',
                hovertemplate='<b>Time:</b> %{x}<br><b>Equity:</b> $%{y:,.2f}<extra></extra>'
            ))
            fig_eq.update_layout(
                title="Account Equity Over Time",
                xaxis_title="Time", yaxis_title="Equity ($)",
                hovermode='x unified', template='plotly_dark',
                height=400, margin=dict(l=50, r=50, t=40, b=40)
            )
            st.plotly_chart(fig_eq, use_container_width=True)
        else:
            st.info("No PnL values to display equity curve.")
    else:
        st.info("No performance log found.")

    st.subheader("📋 Recent Signals & Trades")
    if not perf_df.empty:
        display_df = perf_df.sort_values("timestamp", ascending=False).head(25).copy()
        
        # Clean up display
        if "timestamp" in display_df.columns:
            display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        st.dataframe(display_df, use_container_width=True, height=400)
    else:
        st.info("No signals to display.")

with col2:
    st.subheader("📊 Trading Summary")
    
    if not perf_df.empty:
        total = len(perf_df)
        buys = len(perf_df[perf_df["signal"] == "BUY"]) if "signal" in perf_df.columns else 0
        sells = len(perf_df[perf_df["signal"] == "SELL"]) if "signal" in perf_df.columns else 0
        holds = len(perf_df[perf_df["signal"] == "HOLD"]) if "signal" in perf_df.columns else 0
        
        st.metric("🔵 Total Signals", total)
        st.metric("📈 Buy Signals", buys)
        st.metric("📉 Sell Signals", sells)
        st.metric("⏸️ Hold Signals", holds)
        
        if "pnl" in perf_df.columns:
            total_pnl = float(perf_df["pnl"].fillna(0).sum())
            avg_pnl = total_pnl / total if total > 0 else 0
            st.metric("Avg PnL per Signal", f"${avg_pnl:.2f}")
    
    st.subheader("📈 Backtest Summary")
    if backtest is None:
        st.info("No backtest results found. Run `backtest_engine.py --output backtest_results.json` to generate.")
    else:
        metrics = backtest.get("metrics", {})
        if metrics:
            st.json(metrics)
        else:
            st.info("No backtest metrics available.")

st.markdown("---")

# === SIGNAL DISTRIBUTION ===
st.subheader("📊 Signal Distribution by Symbol")
if not perf_df.empty and "symbol" in perf_df.columns:
    signal_dist = perf_df.groupby(["symbol", "signal"]).size().reset_index(name="count")
    fig_dist = px.bar(signal_dist, x="symbol", y="count", color="signal", barmode="group",
                      title="Signals by Symbol", template="plotly_dark")
    st.plotly_chart(fig_dist, use_container_width=True)

st.markdown("---")

# === RAW DATA ===
if show_raw_data:
    st.subheader("🔍 Raw Performance Data")
    if not perf_df.empty:
        st.write(perf_df)
    st.subheader("🔍 Raw Backtest Data")
    if backtest:
        st.json(backtest)

st.markdown("---")
st.caption("TheBot Dashboard — Real-time performance monitoring | Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
