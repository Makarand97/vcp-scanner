"""
VCP Scanner Engine — Mark Minervini's Volatility Contraction Pattern
Uses daily OHLCV data. Designed for Indian NSE stocks via yfinance.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import time
import requests

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# 1. STOCK LIST
# ─────────────────────────────────────────────

def get_nifty500_symbols() -> list[str]:
    """Fetch Nifty 500 symbol list. Falls back to Nifty 50 on failure."""
    urls = [
        "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://www1.nseindia.com/content/indices/ind_nifty500list.csv",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv",
    }
    for url in urls:
        try:
            df = pd.read_csv(url, storage_options={"User-Agent": "Mozilla/5.0"})
            if "Symbol" in df.columns:
                return [s.strip() + ".NS" for s in df["Symbol"].tolist()]
        except Exception:
            pass

    # Fallback: Nifty 50
    nifty50 = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
        "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC", "LT", "AXISBANK",
        "BAJFINANCE", "ASIANPAINT", "MARUTI", "HCLTECH", "SUNPHARMA",
        "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND", "TATAMOTORS",
        "ONGC", "NTPC", "POWERGRID", "M&M", "TATASTEEL", "JSWSTEEL",
        "ADANIENT", "ADANIPORTS", "BAJAJFINSV", "TECHM", "HDFCLIFE",
        "SBILIFE", "DIVISLAB", "DRREDDY", "CIPLA", "GRASIM",
        "APOLLOHOSP", "EICHERMOT", "HEROMOTOCO", "BPCL", "COALINDIA",
        "INDUSINDBK", "TATACONSUM", "BRITANNIA", "HINDALCO",
        "BAJAJ-AUTO", "SHRIRAMFIN", "TRENT",
    ]
    return [s + ".NS" for s in nifty50]


# ─────────────────────────────────────────────
# 2. DATA FETCHING
# ─────────────────────────────────────────────

def fetch_data(symbols: list[str], end_date: str = None, days: int = 400) -> dict[str, pd.DataFrame]:
    """
    Download OHLCV data for symbols from yfinance.
    Returns dict: symbol -> DataFrame with columns [Open, High, Low, Close, Volume].
    """
    if end_date:
        end = pd.Timestamp(end_date)
    else:
        end = pd.Timestamp.now()

    start = end - timedelta(days=days)
    stock_data = {}
    batch_size = 50
    total = len(symbols)

    for i in range(0, total, batch_size):
        batch = symbols[i : i + batch_size]
        tickers_str = " ".join(batch)
        try:
            df = yf.download(
                tickers_str,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False,
                threads=True,
                group_by="ticker",
            )
            if df.empty:
                continue

            if len(batch) == 1:
                sym = batch[0]
                if not df.empty and len(df) >= 200:
                    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
                    if len(df) >= 200:
                        stock_data[sym] = df
            else:
                for sym in batch:
                    try:
                        sdf = df[sym][["Open", "High", "Low", "Close", "Volume"]].dropna()
                        if len(sdf) >= 200:
                            stock_data[sym] = sdf
                    except Exception:
                        continue
        except Exception:
            continue

        time.sleep(0.5)  # rate limit

    return stock_data


def fetch_index_data(end_date: str = None, days: int = 400) -> pd.DataFrame:
    """Fetch Nifty 50 index data for RS Rating computation."""
    if end_date:
        end = pd.Timestamp(end_date)
    else:
        end = pd.Timestamp.now()
    start = end - timedelta(days=days)
    try:
        df = yf.download(
            "^NSEI",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
        )
        return df[["Close"]].dropna()
    except Exception:
        return pd.DataFrame()


# ─────────────────────────────────────────────
# 3. INDICATOR COMPUTATION
# ─────────────────────────────────────────────

def compute_sma(series: pd.Series, period: int) -> float:
    if len(series) < period:
        return np.nan
    return series.iloc[-period:].mean()


def compute_rs_rating(all_close: dict[str, pd.Series]) -> dict[str, float]:
    """
    Compute IBD-style RS Rating (1-99) for all stocks.
    Weighted: 2x recent quarter, 1x each older quarter.
    """
    perfs = {}
    for sym, close in all_close.items():
        if len(close) < 252:
            continue
        try:
            c = close.iloc[-1]
            p63 = (c - close.iloc[-63]) / close.iloc[-63] if len(close) >= 63 else 0
            p126 = (c - close.iloc[-126]) / close.iloc[-126] if len(close) >= 126 else 0
            p189 = (c - close.iloc[-189]) / close.iloc[-189] if len(close) >= 189 else 0
            p252 = (c - close.iloc[-252]) / close.iloc[-252] if len(close) >= 252 else 0
            perfs[sym] = (p63 * 2 + p126 + p189 + p252) / 5
        except Exception:
            continue

    if not perfs:
        return {}

    sorted_syms = sorted(perfs.keys(), key=lambda s: perfs[s])
    n = len(sorted_syms)
    ratings = {}
    for rank, sym in enumerate(sorted_syms):
        ratings[sym] = round((rank / n) * 99) + 1
    return ratings


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Average True Range as percentage of current price."""
    if len(close) < period + 1:
        return np.nan
    h = high.iloc[-(period + 1):]
    l = low.iloc[-(period + 1):]
    c = close.iloc[-(period + 1):]
    tr = pd.concat([
        h.iloc[1:].values - l.iloc[1:].values,
        abs(h.iloc[1:].values - c.iloc[:-1].values),
        abs(l.iloc[1:].values - c.iloc[:-1].values),
    ], axis=1).max(axis=1) if False else None  # noqa

    # manual TR
    trs = []
    for i in range(1, len(h)):
        tr = max(
            h.iloc[i] - l.iloc[i],
            abs(h.iloc[i] - c.iloc[i - 1]),
            abs(l.iloc[i] - c.iloc[i - 1]),
        )
        trs.append(tr)
    atr = np.mean(trs[-period:])
    return (atr / close.iloc[-1]) * 100


# ─────────────────────────────────────────────
# 4. TREND TEMPLATE
# ─────────────────────────────────────────────

def check_trend_template(df: pd.DataFrame, rs_rating: float) -> tuple[bool, dict]:
    """
    Apply Minervini's 8-point Trend Template + RS filter.
    Returns (pass: bool, details: dict).
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    c = close.iloc[-1]
    sma50 = compute_sma(close, 50)
    sma150 = compute_sma(close, 150)
    sma200 = compute_sma(close, 200)
    sma200_22ago = compute_sma(close.iloc[:-22], 200) if len(close) > 222 else np.nan
    high_52w = high.iloc[-252:].max() if len(high) >= 252 else high.max()
    low_52w = low.iloc[-252:].min() if len(low) >= 252 else low.min()

    if any(np.isnan(x) for x in [sma50, sma150, sma200, sma200_22ago]):
        return False, {}

    conditions = {
        "price_above_sma150": c > sma150,
        "price_above_sma200": c > sma200,
        "sma150_above_sma200": sma150 > sma200,
        "sma200_rising": sma200 > sma200_22ago,
        "sma50_above_sma150": sma50 > sma150,
        "sma50_above_sma200": sma50 > sma200,
        "price_above_sma50": c > sma50,
        "within_25pct_of_52w_high": c >= high_52w * 0.75,
        "above_30pct_of_52w_low": c >= low_52w * 1.30,
        "rs_above_70": rs_rating >= 70,
    }

    passed = all(conditions.values())

    details = {
        "close": round(c, 2),
        "sma_50": round(sma50, 2),
        "sma_150": round(sma150, 2),
        "sma_200": round(sma200, 2),
        "high_52w": round(high_52w, 2),
        "low_52w": round(low_52w, 2),
        "rs_rating": rs_rating,
        "pct_from_52w_high": round((1 - c / high_52w) * 100, 1),
        "pct_above_52w_low": round((c / low_52w - 1) * 100, 1),
    }
    details.update(conditions)
    return passed, details


# ─────────────────────────────────────────────
# 5. VCP DETECTION
# ─────────────────────────────────────────────

def detect_zigzag(highs: np.ndarray, lows: np.ndarray, threshold: float = 0.03):
    """
    Detect alternating swing highs and lows.
    Returns list of (type, index, price) tuples.
    """
    swings = []
    direction = 0  # 0=undecided, 1=up, -1=down
    last_high_idx = 0
    last_high_val = highs[0]
    last_low_idx = 0
    last_low_val = lows[0]

    for i in range(1, len(highs)):
        if direction >= 0:
            if highs[i] > last_high_val:
                last_high_val = highs[i]
                last_high_idx = i
            if last_high_val > 0 and (last_high_val - lows[i]) / last_high_val >= threshold:
                if direction == 0 or not swings or swings[-1][0] != "H":
                    swings.append(("H", last_high_idx, last_high_val))
                direction = -1
                last_low_val = lows[i]
                last_low_idx = i

        if direction == -1:
            if lows[i] < last_low_val:
                last_low_val = lows[i]
                last_low_idx = i
            if last_low_val > 0 and (highs[i] - last_low_val) / last_low_val >= threshold:
                swings.append(("L", last_low_idx, last_low_val))
                direction = 1
                last_high_val = highs[i]
                last_high_idx = i

    # Capture trailing swing
    if direction == -1:
        swings.append(("L", last_low_idx, last_low_val))

    return swings


def detect_vcp(df: pd.DataFrame, params: dict = None) -> dict | None:
    """
    Detect VCP pattern in the price data.
    Returns VCP details dict or None.
    """
    if params is None:
        params = {}

    base_min = params.get("base_min_days", 15)
    base_max = params.get("base_max_days", 150)
    base_max_depth = params.get("base_max_depth", 0.35)
    min_contractions = params.get("min_contractions", 2)
    max_contractions = params.get("max_contractions", 6)
    zigzag_thresh = params.get("zigzag_threshold", 0.03)
    last_contraction_max = params.get("last_contraction_max", 0.15)
    vol_decline_ratio = params.get("vol_decline_ratio", 0.85)
    tightness_max = params.get("tightness_max_pct", 12)
    pivot_proximity = params.get("pivot_proximity_pct", 12)

    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    volume = df["Volume"].values
    current_close = close[-1]

    # Find pivot high in last 150 days
    lookback = min(base_max, len(high) - 1)
    base_high = high[-lookback:]
    pivot_idx_in_base = np.argmax(base_high)
    pivot_price = base_high[pivot_idx_in_base]

    # Base runs from pivot to current
    base_start = len(high) - lookback + pivot_idx_in_base
    base_length = len(high) - 1 - base_start

    if base_length < base_min:
        return None

    base_h = high[base_start:]
    base_l = low[base_start:]
    base_v = volume[base_start:]

    # Base depth
    base_low = np.min(base_l)
    base_depth = (pivot_price - base_low) / pivot_price if pivot_price > 0 else 0
    if base_depth > base_max_depth:
        return None

    # Zigzag contractions
    swings = detect_zigzag(base_h, base_l, zigzag_thresh)

    # Extract contractions (H -> L pairs)
    contractions = []
    for i in range(len(swings) - 1):
        if swings[i][0] == "H" and swings[i + 1][0] == "L":
            sh = swings[i][2]
            sl = swings[i + 1][2]
            if sh > 0:
                contractions.append((sh - sl) / sh)

    if len(contractions) < min_contractions:
        return None
    if len(contractions) > max_contractions:
        contractions = contractions[-max_contractions:]

    # Check contraction is decreasing (last < first * 0.7)
    if contractions[-1] >= contractions[0] * 0.70:
        return None

    # Last contraction size
    if contractions[-1] > last_contraction_max:
        return None

    # Volume decline
    avg_vol_base = np.mean(base_v) if len(base_v) > 0 else 1
    avg_vol_recent = np.mean(volume[-10:]) if len(volume) >= 10 else avg_vol_base
    vol_ratio = avg_vol_recent / avg_vol_base if avg_vol_base > 0 else 1
    vol_declining = vol_ratio <= vol_decline_ratio

    # Tightness (10-day range)
    range_10d = 0
    if len(high) >= 10:
        range_10d = (np.max(high[-10:]) - np.min(low[-10:])) / current_close * 100

    # Pivot proximity
    dist_to_pivot = (pivot_price - current_close) / pivot_price * 100 if pivot_price > 0 else 100

    if dist_to_pivot > pivot_proximity:
        return None

    # ── Stop-loss calculation ──
    # Stop = low of the last contraction swing low
    last_swing_low = base_low
    for s in reversed(swings):
        if s[0] == "L":
            last_swing_low = s[2]
            break
    stop_loss = round(last_swing_low * 0.99, 2)  # 1% buffer below last swing low
    stop_loss_pct = round((1 - stop_loss / current_close) * 100, 1)

    # Cap stop-loss at 8% max
    if stop_loss_pct > 8:
        stop_loss = round(current_close * 0.92, 2)
        stop_loss_pct = 8.0

    # ── Entry price ──
    entry_price = round(pivot_price, 2)  # breakout above pivot
    # If already near/above pivot, entry = current close
    if current_close >= pivot_price * 0.97:
        entry_price = round(current_close, 2)

    # ── VCP Score ──
    score = 0
    # Contraction quality (0-25)
    if contractions[0] > 0:
        score += (1 - contractions[-1] / contractions[0]) * 25
    # Volume dry-up (0-20)
    if vol_declining:
        score += (1 - vol_ratio) * 20
    # Tightness (0-20)
    if range_10d <= tightness_max:
        score += (1 - range_10d / tightness_max) * 20
    # Pivot proximity (0-15)
    if dist_to_pivot <= pivot_proximity:
        score += (1 - dist_to_pivot / pivot_proximity) * 15
    # Base depth quality (0-20) — shallower is better
    score += (1 - base_depth / base_max_depth) * 20

    return {
        "base_length_days": base_length,
        "base_depth_pct": round(base_depth * 100, 1),
        "num_contractions": len(contractions),
        "contractions_pct": [round(c * 100, 1) for c in contractions],
        "pivot_high": round(pivot_price, 2),
        "distance_to_pivot_pct": round(dist_to_pivot, 1),
        "volume_decline_ratio": round(vol_ratio, 2),
        "volume_declining": vol_declining,
        "tightness_10d_pct": round(range_10d, 1),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "stop_loss_pct": stop_loss_pct,
        "risk_reward_note": f"Risk {stop_loss_pct}% | Entry near {entry_price}",
        "vcp_score": round(score, 1),
    }


# ─────────────────────────────────────────────
# 6. FULL SCANNER
# ─────────────────────────────────────────────

def run_scan(stock_data: dict, rs_ratings: dict, params: dict = None) -> list[dict]:
    """Run full VCP scan on all stocks. Returns sorted list of results."""
    results = []

    for sym, df in stock_data.items():
        rs = rs_ratings.get(sym, 0)

        # Trend Template
        tt_pass, tt_details = check_trend_template(df, rs)
        if not tt_pass:
            continue

        # VCP Detection
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


# ─────────────────────────────────────────────
# 7. BACKTEST
# ─────────────────────────────────────────────

def backtest_scan(
    scan_results: list[dict],
    stock_data: dict,
    scan_date: pd.Timestamp,
    forward_days: list[int] = None,
) -> list[dict]:
    """
    For top 5 scan results, compute forward returns and stop-loss hits.
    Uses data AFTER scan_date.
    """
    if forward_days is None:
        forward_days = [5, 10, 20, 40]

    top5 = scan_results[:5]
    backtest_results = []

    for stock in top5:
        sym = stock["yf_symbol"]
        if sym not in stock_data:
            continue

        df = stock_data[sym]
        # Find the scan_date index
        future = df[df.index > scan_date]
        if len(future) < 2:
            continue

        entry_price = future["Open"].iloc[0]  # next day open
        stop_loss = stock["stop_loss"]
        # Adjust stop-loss relative to entry
        sl_pct = stock["stop_loss_pct"]
        stop_loss = round(entry_price * (1 - sl_pct / 100), 2)

        result = {
            "symbol": stock["symbol"],
            "scan_date": scan_date.strftime("%Y-%m-%d"),
            "entry_date": future.index[0].strftime("%Y-%m-%d"),
            "entry_price": round(entry_price, 2),
            "stop_loss": stop_loss,
            "stop_loss_pct": sl_pct,
            "vcp_score": stock["vcp_score"],
            "rs_rating": stock["rs_rating"],
        }

        # Check stop-loss hit
        sl_hit = False
        sl_hit_day = None
        for i in range(len(future)):
            if future["Low"].iloc[i] <= stop_loss:
                sl_hit = True
                sl_hit_day = i + 1
                break

        result["stop_loss_hit"] = sl_hit
        result["stop_loss_hit_day"] = sl_hit_day

        # Forward returns
        for fd in forward_days:
            if len(future) > fd:
                exit_price = future["Close"].iloc[fd]
                # If stop-loss was hit before this day, use stop-loss price
                if sl_hit and sl_hit_day <= fd:
                    ret = round((stop_loss - entry_price) / entry_price * 100, 1)
                    result[f"return_{fd}d"] = ret
                    result[f"exit_price_{fd}d"] = stop_loss
                    result[f"stopped_out_{fd}d"] = True
                else:
                    ret = round((exit_price - entry_price) / entry_price * 100, 1)
                    result[f"return_{fd}d"] = ret
                    result[f"exit_price_{fd}d"] = round(exit_price, 2)
                    result[f"stopped_out_{fd}d"] = False
            else:
                result[f"return_{fd}d"] = None
                result[f"exit_price_{fd}d"] = None
                result[f"stopped_out_{fd}d"] = None

        backtest_results.append(result)

    return backtest_results
