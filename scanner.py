"""
VCP Scanner Engine v2 — Optimized for Positive Returns
Key improvements over v1:
  1. Breakout-confirmed entry (not blind next-day open)
  2. Trailing stop-loss (locks profits, cuts losers fast)
  3. Tighter trend template (RS 80+, near 52W high)
  4. Better VCP detection (ATR contraction, volume profile)
  5. Multi-date backtest with trade simulation
  6. Auto-parameter optimization
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from itertools import product as iterproduct
import warnings
import time

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════
# 1. STOCK LIST
# ═══════════════════════════════════════════════

NIFTY50 = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN",
    "BHARTIARTL","KOTAKBANK","ITC","LT","AXISBANK","BAJFINANCE","ASIANPAINT",
    "MARUTI","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NESTLEIND",
    "TATAMOTORS","ONGC","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL",
    "ADANIENT","ADANIPORTS","BAJAJFINSV","TECHM","HDFCLIFE","SBILIFE",
    "DIVISLAB","DRREDDY","CIPLA","GRASIM","APOLLOHOSP","EICHERMOT",
    "HEROMOTOCO","BPCL","COALINDIA","INDUSINDBK","TATACONSUM","BRITANNIA",
    "HINDALCO","BAJAJ-AUTO","SHRIRAMFIN","TRENT",
]

def get_nifty500_symbols() -> list[str]:
    """Fetch Nifty 500 list. Falls back to Nifty 50."""
    try:
        df = pd.read_csv(
            "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
            storage_options={"User-Agent": "Mozilla/5.0"},
        )
        if "Symbol" in df.columns:
            return [s.strip() + ".NS" for s in df["Symbol"].tolist()]
    except Exception:
        pass
    return [s + ".NS" for s in NIFTY50]


# ═══════════════════════════════════════════════
# 2. DATA FETCHING
# ═══════════════════════════════════════════════

def fetch_data(symbols: list[str], end_date: str = None, days: int = 450) -> dict[str, pd.DataFrame]:
    if end_date:
        end = pd.Timestamp(end_date)
    else:
        end = pd.Timestamp.now()
    start = end - timedelta(days=days)
    stock_data = {}
    batch_size = 40

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        try:
            df = yf.download(
                " ".join(batch),
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False, threads=True, group_by="ticker",
            )
            if df.empty:
                continue
            if len(batch) == 1:
                sym = batch[0]
                sdf = df[["Open","High","Low","Close","Volume"]].dropna()
                if len(sdf) >= 200:
                    stock_data[sym] = sdf
            else:
                for sym in batch:
                    try:
                        sdf = df[sym][["Open","High","Low","Close","Volume"]].dropna()
                        if len(sdf) >= 200:
                            stock_data[sym] = sdf
                    except Exception:
                        continue
        except Exception:
            continue
        time.sleep(0.3)

    return stock_data


# ═══════════════════════════════════════════════
# 3. INDICATORS
# ═══════════════════════════════════════════════

def sma(series, period):
    return series.rolling(period).mean()

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def compute_atr(high, low, close, period=14):
    """ATR series."""
    prev_c = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_c).abs(),
        (low - prev_c).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def compute_rs_ratings(all_close: dict[str, pd.Series]) -> dict[str, float]:
    """IBD-style RS rating 1-99, double-weighted recent quarter."""
    perfs = {}
    for sym, close in all_close.items():
        n = len(close)
        if n < 252:
            continue
        c = close.iloc[-1]
        try:
            p63  = (c / close.iloc[-63] - 1)  if n >= 63  else 0
            p126 = (c / close.iloc[-126] - 1) if n >= 126 else 0
            p189 = (c / close.iloc[-189] - 1) if n >= 189 else 0
            p252 = (c / close.iloc[-252] - 1) if n >= 252 else 0
            perfs[sym] = (p63 * 2 + p126 + p189 + p252) / 5
        except Exception:
            continue

    if not perfs:
        return {}
    sorted_syms = sorted(perfs, key=lambda s: perfs[s])
    n = len(sorted_syms)
    return {sym: round((rank / n) * 99) + 1 for rank, sym in enumerate(sorted_syms)}


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators as columns."""
    df = df.copy()
    df["SMA_20"]  = sma(df["Close"], 20)
    df["SMA_50"]  = sma(df["Close"], 50)
    df["SMA_150"] = sma(df["Close"], 150)
    df["SMA_200"] = sma(df["Close"], 200)
    df["EMA_8"]   = ema(df["Close"], 8)
    df["EMA_21"]  = ema(df["Close"], 21)
    df["ATR_14"]  = compute_atr(df["High"], df["Low"], df["Close"], 14)
    df["ATR_pct"] = df["ATR_14"] / df["Close"] * 100
    df["VOL_50"]  = sma(df["Volume"], 50)
    df["VOL_10"]  = sma(df["Volume"], 10)

    # 52-week rolling
    df["HIGH_52W"] = df["High"].rolling(252, min_periods=200).max()
    df["LOW_52W"]  = df["Low"].rolling(252, min_periods=200).min()

    # Relative volume
    df["RVOL"] = df["Volume"] / df["VOL_50"]

    # 10-day range tightness
    df["RANGE_10D"] = (
        df["High"].rolling(10).max() - df["Low"].rolling(10).min()
    ) / df["Close"] * 100

    return df


# ═══════════════════════════════════════════════
# 4. TREND TEMPLATE (OPTIMIZED)
# ═══════════════════════════════════════════════

def check_trend_template(df: pd.DataFrame, rs_rating: float, p: dict) -> tuple[bool, dict]:
    """
    Stricter trend template with configurable thresholds.
    p = parameter dict with keys: rs_min, high_52w_pct, low_52w_pct, sma200_trend_days
    """
    if len(df) < 253:
        return False, {}

    row = df.iloc[-1]
    c = row["Close"]
    s50 = row["SMA_50"]
    s150 = row["SMA_150"]
    s200 = row["SMA_200"]
    h52 = row["HIGH_52W"]
    l52 = row["LOW_52W"]

    trend_days = p.get("sma200_trend_days", 22)
    if len(df) < 200 + trend_days:
        return False, {}
    s200_past = df["SMA_200"].iloc[-(trend_days + 1)]

    if any(pd.isna(x) for x in [s50, s150, s200, s200_past, h52, l52]):
        return False, {}

    conditions = {
        "price > SMA150": c > s150,
        "price > SMA200": c > s200,
        "SMA150 > SMA200": s150 > s200,
        "SMA200 rising": s200 > s200_past,
        "SMA50 > SMA150": s50 > s150,
        "SMA50 > SMA200": s50 > s200,
        "price > SMA50": c > s50,
        "near 52W high": c >= h52 * p.get("high_52w_pct", 0.80),
        "above 52W low": c >= l52 * p.get("low_52w_pct", 1.30),
        "RS rating": rs_rating >= p.get("rs_min", 80),
        # New: EMA momentum
        "EMA8 > EMA21": row["EMA_8"] > row["EMA_21"],
    }

    passed = all(conditions.values())
    details = {
        "close": round(c, 2),
        "sma50": round(s50, 2),
        "sma150": round(s150, 2),
        "sma200": round(s200, 2),
        "high_52w": round(h52, 2),
        "low_52w": round(l52, 2),
        "rs_rating": rs_rating,
        "pct_from_52w_high": round((1 - c / h52) * 100, 1),
        "atr_pct": round(row["ATR_pct"], 2) if not pd.isna(row["ATR_pct"]) else 0,
    }
    return passed, details


# ═══════════════════════════════════════════════
# 5. VCP DETECTION (IMPROVED)
# ═══════════════════════════════════════════════

def detect_zigzag(highs, lows, threshold=0.03):
    """Improved zigzag: returns list of (type, index, price)."""
    n = len(highs)
    if n < 5:
        return []

    swings = []
    direction = 0
    last_h_val, last_h_idx = highs[0], 0
    last_l_val, last_l_idx = lows[0], 0

    for i in range(1, n):
        if direction >= 0:
            if highs[i] > last_h_val:
                last_h_val, last_h_idx = highs[i], i
            if last_h_val > 0 and (last_h_val - lows[i]) / last_h_val >= threshold:
                if not swings or swings[-1][0] != "H":
                    swings.append(("H", last_h_idx, last_h_val))
                direction = -1
                last_l_val, last_l_idx = lows[i], i

        if direction == -1:
            if lows[i] < last_l_val:
                last_l_val, last_l_idx = lows[i], i
            if last_l_val > 0 and (highs[i] - last_l_val) / last_l_val >= threshold:
                swings.append(("L", last_l_idx, last_l_val))
                direction = 1
                last_h_val, last_h_idx = highs[i], i

    if direction == -1:
        swings.append(("L", last_l_idx, last_l_val))

    return swings


def detect_vcp(df: pd.DataFrame, p: dict) -> dict | None:
    """
    Improved VCP detection with ATR contraction confirmation.
    """
    base_min = p.get("base_min_days", 15)
    base_max = p.get("base_max_days", 120)
    base_max_depth = p.get("base_max_depth", 0.30)
    min_contractions = p.get("min_contractions", 2)
    max_contractions = p.get("max_contractions", 6)
    zigzag_thresh = p.get("zigzag_threshold", 0.03)
    last_c_max = p.get("last_contraction_max", 0.10)
    vol_decline = p.get("vol_decline_ratio", 0.80)
    tightness_max = p.get("tightness_max_pct", 10)
    pivot_prox = p.get("pivot_proximity_pct", 10)

    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    volume = df["Volume"].values
    atr_pct = df["ATR_pct"].values

    current_close = close[-1]

    # ── Find pivot (highest high in lookback) ──
    lookback = min(base_max, len(high) - 50)
    if lookback < base_min:
        return None

    search_region = high[-lookback:]
    pivot_rel_idx = np.argmax(search_region)
    pivot_price = search_region[pivot_rel_idx]
    base_abs_start = len(high) - lookback + pivot_rel_idx
    base_length = len(high) - 1 - base_abs_start

    if base_length < base_min:
        return None

    base_h = high[base_abs_start:]
    base_l = low[base_abs_start:]
    base_v = volume[base_abs_start:]

    # ── Base depth ──
    base_low = np.min(base_l)
    base_depth = (pivot_price - base_low) / pivot_price if pivot_price > 0 else 1
    if base_depth > base_max_depth:
        return None

    # ── Zigzag contractions ──
    swings = detect_zigzag(base_h, base_l, zigzag_thresh)
    contractions = []
    for i in range(len(swings) - 1):
        if swings[i][0] == "H" and swings[i + 1][0] == "L":
            sh, sl = swings[i][2], swings[i + 1][2]
            if sh > 0:
                contractions.append((sh - sl) / sh)

    if len(contractions) < min_contractions or len(contractions) > max_contractions:
        return None

    # ── Contraction must be decreasing ──
    # Last contraction < first * 0.60
    if contractions[-1] >= contractions[0] * 0.60:
        return None

    if contractions[-1] > last_c_max:
        return None

    # ── Check monotonic-ish decrease (allow 1 violation) ──
    violations = 0
    for i in range(1, len(contractions)):
        if contractions[i] > contractions[i - 1] * 1.05:
            violations += 1
    if violations > 1:
        return None

    # ── Volume decline ──
    avg_vol_base = np.mean(base_v) if len(base_v) > 0 else 1
    avg_vol_recent = np.mean(volume[-5:])
    vol_ratio = avg_vol_recent / avg_vol_base if avg_vol_base > 0 else 1
    if vol_ratio > vol_decline:
        return None

    # ── ATR contraction (key v2 improvement) ──
    if len(atr_pct) > base_length and base_length > 10:
        atr_at_start = np.mean(atr_pct[base_abs_start : base_abs_start + 10])
        atr_now = np.mean(atr_pct[-5:])
        if atr_at_start > 0:
            atr_contraction = atr_now / atr_at_start
        else:
            atr_contraction = 1.0
    else:
        atr_contraction = 1.0

    # ── Tightness ──
    range_10d = (np.max(high[-10:]) - np.min(low[-10:])) / current_close * 100
    if range_10d > tightness_max:
        return None

    # ── Pivot proximity ──
    dist_to_pivot = (pivot_price - current_close) / pivot_price * 100 if pivot_price > 0 else 100
    if dist_to_pivot > pivot_prox:
        return None
    if dist_to_pivot < -5:  # already broke out 5%+ above pivot, skip
        return None

    # ── Stop-loss: below last swing low ──
    last_swing_low = base_low
    for s in reversed(swings):
        if s[0] == "L":
            last_swing_low = s[2]
            break
    stop_loss = round(last_swing_low * 0.995, 2)  # 0.5% buffer
    stop_loss_pct = round((1 - stop_loss / current_close) * 100, 1)
    if stop_loss_pct > 8:
        stop_loss = round(current_close * 0.92, 2)
        stop_loss_pct = 8.0
    if stop_loss_pct < 1:
        stop_loss_pct = 2.0
        stop_loss = round(current_close * 0.98, 2)

    # ── Entry ──
    entry_price = round(pivot_price * 1.002, 2)  # just above pivot
    if current_close >= pivot_price * 0.98:
        entry_price = round(current_close, 2)

    # ── VCP Score (0-100) ──
    score = 0
    # Contraction quality (0-30)
    if contractions[0] > 0:
        score += min(30, (1 - contractions[-1] / contractions[0]) * 30)
    # Volume dry-up (0-25)
    score += min(25, (1 - vol_ratio) * 35)
    # ATR contraction (0-20) — NEW
    score += min(20, (1 - atr_contraction) * 30)
    # Tightness (0-15)
    score += min(15, (1 - range_10d / tightness_max) * 15)
    # Pivot proximity (0-10)
    score += min(10, (1 - abs(dist_to_pivot) / pivot_prox) * 10)

    return {
        "base_length_days": base_length,
        "base_depth_pct": round(base_depth * 100, 1),
        "num_contractions": len(contractions),
        "contractions_pct": [round(c * 100, 1) for c in contractions],
        "pivot_high": round(pivot_price, 2),
        "distance_to_pivot_pct": round(dist_to_pivot, 1),
        "volume_ratio": round(vol_ratio, 2),
        "atr_contraction": round(atr_contraction, 2),
        "tightness_10d_pct": round(range_10d, 1),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "stop_loss_pct": stop_loss_pct,
        "vcp_score": round(score, 1),
    }


# ═══════════════════════════════════════════════
# 6. FULL SCANNER
# ═══════════════════════════════════════════════

def run_scan(stock_data: dict, rs_ratings: dict, params: dict) -> list[dict]:
    results = []
    for sym, raw_df in stock_data.items():
        rs = rs_ratings.get(sym, 0)
        df = compute_all_indicators(raw_df)

        tt_pass, tt_details = check_trend_template(df, rs, params)
        if not tt_pass:
            continue

        vcp = detect_vcp(df, params)
        if vcp is None:
            continue

        clean_sym = sym.replace(".NS", "")
        results.append({
            "symbol": clean_sym,
            "yf_symbol": sym,
            **tt_details,
            **vcp,
        })

    results.sort(key=lambda x: x.get("vcp_score", 0), reverse=True)
    return results


# ═══════════════════════════════════════════════
# 7. TRADE SIMULATION (TRAILING STOP)
# ═══════════════════════════════════════════════

def simulate_trade(
    df_future: pd.DataFrame,
    entry_price: float,
    initial_stop: float,
    max_hold: int = 40,
    trail_trigger_pct: float = 5.0,
    trail_pct: float = 8.0,
    breakeven_trigger_pct: float = 3.0,
) -> dict:
    """
    Simulate a single trade with intelligent trailing stop.
    
    Rules:
    1. Initial stop = provided (below last swing low)
    2. After breakeven_trigger_pct gain: move stop to entry + 0.5%
    3. After trail_trigger_pct gain: trail at trail_pct below peak
    4. Max hold = max_hold days
    """
    stop = initial_stop
    peak = entry_price
    entry = entry_price

    daily_returns = []

    for day in range(min(len(df_future), max_hold)):
        low_today = df_future["Low"].iloc[day]
        high_today = df_future["High"].iloc[day]
        close_today = df_future["Close"].iloc[day]

        # Check stop hit (intraday)
        if low_today <= stop:
            exit_price = stop
            pnl = (exit_price / entry - 1) * 100
            return {
                "exit_price": round(exit_price, 2),
                "exit_day": day + 1,
                "exit_reason": "stop_loss",
                "return_pct": round(pnl, 1),
                "max_gain_pct": round((peak / entry - 1) * 100, 1),
                "final_stop": round(stop, 2),
            }

        # Update peak
        if high_today > peak:
            peak = high_today

        gain_from_entry = (peak / entry - 1) * 100

        # Trailing logic
        if gain_from_entry >= trail_trigger_pct:
            new_stop = peak * (1 - trail_pct / 100)
            stop = max(stop, new_stop)
        elif gain_from_entry >= breakeven_trigger_pct:
            stop = max(stop, entry * 1.005)

        daily_returns.append(round((close_today / entry - 1) * 100, 1))

    # Max hold exit
    exit_price = df_future["Close"].iloc[min(len(df_future) - 1, max_hold - 1)]
    pnl = (exit_price / entry - 1) * 100
    return {
        "exit_price": round(exit_price, 2),
        "exit_day": min(len(df_future), max_hold),
        "exit_reason": "max_hold",
        "return_pct": round(pnl, 1),
        "max_gain_pct": round((peak / entry - 1) * 100, 1),
        "final_stop": round(stop, 2),
    }


# ═══════════════════════════════════════════════
# 8. BACKTEST (IMPROVED)
# ═══════════════════════════════════════════════

def run_backtest(
    scan_results: list[dict],
    full_stock_data: dict,
    scan_date: pd.Timestamp,
    top_n: int = 5,
    breakout_wait_days: int = 10,
    max_hold: int = 40,
    trail_trigger: float = 5.0,
    trail_pct: float = 8.0,
) -> list[dict]:
    """
    Improved backtest with breakout-confirmed entry.
    
    1. Take top_n candidates from scan
    2. Wait up to breakout_wait_days for breakout (close > pivot on 1.3x vol)
    3. Enter at next day's open after breakout
    4. Simulate with trailing stop
    5. Also compute fixed-period returns for comparison
    """
    results = []

    for stock in scan_results[:top_n]:
        sym = stock["yf_symbol"]
        if sym not in full_stock_data:
            continue

        df = full_stock_data[sym]
        future_all = df[df.index > scan_date]
        if len(future_all) < 5:
            continue

        df_ind = compute_all_indicators(df)
        future_ind = df_ind[df_ind.index > scan_date]

        pivot = stock["pivot_high"]
        vol50_at_scan = stock.get("vol50_at_scan", None)
        if vol50_at_scan is None:
            pre_scan = df_ind[df_ind.index <= scan_date]
            vol50_at_scan = pre_scan["VOL_50"].iloc[-1] if len(pre_scan) > 0 else 0

        # ── STRATEGY A: Breakout Entry ──
        entry_day_idx = None
        for d in range(min(breakout_wait_days, len(future_ind))):
            row = future_ind.iloc[d]
            # Breakout: close > pivot AND volume > 1.3x average
            if row["Close"] > pivot and row["Volume"] > vol50_at_scan * 1.3:
                entry_day_idx = d
                break

        # ── STRATEGY B: Anticipation Entry (fallback) ──
        # If within 3% of pivot, enter next day
        if entry_day_idx is None:
            close_at_scan = stock["close"]
            if close_at_scan >= pivot * 0.97:
                entry_day_idx = 0

        if entry_day_idx is None:
            continue  # no entry signal

        # Entry at next day's open after signal
        actual_entry_idx = entry_day_idx + 1
        if actual_entry_idx >= len(future_all):
            continue

        entry_price = future_all["Open"].iloc[actual_entry_idx]
        entry_date = future_all.index[actual_entry_idx]

        # Stop-loss relative to entry
        sl_pct = min(stock["stop_loss_pct"], 8.0)
        sl_pct = max(sl_pct, 2.0)
        initial_stop = entry_price * (1 - sl_pct / 100)

        # Post-entry data
        post_entry = future_all.iloc[actual_entry_idx:]

        # Simulate trade
        trade = simulate_trade(
            post_entry, entry_price, initial_stop,
            max_hold=max_hold,
            trail_trigger_pct=trail_trigger,
            trail_pct=trail_pct,
        )

        # Fixed-period returns (for comparison)
        fixed_returns = {}
        for fd in [5, 10, 20, 40]:
            if len(post_entry) > fd:
                fd_close = post_entry["Close"].iloc[fd]
                fixed_returns[f"buy_hold_{fd}d"] = round((fd_close / entry_price - 1) * 100, 1)
            else:
                fixed_returns[f"buy_hold_{fd}d"] = None

        result = {
            "symbol": stock["symbol"],
            "yf_symbol": sym,
            "scan_date": scan_date.strftime("%Y-%m-%d"),
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "entry_type": "breakout" if entry_day_idx > 0 else "anticipation",
            "entry_price": round(entry_price, 2),
            "initial_stop": round(initial_stop, 2),
            "stop_loss_pct": sl_pct,
            "vcp_score": stock["vcp_score"],
            "rs_rating": stock["rs_rating"],
            "num_contractions": stock["num_contractions"],
            **trade,
            **fixed_returns,
        }
        results.append(result)

    return results


# ═══════════════════════════════════════════════
# 9. MULTI-DATE BACKTEST
# ═══════════════════════════════════════════════

def run_multi_date_backtest(
    stock_data: dict,
    params: dict,
    start_date: str,
    end_date: str,
    scan_interval_days: int = 14,
    top_n: int = 5,
    max_hold: int = 40,
) -> tuple[list[dict], dict]:
    """
    Run backtest across many dates and aggregate results.
    Returns (all_trades, summary_stats).
    """
    all_trades = []
    scan_dates = pd.date_range(start=start_date, end=end_date, freq=f"{scan_interval_days}D")

    for scan_dt in scan_dates:
        # Trim data to scan date
        scan_data = {}
        for sym, df in stock_data.items():
            trimmed = df[df.index <= scan_dt]
            if len(trimmed) >= 200:
                scan_data[sym] = trimmed

        if not scan_data:
            continue

        close_dict = {sym: df["Close"] for sym, df in scan_data.items()}
        rs_ratings = compute_rs_ratings(close_dict)

        scan_data_ind = {sym: compute_all_indicators(df) for sym, df in scan_data.items()}
        results = run_scan(scan_data, rs_ratings, params)

        if not results:
            continue

        # Add vol50 for breakout detection
        for r in results:
            sym = r["yf_symbol"]
            if sym in scan_data_ind:
                ind_df = scan_data_ind[sym]
                r["vol50_at_scan"] = ind_df["VOL_50"].iloc[-1] if not pd.isna(ind_df["VOL_50"].iloc[-1]) else 0

        trades = run_backtest(
            results, stock_data, scan_dt,
            top_n=top_n, max_hold=max_hold,
            trail_trigger=params.get("trail_trigger_pct", 5),
            trail_pct=params.get("trail_pct", 8),
        )
        all_trades.extend(trades)

    # Summary
    if not all_trades:
        return all_trades, {}

    returns = [t["return_pct"] for t in all_trades]
    winners = [r for r in returns if r > 0]
    losers = [r for r in returns if r <= 0]

    summary = {
        "total_trades": len(all_trades),
        "avg_return": round(np.mean(returns), 1),
        "median_return": round(np.median(returns), 1),
        "win_rate": round(len(winners) / len(returns) * 100, 1),
        "avg_winner": round(np.mean(winners), 1) if winners else 0,
        "avg_loser": round(np.mean(losers), 1) if losers else 0,
        "best_trade": round(max(returns), 1),
        "worst_trade": round(min(returns), 1),
        "profit_factor": round(
            abs(sum(winners) / sum(losers)), 2
        ) if losers and sum(losers) != 0 else float("inf"),
        "total_return_pts": round(sum(returns), 1),
        "expectancy": round(np.mean(returns), 2),
    }

    return all_trades, summary


# ═══════════════════════════════════════════════
# 10. PARAMETER OPTIMIZATION
# ═══════════════════════════════════════════════

DEFAULT_PARAMS = {
    "rs_min": 80,
    "high_52w_pct": 0.85,
    "low_52w_pct": 1.30,
    "sma200_trend_days": 22,
    "base_min_days": 15,
    "base_max_days": 120,
    "base_max_depth": 0.30,
    "min_contractions": 2,
    "max_contractions": 6,
    "zigzag_threshold": 0.03,
    "last_contraction_max": 0.10,
    "vol_decline_ratio": 0.80,
    "tightness_max_pct": 10,
    "pivot_proximity_pct": 10,
    "trail_trigger_pct": 5.0,
    "trail_pct": 8.0,
}


def optimize_parameters(
    stock_data: dict,
    start_date: str,
    end_date: str,
    scan_interval_days: int = 21,
    top_n: int = 5,
) -> tuple[dict, list[dict]]:
    """
    Test parameter combinations and return the best one.
    Returns (best_params, all_results).
    """
    # Parameter grid (focused on high-impact params)
    grid = {
        "rs_min":              [70, 80, 85],
        "high_52w_pct":        [0.80, 0.85, 0.90],
        "base_max_depth":      [0.25, 0.30, 0.35],
        "last_contraction_max":[0.08, 0.10, 0.12],
        "vol_decline_ratio":   [0.70, 0.80, 0.90],
        "pivot_proximity_pct": [8, 10, 12],
        "trail_trigger_pct":   [4, 5, 7],
        "trail_pct":           [6, 8, 10],
    }

    # Generate combinations
    keys = list(grid.keys())
    values = list(grid.values())
    combos = list(iterproduct(*values))

    all_results = []
    best_summary = None
    best_params = None
    best_score = -999

    for combo in combos:
        params = DEFAULT_PARAMS.copy()
        for k, v in zip(keys, combo):
            params[k] = v

        _, summary = run_multi_date_backtest(
            stock_data, params, start_date, end_date,
            scan_interval_days=scan_interval_days,
            top_n=top_n, max_hold=40,
        )

        if not summary:
            continue

        # Optimization score: combines return, win rate, and profit factor
        opt_score = (
            summary["avg_return"] * 2
            + summary["win_rate"] * 0.3
            + min(summary["profit_factor"], 5) * 3
            - abs(summary["avg_loser"]) * 0.5
        )

        summary["opt_score"] = round(opt_score, 1)
        result = {**{k: v for k, v in zip(keys, combo)}, **summary}
        all_results.append(result)

        if opt_score > best_score:
            best_score = opt_score
            best_params = params.copy()
            best_summary = summary.copy()

    # Sort by opt_score
    all_results.sort(key=lambda x: x.get("opt_score", -999), reverse=True)

    return best_params, all_results


# ═══════════════════════════════════════════════
# 11. CHART DATA HELPER
# ═══════════════════════════════════════════════

def get_chart_data(df: pd.DataFrame, days: int = 252) -> pd.DataFrame:
    """Get last N days of OHLCV + indicators for charting."""
    df_ind = compute_all_indicators(df)
    chart = df_ind.tail(days)[["Open","High","Low","Close","Volume","SMA_50","SMA_150","SMA_200","EMA_21"]].copy()
    chart.index = chart.index.strftime("%Y-%m-%d")
    return chart
