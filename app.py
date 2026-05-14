"""
VCP Scanner — Web Application
Mark Minervini's Volatility Contraction Pattern Scanner for Indian Stocks
Deploy on Streamlit Cloud: https://share.streamlit.io
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scanner import (
    get_nifty500_symbols,
    fetch_data,
    fetch_index_data,
    compute_rs_rating,
    run_scan,
    backtest_scan,
)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="VCP Scanner — Minervini Strategy",
    page_icon="📈",
    layout="wide",
)

st.title("📈 VCP Scanner — Minervini Strategy")
st.caption("Mark Minervini's Trend Template + Volatility Contraction Pattern | NSE Stocks via yfinance")

# ─────────────────────────────────────────────
# SIDEBAR — PARAMETERS
# ─────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Scanner Parameters")

    st.subheader("Trend Template")
    rs_min = st.slider("Min RS Rating", 50, 95, 70)
    high_52w_pct = st.slider("Max % from 52W High", 5, 40, 25)
    low_52w_mult = st.slider("Min % above 52W Low", 10, 80, 30)

    st.subheader("VCP Detection")
    base_min = st.slider("Min Base Length (days)", 10, 30, 15)
    base_max = st.slider("Max Base Length (days)", 80, 200, 150)
    base_depth = st.slider("Max Base Depth %", 15, 45, 35)
    min_contractions = st.slider("Min Contractions", 2, 4, 2)
    zigzag_pct = st.slider("Zigzag Threshold %", 2, 6, 3)
    tightness = st.slider("Max 10-day Range %", 5, 20, 12)
    pivot_prox = st.slider("Max Distance to Pivot %", 5, 20, 12)

    st.subheader("Volume")
    vol_decline = st.slider("Volume Decline Ratio", 0.50, 1.00, 0.85, 0.05)

    params = {
        "rs_min": rs_min,
        "high_52w_pct": (100 - high_52w_pct) / 100,
        "low_52w_mult": 1 + low_52w_mult / 100,
        "base_min_days": base_min,
        "base_max_days": base_max,
        "base_max_depth": base_depth / 100,
        "min_contractions": min_contractions,
        "max_contractions": 6,
        "zigzag_threshold": zigzag_pct / 100,
        "last_contraction_max": 0.15,
        "vol_decline_ratio": vol_decline,
        "tightness_max_pct": tightness,
        "pivot_proximity_pct": pivot_prox,
    }

# ─────────────────────────────────────────────
# CACHING
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(symbols: tuple, end_date: str, days: int):
    return fetch_data(list(symbols), end_date, days)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_index(end_date: str, days: int):
    return fetch_index_data(end_date, days)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_symbols():
    return get_nifty500_symbols()


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab_live, tab_backtest, tab_guide = st.tabs(["🔍 Live Scan", "📊 Backtest", "📖 Strategy Guide"])

# ═════════════════════════════════════════════
# TAB 1: LIVE SCAN
# ═════════════════════════════════════════════

with tab_live:
    st.subheader("Scan Today's Market")
    st.info("Fetches latest data for Nifty 500 stocks and runs the VCP scanner. Takes 3-8 minutes on first run (cached for 1 hour).")

    if st.button("🚀 Run Live Scan", type="primary", key="live"):
        symbols = cached_symbols()
        st.write(f"Stock universe: **{len(symbols)} symbols**")

        with st.spinner("Fetching price data from yfinance..."):
            today = datetime.now().strftime("%Y-%m-%d")
            stock_data = cached_fetch(tuple(symbols), today, 400)
            st.write(f"Data fetched: **{len(stock_data)} stocks** with sufficient history")

        with st.spinner("Computing RS Ratings..."):
            close_dict = {sym: df["Close"] for sym, df in stock_data.items()}
            rs_ratings = compute_rs_rating(close_dict)

        with st.spinner("Running Trend Template + VCP scan..."):
            results = run_scan(stock_data, rs_ratings, params)

        if results:
            st.success(f"Found **{len(results)} stocks** passing all filters!")

            # Summary table
            display_cols = [
                "symbol", "close", "rs_rating", "vcp_score",
                "entry_price", "stop_loss", "stop_loss_pct",
                "num_contractions", "base_depth_pct", "base_length_days",
                "distance_to_pivot_pct", "tightness_10d_pct",
                "volume_decline_ratio", "pct_from_52w_high",
            ]
            df_results = pd.DataFrame(results)
            available_cols = [c for c in display_cols if c in df_results.columns]
            df_display = df_results[available_cols].copy()

            col_names = {
                "symbol": "Symbol",
                "close": "Close (INR)",
                "rs_rating": "RS Rating",
                "vcp_score": "VCP Score",
                "entry_price": "Entry (INR)",
                "stop_loss": "Stop-Loss (INR)",
                "stop_loss_pct": "SL Risk %",
                "num_contractions": "Contractions",
                "base_depth_pct": "Base Depth %",
                "base_length_days": "Base Days",
                "distance_to_pivot_pct": "Dist to Pivot %",
                "tightness_10d_pct": "10D Range %",
                "volume_decline_ratio": "Vol Ratio",
                "pct_from_52w_high": "From 52W High %",
            }
            df_display.rename(columns=col_names, inplace=True)

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
            )

            # Detailed cards for top 5
            st.subheader("Top 5 Setups")
            for i, stock in enumerate(results[:5]):
                with st.expander(f"#{i+1} — {stock['symbol']} | Score: {stock['vcp_score']} | RS: {stock['rs_rating']}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Close", f"₹{stock['close']}")
                        st.metric("Entry Price", f"₹{stock['entry_price']}")
                        st.metric("Stop-Loss", f"₹{stock['stop_loss']} ({stock['stop_loss_pct']}%)")
                    with c2:
                        st.metric("RS Rating", stock["rs_rating"])
                        st.metric("VCP Score", stock["vcp_score"])
                        st.metric("Contractions", stock["num_contractions"])
                    with c3:
                        st.metric("Base Depth", f"{stock['base_depth_pct']}%")
                        st.metric("Base Length", f"{stock['base_length_days']} days")
                        st.metric("Volume Ratio", stock["volume_decline_ratio"])

                    st.write(f"**Contractions:** {stock['contractions_pct']}%")
                    st.write(f"**Pivot:** ₹{stock['pivot_high']} | **Distance:** {stock['distance_to_pivot_pct']}%")
                    st.write(f"**10-Day Tightness:** {stock['tightness_10d_pct']}%")
                    st.caption(stock["risk_reward_note"])
        else:
            st.warning("No stocks passed all filters. Try relaxing parameters in the sidebar.")


# ═════════════════════════════════════════════
# TAB 2: BACKTEST
# ═════════════════════════════════════════════

with tab_backtest:
    st.subheader("Historical Scan + Returns")
    st.info("Pick a past date. The scanner runs as of that date and shows top 5 picks with actual subsequent returns.")

    col_date, col_btn = st.columns([2, 1])
    with col_date:
        scan_date = st.date_input(
            "Scan Date",
            value=datetime.now() - timedelta(days=60),
            max_value=datetime.now() - timedelta(days=5),
            min_value=datetime(2023, 1, 1),
        )
    with col_btn:
        st.write("")
        st.write("")
        run_bt = st.button("📊 Run Backtest", type="primary", key="backtest")

    if run_bt:
        scan_ts = pd.Timestamp(scan_date)
        end_for_fetch = scan_ts + timedelta(days=70)  # extra days for forward returns
        symbols = cached_symbols()

        with st.spinner("Fetching historical data..."):
            stock_data = cached_fetch(
                tuple(symbols),
                end_for_fetch.strftime("%Y-%m-%d"),
                450,
            )
            st.write(f"Data fetched: **{len(stock_data)} stocks**")

        # Trim data to scan_date for the scan itself
        scan_data = {}
        for sym, df in stock_data.items():
            trimmed = df[df.index <= scan_ts]
            if len(trimmed) >= 200:
                scan_data[sym] = trimmed

        with st.spinner("Computing RS Ratings as of scan date..."):
            close_dict = {sym: df["Close"] for sym, df in scan_data.items()}
            rs_ratings = compute_rs_rating(close_dict)

        with st.spinner("Running scan as of selected date..."):
            results = run_scan(scan_data, rs_ratings, params)

        if not results:
            st.warning("No stocks passed filters on this date. Try a different date or relax parameters.")
        else:
            st.success(f"Found **{len(results)} stocks** on {scan_date}. Showing top 5 with returns.")

            # Backtest returns
            bt_results = backtest_scan(results, stock_data, scan_ts)

            if bt_results:
                # Summary table
                bt_df = pd.DataFrame(bt_results)
                display_bt_cols = [
                    "symbol", "entry_date", "entry_price", "stop_loss", "stop_loss_pct",
                    "vcp_score", "rs_rating",
                    "return_5d", "return_10d", "return_20d", "return_40d",
                    "stop_loss_hit", "stop_loss_hit_day",
                ]
                available_bt = [c for c in display_bt_cols if c in bt_df.columns]
                bt_display = bt_df[available_bt].copy()

                bt_col_names = {
                    "symbol": "Symbol",
                    "entry_date": "Entry Date",
                    "entry_price": "Entry (INR)",
                    "stop_loss": "SL (INR)",
                    "stop_loss_pct": "SL %",
                    "vcp_score": "Score",
                    "rs_rating": "RS",
                    "return_5d": "5D Ret %",
                    "return_10d": "10D Ret %",
                    "return_20d": "20D Ret %",
                    "return_40d": "40D Ret %",
                    "stop_loss_hit": "SL Hit?",
                    "stop_loss_hit_day": "SL Day",
                }
                bt_display.rename(columns=bt_col_names, inplace=True)

                st.dataframe(bt_display, use_container_width=True, hide_index=True)

                # Return summary
                st.subheader("Return Summary (with Stop-Loss)")
                for period in ["5D Ret %", "10D Ret %", "20D Ret %", "40D Ret %"]:
                    if period in bt_display.columns:
                        vals = bt_display[period].dropna()
                        if len(vals) > 0:
                            avg_ret = vals.mean()
                            winners = (vals > 0).sum()
                            st.write(
                                f"**{period.replace(' Ret %', '')}:** "
                                f"Avg Return = **{avg_ret:.1f}%** | "
                                f"Winners = **{winners}/{len(vals)}**"
                            )

                sl_hits = bt_display["SL Hit?"].sum() if "SL Hit?" in bt_display.columns else 0
                st.write(f"**Stop-Loss triggered:** {sl_hits} out of {len(bt_display)} trades")

                # Detailed cards
                st.subheader("Trade Details")
                for _, row in bt_display.iterrows():
                    sl_tag = "🔴 STOPPED OUT" if row.get("SL Hit?") else "🟢 HELD"
                    with st.expander(f"{row['Symbol']} | Entry ₹{row['Entry (INR)']} | {sl_tag}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Entry:** {row['Entry Date']} at ₹{row['Entry (INR)']}")
                            st.write(f"**Stop-Loss:** ₹{row['SL (INR)']} ({row['SL %']}% risk)")
                            st.write(f"**VCP Score:** {row['Score']} | **RS:** {row['RS']}")
                        with c2:
                            for p in ["5D Ret %", "10D Ret %", "20D Ret %", "40D Ret %"]:
                                v = row.get(p)
                                if v is not None:
                                    color = "green" if v > 0 else "red"
                                    st.markdown(f"**{p.replace(' Ret %', '')}:** :{color}[{v}%]")
                            if row.get("SL Hit?"):
                                st.write(f"⚠️ Stop-loss hit on day **{row.get('SL Day', '?')}**")
            else:
                st.warning("Could not compute forward returns (insufficient future data).")


# ═════════════════════════════════════════════
# TAB 3: STRATEGY GUIDE
# ═════════════════════════════════════════════

with tab_guide:
    st.subheader("How This Scanner Works")

    st.markdown("""
### Trend Template (Stage 2 Filter)

Every stock must pass **all** these conditions to qualify:

| Condition | Rule |
|-----------|------|
| MA Stack | Price > SMA 50 > SMA 150 > SMA 200 |
| SMA 200 Rising | SMA 200 today > SMA 200 from 22 days ago |
| Near 52W High | Price within 25% of 52-week high |
| Above 52W Low | Price at least 30% above 52-week low |
| RS Rating | ≥ 70 (outperforming 70% of market) |

---

### VCP Pattern (Volatility Contraction)

After trend template, the scanner looks for:

1. **Base formation** (15–150 days) with max depth of 35%
2. **2–6 contractions** where each pullback is smaller than the previous
3. **Volume decline** — recent volume < 85% of base average
4. **Tight price action** — last 10 days range < 12% of price
5. **Near pivot** — price within 12% of the base high

---

### Entry & Stop-Loss Strategy

| | Rule |
|---|---|
| **Entry** | Buy on breakout above pivot high on volume ≥ 1.5× average. If already near pivot, enter at current price. |
| **Stop-Loss** | 1% below the low of the last VCP contraction. Capped at max 8% from entry. |
| **Position Size** | Risk 1–2% of capital per trade. If SL is 5%, position = (capital × 0.02) / 0.05 |
| **Exit** | Sell into strength at 20–25% gain, or trail stop using 10-day low |

---

### Backtest Interpretation

- **5D/10D/20D/40D Returns** show actual price change after entry
- If stop-loss was hit before a return period, the return reflects the SL loss
- **SL Day** shows which trading day the stop was triggered
- Compare average returns to see which holding period works best

---

### RS Rating Calculation

Custom IBD-style rating using weighted price performance:
- 3-month performance × 2 (double-weighted for recency)
- 6-month, 9-month, 12-month performance × 1 each
- Ranked as percentile (1–99) across the stock universe
""")

    st.subheader("Recommended Workflow")
    st.markdown("""
1. **Run the backtest** on several past dates to validate the strategy works in Indian markets
2. **Adjust parameters** in the sidebar if too few/many stocks pass
3. **Run live scan** daily after market close (3:45 PM IST)
4. **Review top 5** — check the charts manually before entering
5. **Set stop-loss** immediately after entering a trade
6. **Never risk more than 2%** of your capital on a single trade
""")
