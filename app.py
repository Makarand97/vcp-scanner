"""
VCP Scanner v2 — Optimized Web Application
Features:
  - Live scan with inline price charts (click stock name)
  - Multi-date backtest with trailing stop simulation
  - Parameter auto-optimization
  - Strategy guide
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from scanner import (
    get_nifty500_symbols, fetch_data,
    compute_all_indicators, compute_rs_ratings,
    run_scan, run_backtest, run_multi_date_backtest,
    optimize_parameters, get_chart_data,
    DEFAULT_PARAMS,
)

# ─────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────

st.set_page_config(page_title="VCP Scanner v2", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .stPopover { max-width: 700px !important; }
    div[data-testid="stMetric"] { background: #f8f9fa; padding: 8px 12px; border-radius: 8px; }
    .winner { color: #16a34a; font-weight: bold; }
    .loser { color: #dc2626; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("📈 VCP Scanner v2 — Optimized")
st.caption("Minervini VCP with breakout entry, trailing stop, and auto-optimization")

# ─────────────────────────────────
# SIDEBAR
# ─────────────────────────────────

with st.sidebar:
    st.header("⚙️ Parameters")

    with st.expander("Trend Template", expanded=False):
        rs_min = st.slider("Min RS Rating", 50, 95, 80, key="rs")
        high_pct = st.slider("Max % from 52W High", 5, 30, 15, key="h52")
        low_mult = st.slider("Min % above 52W Low", 10, 80, 30, key="l52")
        sma200_days = st.slider("SMA200 rising (days)", 15, 100, 22, key="s200d")

    with st.expander("VCP Detection", expanded=False):
        base_min = st.slider("Min Base Days", 10, 30, 15, key="bmin")
        base_max = st.slider("Max Base Days", 60, 200, 120, key="bmax")
        base_depth = st.slider("Max Base Depth %", 15, 40, 30, key="bdep")
        min_c = st.slider("Min Contractions", 2, 4, 2, key="mc")
        zigzag = st.slider("Zigzag Threshold %", 2, 6, 3, key="zz")
        last_c = st.slider("Max Last Contraction %", 3, 15, 10, key="lc")
        tight = st.slider("Max 10-day Range %", 4, 18, 10, key="tght")
        pivot_p = st.slider("Max Pivot Distance %", 3, 15, 10, key="pp")

    with st.expander("Volume & Trailing Stop", expanded=False):
        vol_d = st.slider("Volume Decline Ratio", 0.50, 1.00, 0.80, 0.05, key="vd")
        trail_trigger = st.slider("Trail Trigger %", 3, 10, 5, key="tt")
        trail_pct = st.slider("Trail Distance %", 4, 15, 8, key="tp")

    params = {
        "rs_min": rs_min,
        "high_52w_pct": (100 - high_pct) / 100,
        "low_52w_pct": 1 + low_mult / 100,
        "sma200_trend_days": sma200_days,
        "base_min_days": base_min,
        "base_max_days": base_max,
        "base_max_depth": base_depth / 100,
        "min_contractions": min_c,
        "max_contractions": 6,
        "zigzag_threshold": zigzag / 100,
        "last_contraction_max": last_c / 100,
        "vol_decline_ratio": vol_d,
        "tightness_max_pct": tight,
        "pivot_proximity_pct": pivot_p,
        "trail_trigger_pct": trail_trigger,
        "trail_pct": trail_pct,
    }

    if st.button("🔄 Reset to Optimized Defaults"):
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────
# CACHING
# ─────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(symbols_tuple, end_date, days):
    return fetch_data(list(symbols_tuple), end_date, days)

@st.cache_data(ttl=86400, show_spinner=False)
def cached_symbols():
    return get_nifty500_symbols()


# ─────────────────────────────────
# CHART BUILDER
# ─────────────────────────────────

def build_chart(df: pd.DataFrame, symbol: str, pivot: float = None, stop: float = None):
    """Build a 1-year price + volume chart with SMAs and VCP annotations."""
    chart_df = get_chart_data(df, 252)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=chart_df.index,
        open=chart_df["Open"], high=chart_df["High"],
        low=chart_df["Low"], close=chart_df["Close"],
        name="Price", increasing_line_color="#16a34a", decreasing_line_color="#dc2626",
    ), row=1, col=1)

    # SMAs
    for col, color, name in [
        ("SMA_50", "#f59e0b", "SMA 50"),
        ("SMA_150", "#3b82f6", "SMA 150"),
        ("SMA_200", "#8b5cf6", "SMA 200"),
    ]:
        if col in chart_df.columns:
            fig.add_trace(go.Scatter(
                x=chart_df.index, y=chart_df[col],
                line=dict(color=color, width=1.5), name=name,
            ), row=1, col=1)

    # Pivot line
    if pivot:
        fig.add_hline(y=pivot, line_dash="dash", line_color="green",
                       annotation_text=f"Pivot ₹{pivot}", row=1, col=1)

    # Stop-loss line
    if stop:
        fig.add_hline(y=stop, line_dash="dash", line_color="red",
                       annotation_text=f"SL ₹{stop}", row=1, col=1)

    # Volume
    colors = ["#16a34a" if c >= o else "#dc2626"
              for c, o in zip(chart_df["Close"], chart_df["Open"])]
    fig.add_trace(go.Bar(
        x=chart_df.index, y=chart_df["Volume"],
        marker_color=colors, name="Volume", showlegend=False,
    ), row=2, col=1)

    fig.update_layout(
        height=420, margin=dict(l=0, r=0, t=30, b=0),
        title=f"{symbol} — 1 Year",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        template="plotly_white",
    )
    fig.update_xaxes(type="category", nticks=12, row=2, col=1)
    fig.update_xaxes(type="category", showticklabels=False, row=1, col=1)

    return fig


# ─────────────────────────────────
# TABS
# ─────────────────────────────────

tab_live, tab_bt, tab_multi, tab_opt, tab_guide = st.tabs([
    "🔍 Live Scan", "📊 Single Backtest", "📈 Multi-Date Backtest",
    "🎯 Optimize", "📖 Guide"
])


# ═══════════════════════════════════
# TAB 1: LIVE SCAN
# ═══════════════════════════════════

with tab_live:
    st.subheader("Live Scan — Today")
    st.info("Click on any stock symbol to see its 1-year chart with pivot & stop-loss levels.")

    if st.button("🚀 Run Live Scan", type="primary", key="live_btn"):
        symbols = cached_symbols()
        st.write(f"Universe: **{len(symbols)} stocks**")

        with st.spinner("Fetching data (3-8 min on first run, cached after)..."):
            today = datetime.now().strftime("%Y-%m-%d")
            stock_data = cached_fetch(tuple(symbols), today, 450)
            st.write(f"Loaded: **{len(stock_data)} stocks** with 200+ days history")

        with st.spinner("Computing RS Ratings & running scan..."):
            close_dict = {s: d["Close"] for s, d in stock_data.items()}
            rs_ratings = compute_rs_ratings(close_dict)
            results = run_scan(stock_data, rs_ratings, params)

        if not results:
            st.warning("No stocks passed. Try relaxing parameters.")
        else:
            st.success(f"**{len(results)} stocks** passed all filters!")

            for i, stock in enumerate(results):
                sym_yf = stock["yf_symbol"]
                sym = stock["symbol"]

                col_chart, col_info = st.columns([1, 3])

                with col_chart:
                    # Floating chart on click
                    with st.popover(f"📈 {sym}"):
                        if sym_yf in stock_data:
                            fig = build_chart(
                                stock_data[sym_yf], sym,
                                pivot=stock.get("pivot_high"),
                                stop=stock.get("stop_loss"),
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.write("Chart unavailable")

                with col_info:
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    c1.metric("Score", stock["vcp_score"])
                    c2.metric("RS", stock["rs_rating"])
                    c3.metric("Close", f"₹{stock['close']}")
                    c4.metric("Entry", f"₹{stock['entry_price']}")
                    c5.metric("Stop-Loss", f"₹{stock['stop_loss']}")
                    c6.metric("Risk", f"{stock['stop_loss_pct']}%")

                if i < len(results) - 1:
                    st.divider()


# ═══════════════════════════════════
# TAB 2: SINGLE BACKTEST
# ═══════════════════════════════════

with tab_bt:
    st.subheader("Single Date Backtest")
    st.info("Scan as of a past date → enter on breakout → trailing stop → see actual returns.")

    col_d, col_n, col_b = st.columns([2, 1, 1])
    with col_d:
        scan_date = st.date_input(
            "Scan Date", value=datetime.now() - timedelta(days=75),
            max_value=datetime.now() - timedelta(days=10),
            min_value=datetime(2023, 6, 1), key="bt_date",
        )
    with col_n:
        top_n = st.number_input("Top N stocks", 3, 10, 5, key="topn")
    with col_b:
        st.write("")
        st.write("")
        run_single = st.button("📊 Run Backtest", type="primary", key="bt_btn")

    if run_single:
        scan_ts = pd.Timestamp(scan_date)
        end_fetch = scan_ts + timedelta(days=80)
        symbols = cached_symbols()

        with st.spinner("Fetching data..."):
            stock_data = cached_fetch(tuple(symbols), end_fetch.strftime("%Y-%m-%d"), 450)

        # Trim for scan
        scan_data = {s: d[d.index <= scan_ts] for s, d in stock_data.items() if len(d[d.index <= scan_ts]) >= 200}

        with st.spinner("Running scan + backtest..."):
            close_dict = {s: d["Close"] for s, d in scan_data.items()}
            rs_ratings = compute_rs_ratings(close_dict)

            # Compute vol50 for breakout detection
            scan_data_ind = {}
            for s, d in scan_data.items():
                try:
                    scan_data_ind[s] = compute_all_indicators(d)
                except:
                    pass

            results = run_scan(scan_data, rs_ratings, params)

            # Attach vol50
            for r in results:
                sym = r["yf_symbol"]
                if sym in scan_data_ind:
                    v50 = scan_data_ind[sym]["VOL_50"].iloc[-1]
                    r["vol50_at_scan"] = v50 if not pd.isna(v50) else 0

            trades = run_backtest(
                results, stock_data, scan_ts,
                top_n=top_n, max_hold=40,
                trail_trigger=params.get("trail_trigger_pct", 5),
                trail_pct=params.get("trail_pct", 8),
            )

        if not trades:
            st.warning("No trades triggered. Try different date or parameters.")
        else:
            st.success(f"**{len(trades)} trades** executed from {len(results)} candidates")

            # Summary metrics
            returns = [t["return_pct"] for t in trades]
            winners = [r for r in returns if r > 0]

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Avg Return", f"{np.mean(returns):.1f}%")
            mc2.metric("Win Rate", f"{len(winners)/len(returns)*100:.0f}%")
            mc3.metric("Best", f"{max(returns):.1f}%")
            mc4.metric("Worst", f"{min(returns):.1f}%")

            # Trade table
            trade_df = pd.DataFrame(trades)
            display_cols = [
                "symbol", "entry_date", "entry_type", "entry_price",
                "initial_stop", "stop_loss_pct", "vcp_score", "rs_rating",
                "exit_price", "exit_day", "exit_reason", "return_pct",
                "max_gain_pct",
                "buy_hold_5d", "buy_hold_10d", "buy_hold_20d", "buy_hold_40d",
            ]
            avail = [c for c in display_cols if c in trade_df.columns]
            st.dataframe(
                trade_df[avail].rename(columns={
                    "symbol": "Symbol", "entry_date": "Entry", "entry_type": "Type",
                    "entry_price": "Entry ₹", "initial_stop": "SL ₹",
                    "stop_loss_pct": "SL%", "vcp_score": "Score", "rs_rating": "RS",
                    "exit_price": "Exit ₹", "exit_day": "Day", "exit_reason": "Reason",
                    "return_pct": "Return%", "max_gain_pct": "Max Gain%",
                    "buy_hold_5d": "B&H 5D", "buy_hold_10d": "B&H 10D",
                    "buy_hold_20d": "B&H 20D", "buy_hold_40d": "B&H 40D",
                }),
                use_container_width=True, hide_index=True,
            )

            # Charts for each trade
            st.subheader("Trade Charts")
            for t in trades:
                sym_yf = t["yf_symbol"]
                with st.popover(f"📈 {t['symbol']} → {t['return_pct']}%"):
                    if sym_yf in stock_data:
                        fig = build_chart(stock_data[sym_yf], t["symbol"])
                        fig.add_hline(y=t["entry_price"], line_dash="dot", line_color="blue",
                                       annotation_text=f"Entry ₹{t['entry_price']}")
                        fig.add_hline(y=t["initial_stop"], line_dash="dot", line_color="red",
                                       annotation_text=f"SL ₹{t['initial_stop']}")
                        st.plotly_chart(fig, use_container_width=True)

            # Strategy comparison
            st.subheader("Trailing Stop vs Buy & Hold")
            comp_data = []
            for t in trades:
                row = {"Symbol": t["symbol"], "Trailing Stop": t["return_pct"]}
                for fd in [5, 10, 20, 40]:
                    key = f"buy_hold_{fd}d"
                    row[f"B&H {fd}D"] = t.get(key)
                comp_data.append(row)
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)


# ═══════════════════════════════════
# TAB 3: MULTI-DATE BACKTEST
# ═══════════════════════════════════

with tab_multi:
    st.subheader("Multi-Date Aggregate Backtest")
    st.info("Run the scanner every N days over a period and aggregate all trade results.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        bt_start = st.date_input("Start Date", datetime(2024, 6, 1), key="mbt_s")
    with col2:
        bt_end = st.date_input("End Date", datetime.now() - timedelta(days=50), key="mbt_e")
    with col3:
        interval = st.number_input("Scan every N days", 7, 30, 14, key="mbt_int")
    with col4:
        mbt_topn = st.number_input("Top N per scan", 3, 10, 5, key="mbt_n")

    if st.button("📈 Run Multi-Date Backtest", type="primary", key="mbt_btn"):
        symbols = cached_symbols()

        with st.spinner("Fetching full period data..."):
            full_end = pd.Timestamp(bt_end) + timedelta(days=80)
            stock_data = cached_fetch(
                tuple(symbols), full_end.strftime("%Y-%m-%d"), 
                (full_end - pd.Timestamp(bt_start)).days + 400,
            )
            st.write(f"Loaded **{len(stock_data)} stocks**")

        with st.spinner("Running multi-date backtest (may take 2-5 min)..."):
            all_trades, summary = run_multi_date_backtest(
                stock_data, params,
                bt_start.strftime("%Y-%m-%d"),
                bt_end.strftime("%Y-%m-%d"),
                scan_interval_days=interval,
                top_n=mbt_topn, max_hold=40,
            )

        if not all_trades:
            st.warning("No trades generated. Relax parameters or widen date range.")
        else:
            st.success(f"**{summary['total_trades']} total trades** across the period")

            # Summary dashboard
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("Avg Return", f"{summary['avg_return']}%")
            mc2.metric("Win Rate", f"{summary['win_rate']}%")
            mc3.metric("Profit Factor", f"{summary['profit_factor']}")
            mc4.metric("Avg Winner", f"+{summary['avg_winner']}%")
            mc5.metric("Avg Loser", f"{summary['avg_loser']}%")

            mc6, mc7, mc8, mc9 = st.columns(4)
            mc6.metric("Best Trade", f"+{summary['best_trade']}%")
            mc7.metric("Worst Trade", f"{summary['worst_trade']}%")
            mc8.metric("Median Return", f"{summary['median_return']}%")
            mc9.metric("Total Points", f"{summary['total_return_pts']}%")

            # Returns distribution
            returns = [t["return_pct"] for t in all_trades]
            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=returns, nbinsx=30,
                marker_color=["#16a34a" if r > 0 else "#dc2626" for r in sorted(returns)],
            ))
            fig_dist.update_layout(
                title="Return Distribution", height=300,
                xaxis_title="Return %", yaxis_title="Count",
                template="plotly_white",
            )
            st.plotly_chart(fig_dist, use_container_width=True)

            # Equity curve
            cumulative = np.cumsum(returns)
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(
                y=cumulative, mode="lines+markers",
                line=dict(color="#3b82f6", width=2),
                marker=dict(
                    color=["#16a34a" if r > 0 else "#dc2626" for r in returns],
                    size=6,
                ),
            ))
            fig_eq.update_layout(
                title="Cumulative Returns (% points)",
                height=300, template="plotly_white",
                xaxis_title="Trade #", yaxis_title="Cumulative %",
            )
            st.plotly_chart(fig_eq, use_container_width=True)

            # All trades table
            with st.expander("All Trades"):
                tdf = pd.DataFrame(all_trades)
                show_cols = ["symbol", "scan_date", "entry_date", "entry_type",
                             "entry_price", "exit_price", "exit_day", "exit_reason",
                             "return_pct", "max_gain_pct", "vcp_score", "rs_rating"]
                avail = [c for c in show_cols if c in tdf.columns]
                st.dataframe(tdf[avail], use_container_width=True, hide_index=True)

            # Exit reason breakdown
            exit_reasons = pd.DataFrame(all_trades)["exit_reason"].value_counts()
            st.write("**Exit Reasons:**")
            st.dataframe(exit_reasons, use_container_width=True)


# ═══════════════════════════════════
# TAB 4: OPTIMIZE
# ═══════════════════════════════════

with tab_opt:
    st.subheader("Auto-Optimize Parameters")
    st.info(
        "Tests 6,500+ parameter combinations across multiple dates to find "
        "the best settings for Indian stocks. Takes 10-30 minutes."
    )
    st.warning("⚠️ Run this once, note the best parameters, then set them in the sidebar.")

    col_o1, col_o2 = st.columns(2)
    with col_o1:
        opt_start = st.date_input("Optimization Start", datetime(2024, 6, 1), key="opt_s")
    with col_o2:
        opt_end = st.date_input("Optimization End", datetime.now() - timedelta(days=50), key="opt_e")

    if st.button("🎯 Start Optimization", type="primary", key="opt_btn"):
        symbols = cached_symbols()

        with st.spinner("Fetching data for optimization period..."):
            full_end = pd.Timestamp(opt_end) + timedelta(days=80)
            stock_data = cached_fetch(
                tuple(symbols), full_end.strftime("%Y-%m-%d"),
                (full_end - pd.Timestamp(opt_start)).days + 400,
            )
            st.write(f"Loaded **{len(stock_data)} stocks**")

        with st.spinner("⏳ Optimizing (this takes 10-30 min)..."):
            best_params, all_results = optimize_parameters(
                stock_data,
                opt_start.strftime("%Y-%m-%d"),
                opt_end.strftime("%Y-%m-%d"),
                scan_interval_days=21,
                top_n=5,
            )

        if not all_results:
            st.warning("Optimization produced no results. Try wider date range.")
        else:
            st.success("Optimization complete!")

            st.subheader("Best Parameters Found")
            best_display = {
                "RS Min": best_params["rs_min"],
                "52W High %": f'{(1-best_params["high_52w_pct"])*100:.0f}%',
                "Base Max Depth": f'{best_params["base_max_depth"]*100:.0f}%',
                "Last Contraction Max": f'{best_params["last_contraction_max"]*100:.0f}%',
                "Vol Decline Ratio": best_params["vol_decline_ratio"],
                "Pivot Proximity": f'{best_params["pivot_proximity_pct"]}%',
                "Trail Trigger": f'{best_params["trail_trigger_pct"]}%',
                "Trail Distance": f'{best_params["trail_pct"]}%',
            }
            bc1, bc2, bc3, bc4 = st.columns(4)
            items = list(best_display.items())
            for idx, (k, v) in enumerate(items):
                [bc1, bc2, bc3, bc4][idx % 4].metric(k, v)

            # Top 20 results
            st.subheader("Top 20 Parameter Combinations")
            top20 = pd.DataFrame(all_results[:20])
            st.dataframe(top20, use_container_width=True, hide_index=True)

            st.subheader("Copy These to Sidebar")
            st.code(f"""
rs_min = {best_params['rs_min']}
high_52w_pct = {best_params['high_52w_pct']}
base_max_depth = {best_params['base_max_depth']}
last_contraction_max = {best_params['last_contraction_max']}
vol_decline_ratio = {best_params['vol_decline_ratio']}
pivot_proximity_pct = {best_params['pivot_proximity_pct']}
trail_trigger_pct = {best_params['trail_trigger_pct']}
trail_pct = {best_params['trail_pct']}
""")


# ═══════════════════════════════════
# TAB 5: GUIDE
# ═══════════════════════════════════

with tab_guide:
    st.subheader("How This Scanner Works")

    st.markdown("""
### What Changed in v2 (vs v1)

| Problem in v1 | Fix in v2 |
|----------------|-----------|
| Entered next-day open blindly | **Breakout-confirmed entry**: waits up to 10 days for close > pivot on 1.3× volume |
| Fixed-period exit (5/10/20/40d) | **Trailing stop**: locks profits after 5% gain, trails at 8% below peak |
| Loose VCP detection | **ATR contraction check** + stricter contraction validation |
| RS ≥ 70 too loose | **RS ≥ 80** default (top 20% performers) |
| 25% from 52W high too far | **15% from 52W high** (stock is near highs) |
| No momentum filter | **EMA 8 > EMA 21** required (short-term bullish) |
| No optimization | **Auto-optimizer** tests 6,500+ parameter combos |

---

### Entry Strategy

**Breakout Entry (primary):**
- After VCP detected, monitor for up to 10 days
- Enter when: close > pivot price AND volume > 1.3× 50-day avg
- Entry price: next day's open after breakout signal

**Anticipation Entry (fallback):**
- If price is within 3% of pivot on scan day, enter next day open
- Tighter stop-loss used

---

### Stop-Loss & Trailing Stop

| Stage | Rule |
|-------|------|
| **Initial SL** | 0.5% below last VCP swing low (max 8% from entry) |
| **After +3% gain** | Move stop to breakeven + 0.5% |
| **After +5% gain** | Trail at 8% below highest peak since entry |
| **Max hold** | Exit at day 40 if neither SL nor trail triggered |

This approach cuts losers at -3% to -8% while letting winners run to +15% or more.

---

### Position Sizing (for live trading)

```
Max risk per trade = 2% of capital
Position size = (Capital × 0.02) / Stop-loss %

Example:
  Capital = ₹10,00,000
  Stop-loss = 5%
  Position = (10,00,000 × 0.02) / 0.05 = ₹4,00,000
```

---

### Recommended Workflow

1. **Optimize first**: Run the optimizer on 1-year data → note best params
2. **Set params in sidebar**: Use optimized values
3. **Multi-date backtest**: Validate with optimized params → aim for:
   - Win rate > 45%
   - Avg return > 2%
   - Profit factor > 1.5
4. **Daily live scan**: Run after 3:45 PM IST
5. **Enter on breakout only**: Wait for volume confirmation
6. **Set stop-loss immediately**: Never average down
7. **Trail the stop**: Let winners run

---

### Metrics Explained

| Metric | Target | Meaning |
|--------|--------|---------|
| **Win Rate** | > 45% | % of trades that make money |
| **Avg Return** | > 2% | Average gain per trade |
| **Profit Factor** | > 1.5 | Gross profit ÷ gross loss |
| **Avg Winner** | > 5% | How much winners make |
| **Avg Loser** | > -4% | How much losers lose (smaller = better) |
| **Expectancy** | > 1% | Expected return per trade |

---

### When NOT to Trade

- Market (Nifty 50) below 200-day SMA → go to cash
- Fewer than 10 stocks passing Trend Template → weak market breadth
- Your recent win rate < 30% over last 10 trades → re-evaluate or reduce size
""")
