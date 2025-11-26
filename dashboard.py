#!/usr/bin/env python3
"""TheBot — Premium Trading Dashboard (inspired by altBot design)"""
import os
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components

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
RUNTIME_STATE = os.path.join(BASE_DIR, "runtime_state.json")
WS_CLIENT_HTML_TEMPLATE = """
<div id="thebot-live" style="color:#fff;font-family:Segoe UI,Arial;">
    <h3 style="color:#00d9ff;">Live Feed</h3>
    <div id="feed"></div>
</div>
<script>
    const feed = document.getElementById('feed');
    const addr = 'ws://localhost:8765';
    const token = '%(token)s';
    try {
        const url = token && token.length > 0 ? addr + '?token=' + encodeURIComponent(token) : addr;
        const ws = new WebSocket(url);
        ws.onopen = () => { console.log('Connected to TheBot WS'); };
        ws.onmessage = (ev) => {
            try {
                const data = JSON.parse(ev.data);
                let html = '';
                if (data && typeof data === 'object') {
                    if (Object.keys(data).length > 0 && Object.values(data).every(v=>v && v.symbol)) {
                        for (const k of Object.keys(data)) {
                            const it = data[k];
                            html += `<div style="padding:8px;border-bottom:1px solid rgba(255,255,255,0.05)"><strong>${it.symbol}</strong> — ${it.signal} — ${it.prediction} (${(it.confidence*100).toFixed(1)}%)<div style="font-size:12px;color:#aaa">${it.ts}</div></div>`;
                        }
                    } else if (data.symbol) {
                        const it = data;
                        html = `<div style="padding:8px;border-bottom:1px solid rgba(255,255,255,0.05)"><strong>${it.symbol}</strong> — ${it.signal} — ${it.prediction} (${(it.confidence*100).toFixed(1)}%)<div style="font-size:12px;color:#aaa">${it.ts}</div></div>`;
                    }
                }
                feed.innerHTML = html || JSON.stringify(data);
            } catch(e) { console.error(e); }
        };
        ws.onclose = () => { console.log('WS closed'); };
    } catch(e) { console.error('WS init failed', e); }
</script>
"""

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


@st.cache_data
def load_runtime_state(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

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
    live_updates = st.checkbox("Enable auto-reload (live)", value=False)
    show_details = st.checkbox("Show trade details", value=True)
    show_backtest = st.checkbox("Show backtest metrics", value=True)
    time_filter = st.selectbox("Time filter", ["All", "Today", "This Week", "This Month"])

    ws_token_input = st.text_input("WS token (optional)", value=st.secrets.get("WS_SERVER_TOKEN", ""))

if live_updates:
    # inject a tiny JS refresher using the selected refresh_rate
    try:
        components.html(f"<script>setInterval(()=>location.reload(), {int(refresh_rate) * 1000});</script>", height=0)
    except Exception:
        pass

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

# Load runtime state (predictions & live signals)
runtime = load_runtime_state(RUNTIME_STATE)

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

# ============ LIVE PREDICTIONS & SIGNALS ============
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-header">🔮 Live Predictions & Signals</div>', unsafe_allow_html=True)
if not runtime:
    st.info("No live runtime state available. Run the bot to populate predictions.")
else:
    cols = st.columns(3)
    i = 0
    for sym, info in runtime.items():
        col = cols[i % 3]
        with col:
            pred = info.get("prediction", "NEUTRAL")
            conf = info.get("confidence", 0.0)
            sig = info.get("signal", "HOLD")
            price = info.get("last_price")
            ts = info.get("ts")
            badge = f"<div class=\"symbol-badge\">{sym}</div>"
            st.markdown(badge, unsafe_allow_html=True)
            st.write(f"**Signal:** <span class=\"signal-{'buy' if sig=='BUY' else 'sell' if sig=='SELL' else 'hold'}\">{sig}</span>")
            st.write(f"**Prediction:** {pred}  —  Confidence: {conf:.2f}")
            # show model probabilities if available
            prob_up = info.get("prob_up")
            prob_down = info.get("prob_down")
            if prob_up is not None or prob_down is not None:
                pu = float(prob_up) if prob_up is not None else 0.0
                pdn = float(prob_down) if prob_down is not None else 0.0
                st.write(f"**P(up):** {pu:.2f}  —  **P(down):** {pdn:.2f}")
            st.write(f"**Price:** {price}")
            st.caption(f"Updated: {ts}")
            if show_details:
                with st.expander("Indicators"):
                    st.json(info.get("indicators", {}))
        i += 1
st.markdown('</div>', unsafe_allow_html=True)

# Inject the WS client HTML as a small live feed (non-intrusive)
try:
    token_escaped = ws_token_input.replace('"', '\\"') if ws_token_input else ""
    html = WS_CLIENT_HTML_TEMPLATE % {"token": token_escaped}
    components.html(html, height=220)
except Exception:
    pass

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

    st.markdown("---")
    st.subheader("Send test Email")
    with st.form("email_test"):
        email_from = st.text_input("From (or set in secrets)", value=st.secrets.get("EMAIL_FROM", ""))
        email_to = st.text_input("To (or set in secrets)", value=st.secrets.get("EMAIL_TO", ""))
        email_pass = st.text_input("Password (or set in secrets)", value=st.secrets.get("EMAIL_PASSWORD", ""), type="password")
        email_subj = st.text_input("Subject", value="Test from TheBot dashboard")
        email_body = st.text_area("Body", value="This is a test")
        send_email = st.form_submit_button("Send Test Email")
        if send_email:
            if not (email_from and email_pass and email_to):
                st.error("Please provide From/Password/To (or set in Streamlit secrets)")
            else:
                try:
                    import smtplib
                    from email.mime.text import MIMEText
                    msg = MIMEText(email_body)
                    msg["Subject"] = email_subj
                    msg["From"] = email_from
                    msg["To"] = email_to
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                        s.login(email_from, email_pass)
                        s.sendmail(email_from, email_to, msg.as_string())
                    st.success("Email sent (check inbox)")
                except Exception as e:
                    st.error(f"Email failed: {e}")

with st.expander("Generate proposed action (download JSON)"):
    st.write("Create a JSON file that can be placed in your bot's project folder as `proposed_changes.json` to instruct the bot to execute actions.")
    sample = [{
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": "order_send",
        "symbol": "EURUSD",
        "signal": "BUY",
        "comment": "from-dashboard",
        "indicators": {}
    }]
    st.json(sample)
    st.download_button("Download proposed_changes.json", data=json.dumps(sample, indent=2), file_name="proposed_changes.json", mime="application/json")

    st.markdown("---")
    st.subheader("Create modify_sl or close_position proposal")
    with st.form("proposal_form"):
        p_action = st.selectbox("Action", ["modify_sl", "close_position"], index=0)
        p_position = st.text_input("Position ticket (numeric)")
        p_new_sl = st.text_input("New SL (price) — required for modify_sl", value="")
        submitted = st.form_submit_button("Generate proposal JSON")
        if submitted:
            try:
                pos_i = int(p_position)
            except Exception:
                st.error("Invalid position id")
                pos_i = None
            if p_action == "modify_sl" and (not p_new_sl or pos_i is None):
                st.error("Provide numeric position and new_sl for modify_sl")
            else:
                obj = {"ts": datetime.now(timezone.utc).isoformat(), "action": p_action, "position": pos_i}
                if p_action == "modify_sl":
                    obj["new_sl"] = float(p_new_sl)
                st.json(obj)
                st.download_button("Download proposal", data=json.dumps([obj], indent=2), file_name="proposed_changes.json", mime="application/json")

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
