#!/usr/bin/env python3
"""TheBot — Premium Trading Dashboard (inspired by altBot design)"""
import os
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="TheBot Trading Dashboard", layout="wide", initial_sidebar_state="expanded")

# ============ CUSTOM CSS ============
st.markdown("""
<style>
    * { font-family: 'Segoe UI', sans-serif; }
    body { background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%); }
    
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #ff006e;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    
    .card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #2a2a4e;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        margin: 12px 0;
    }
    
    .card-header {
        color: #00d9ff;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 16px;
        border-bottom: 2px solid #ff006e;
        padding-bottom: 12px;
    }
    
    .metric-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 16px;
        margin: 12px 0;
    }
    
    .metric-box {
        background: rgba(255, 0, 110, 0.1);
        padding: 16px;
        border-radius: 10px;
        border-left: 3px solid #ff006e;
        text-align: center;
    }
    
    .metric-label {
        color: #888;
        font-size: 12px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    
    .metric-value {
        color: #00ff88;
        font-size: 24px;
        font-weight: 700;
    }
    
    .metric-value.negative { color: #ff4444; }
    .metric-value.positive { color: #00ff88; }
    
    .symbol-badge {
        display: inline-block;
        background: #ff006e;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin: 4px;
    }
    
    .signal-buy { color: #00ff88; font-weight: 600; }
    .signal-sell { color: #ff4444; font-weight: 600; }
    .signal-hold { color: #ffaa00; font-weight: 600; }
    
    h1 { color: #00d9ff; text-shadow: 0 0 10px rgba(0,217,255,0.3); margin-bottom: 24px; }
    h2 { color: #00d9ff; margin-top: 24px; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(__file__) or "."
PERF_LOG = os.path.join(BASE_DIR, "performance_log.csv")
BACKTEST_JSON = os.path.join(BASE_DIR, "backtest_results.json")

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
    except:
        return pd.DataFrame()

@st.cache_data
def load_backtest(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

# Load data
perf_df = load_perf_log(PERF_LOG)
backtest = load_backtest(BACKTEST_JSON)

# ============ HEADER ============
st.title("🤖 TheBot Trading Dashboard")
st.markdown("---")

# ============ SIDEBAR ============
with st.sidebar:
    st.header("⚙️ Controls")
    refresh_rate = st.select_slider("Auto-refresh interval (seconds)", [5, 10, 30, 60], value=30)
    show_details = st.checkbox("Show trade details", value=True)
    show_backtest = st.checkbox("Show backtest metrics", value=True)
    time_filter = st.selectbox("Time filter", ["All", "Today", "This Week", "This Month"])

# ============ MAIN METRICS CARD ============
if not perf_df.empty:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">💰 Account Summary</div>', unsafe_allow_html=True)
    
    total_pnl = float(perf_df["pnl"].fillna(0).sum()) if "pnl" in perf_df.columns else 0.0
    total_trades = len(perf_df[perf_df["signal"].isin(["BUY", "SELL"])]) if "signal" in perf_df.columns else 0
    win_count = len(perf_df[(perf_df["signal"].isin(["BUY", "SELL"])) & (perf_df["pnl"].fillna(0) > 0)]) if "pnl" in perf_df.columns else 0
    balance = 10000.0 + total_pnl
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Balance", f"${balance:,.2f}", f"${total_pnl:+,.2f}")
    
    with col2:
        st.metric("Total Trades", total_trades, f"{win_count}W/{total_trades-win_count}L" if total_trades > 0 else "0")
    
    with col3:
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%", f"{win_count} wins")
    
    with col4:
        latest_time = perf_df.iloc[-1]["timestamp"] if "timestamp" in perf_df.columns else "N/A"
        time_str = str(latest_time)[-19:-5] if pd.notna(latest_time) else "N/A"
        st.metric("Last Signal", time_str, "")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============ CHARTS ROW ============
col_left, col_right = st.columns((1.5, 1))

with col_left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">📈 Equity Curve</div>', unsafe_allow_html=True)
    
    if not perf_df.empty and "pnl" in perf_df.columns:
        df = perf_df.copy().sort_values("timestamp")
        df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
        df["equity"] = 10000.0 + df["pnl"].cumsum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["equity"],
            fill='tozeroy', fillcolor='rgba(0,255,136,0.2)',
            line=dict(color='#00ff88', width=3),
            hovertemplate='<b>%{x|%H:%M:%S}</b><br>Equity: $%{y:,.0f}<extra></extra>'
        ))
        fig.update_layout(
            xaxis_title="", yaxis_title="Equity ($)",
            template="plotly_dark", hovermode='x unified',
            height=400, margin=dict(l=40, r=20, t=20, b=20),
            showlegend=False
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity data available")
    
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">🎯 Signal Distribution</div>', unsafe_allow_html=True)
    
    if not perf_df.empty and "signal" in perf_df.columns:
        signal_counts = perf_df["signal"].value_counts()
        colors = {"BUY": "#00ff88", "SELL": "#ff4444", "HOLD": "#ffaa00"}
        
        fig = go.Figure(data=[go.Pie(
            labels=signal_counts.index, 
            values=signal_counts.values,
            marker=dict(colors=[colors.get(s, "#666") for s in signal_counts.index]),
            hole=0.3,
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>'
        )])
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signals to display")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============ POSITIONS & TRADES ============
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-header">📊 Recent Trades</div>', unsafe_allow_html=True)

if not perf_df.empty:
    df_display = perf_df.sort_values("timestamp", ascending=False).head(15).copy()
    
    if "timestamp" in df_display.columns:
        df_display["Time"] = df_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        df_display["Time"] = "N/A"
    
    # Build display table
    display_cols = ["Time"]
    if "symbol" in df_display.columns:
        display_cols.append("symbol")
    if "signal" in df_display.columns:
        display_cols.append("signal")
    if "pnl" in df_display.columns:
        display_cols.append("pnl")
    if "reason" in df_display.columns:
        display_cols.append("reason")
    
    df_display = df_display[display_cols]
    df_display = df_display.rename(columns={
        "symbol": "Symbol",
        "signal": "Signal",
        "pnl": "P&L",
        "reason": "Reason"
    })
    
    st.dataframe(df_display, use_container_width=True, height=300, hide_index=True)
else:
    st.info("No trade data available")

st.markdown('</div>', unsafe_allow_html=True)

# ============ ALERTS & ACTIONS ============
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-header">🚨 Alerts & Actions</div>', unsafe_allow_html=True)

with st.expander("Send Telegram / Email Alert"):
    tg_token = st.text_input("Telegram bot token (or set in Secrets)", value=st.secrets.get("TELEGRAM_BOT_TOKEN", ""))
    tg_chat = st.text_input("Telegram chat id (or set in Secrets)", value=st.secrets.get("TELEGRAM_CHAT_ID", ""))
    alert_msg = st.text_area("Message", value="Test alert from TheBot dashboard")
    if st.button("Send Telegram Alert"):
        if not tg_token or not tg_chat:
            st.error("Provide Telegram token and chat id (or set in Streamlit secrets)")
        else:
            import requests
            try:
                r = requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", data={"chat_id": tg_chat, "text": alert_msg}, timeout=10)
                if r.ok:
                    st.success("Telegram alert sent")
                else:
                    st.error(f"Telegram failed: {r.text}")
            except Exception as e:
                st.error(f"Telegram exception: {e}")

with st.expander("Generate proposed action (download JSON)"):
    st.write("Create a JSON file that can be placed in your bot's project folder as `proposed_changes.json` to instruct the bot to execute actions.")
    sample = [{
        "ts": datetime.utcnow().isoformat(),
        "action": "order_send",
        "symbol": "EURUSD",
        "signal": "BUY",
        "comment": "from-dashboard",
        "indicators": {}
    }]
    st.json(sample)
    st.download_button("Download proposed_changes.json", data=json.dumps(sample, indent=2), file_name="proposed_changes.json", mime="application/json")

st.markdown('</div>', unsafe_allow_html=True)

# ============ SYMBOL BREAKDOWN ============
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-header">📍 Performance by Symbol</div>', unsafe_allow_html=True)

if not perf_df.empty and "symbol" in perf_df.columns:
    symbol_stats = perf_df.groupby("symbol").agg({
        "pnl": ["sum", "count"],
        "signal": lambda x: (x == "BUY").sum()
    }).round(2)
    symbol_stats.columns = ["Total PnL", "Trades", "Buys"]
    symbol_stats["Win Rate"] = (symbol_stats["Buys"] / symbol_stats["Trades"] * 100).round(1)
    
    st.dataframe(symbol_stats, use_container_width=True)
else:
    st.info("No symbol data available")

st.markdown('</div>', unsafe_allow_html=True)

# ============ BACKTEST SUMMARY ============
if show_backtest and backtest:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">📈 Backtest Summary</div>', unsafe_allow_html=True)
    
    metrics = backtest.get("metrics", {})
    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Return", f"{metrics.get('total_return_pct', 0):.2f}%")
        with col2:
            st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
        with col3:
            st.metric("Max Drawdown", f"{metrics.get('max_drawdown_pct', 0):.2f}%")
        with col4:
            st.metric("Trades", metrics.get('total_trades', 0))
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============ FOOTER ============
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | TheBot v1.0")
