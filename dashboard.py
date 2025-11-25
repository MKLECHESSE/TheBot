#!/usr/bin/env python3
"""Streamlit dashboard for TheBot performance and backtest results.

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
except Exception:
    print("Plotly is not installed in the current environment.\nInstall with: pip install plotly")
    raise
from datetime import datetime

BASE_DIR = os.path.dirname(__file__) or "."
PERF_LOG = os.path.join(BASE_DIR, "performance_log.csv")
BACKTEST_JSON = os.path.join(BASE_DIR, "backtest_results.json")

st.set_page_config(page_title="TheBot Dashboard", layout="wide")
st.title("TheBot — Performance Dashboard")

# Sidebar
st.sidebar.header("Data Sources")
use_perf = st.sidebar.checkbox("Load performance_log.csv", value=True)
use_backtest = st.sidebar.checkbox("Load backtest_results.json", value=True)

@st.cache_data
def load_perf_log(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    # Try to read as CSV first
    try:
        # file contains a header row, then JSON per-line rows
        lines = open(path, "r", encoding="utf-8").read().splitlines()
        # if the first line looks like a CSV header, skip it
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

col1, col2 = st.columns((2, 1))

with col1:
    st.subheader("Equity / Signals")
    if perf_df.empty:
        st.info("No performance log found. Run TheBot to populate `performance_log.csv` or uncheck this source.")
    else:
        # Build equity curve if PnL present (assumes one-by-line cumulative isn't stored)
        # We'll compute a cumulative PnL over logged trades if pnl present
        df = perf_df.copy()
        # if indicators column is string, try parse
        if "indicators" in df.columns:
            # indicators may be dict or string
            def try_parse(x):
                if isinstance(x, str):
                    try:
                        return json.loads(x)
                    except Exception:
                        return {}
                return x
            df["indicators_parsed"] = df["indicators"].apply(try_parse)
        if "pnl" in df.columns:
            df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
            df["equity"] = df["pnl"].cumsum()
            fig = px.line(df, x="timestamp", y="equity", title="Equity Curve (cumulative PnL)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No PnL values in performance log to build equity curve.")

    st.subheader("Recent Signals")
    if not perf_df.empty:
        show_count = st.slider("Rows to show", 5, 200, 25)
        st.dataframe(perf_df.sort_values("timestamp", ascending=False).head(show_count))

with col2:
    st.subheader("Summary")
    if not perf_df.empty:
        total = len(perf_df)
        buys = len(perf_df[perf_df["signal"] == "BUY"]) if "signal" in perf_df.columns else 0
        sells = len(perf_df[perf_df["signal"] == "SELL"]) if "signal" in perf_df.columns else 0
        holds = len(perf_df[perf_df["signal"] == "HOLD"]) if "signal" in perf_df.columns else 0
        st.metric("Total rows", total)
        st.metric("Buy signals", buys)
        st.metric("Sell signals", sells)
        st.metric("Hold signals", holds)
        if "pnl" in perf_df.columns:
            total_pnl = float(perf_df["pnl"].fillna(0).sum())
            st.metric("Total PnL", f"{total_pnl:.2f}")

    st.subheader("Backtest Summary")
    if backtest is None:
        st.info("No backtest_results.json found. Run `backtest_engine.py` with --output to generate one.")
    else:
        metrics = backtest.get("metrics", {})
        st.write(metrics)
        # Equity curve from simulated trades if present
        trades = backtest.get("trades", [])
        if trades:
            eq = [metrics.get("final_balance", 0)]
            # scenario: show trade returns over time — skip for now
            st.write(f"Trades simulated: {len(trades)}")

st.markdown("---")
st.subheader("Notes & Actions")
st.markdown(
    "- Use `--once --dry-run` to test the bot and generate `performance_log.csv`\n"
    "- Use `python backtest_engine.py <csv> classic --output backtest_results.json` to run backtests\n"
    "- To run the dashboard: `streamlit run dashboard.py`"
)

st.caption("TheBot dashboard — quick visuals for testing and backtesting")
