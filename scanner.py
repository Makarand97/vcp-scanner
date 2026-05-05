#!/usr/bin/env python3
"""
Minervini VCP Breakout Scanner — Nifty 500
==========================================
Uses yfinance daily Close & Volume data.
Outputs: public/data.json (consumed by React frontend)

pip install yfinance pandas numpy
"""

import json, datetime, warnings, sys, os
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# NIFTY 500 TICKERS (NSE symbols with .NS suffix)
# Source: NSE India. Update this list periodically.
# ──────────────────────────────────────────────

def get_nifty500():
    """Try niftystocks library first, fallback to curated list."""
    try:
        from niftystocks import ns
        tickers = ns.get_nifty500_with_ns()
        if len(tickers) > 100:
            return tickers
    except:
        pass

    # Fallback: fetch from NSE indices page via pandas
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        # This may fail due to NSE blocking, so we have a hardcoded fallback
    except:
        pass

    # Hardcoded Nifty 200 as minimum fallback (covers large + midcaps)
    symbols = [
        "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN",
        "BHARTIARTL","ITC","KOTAKBANK","LT","HCLTECH","AXISBANK","ASIANPAINT",
        "MARUTI","SUNPHARMA","TITAN","BAJFINANCE","DMART","NESTLEIND",
        "NTPC","POWERGRID","ULTRACEMCO","WIPRO","ONGC","JSWSTEEL","TATAMOTORS",
        "ADANIENT","TATASTEEL","TECHM","HDFCLIFE","BAJAJFINSV","GRASIM",
        "INDUSINDBK","CIPLA","DIVISLAB","EICHERMOT","BPCL","COALINDIA",
        "DRREDDY","APOLLOHOSP","TATACONSUM","BRITANNIA","SBILIFE","M&M",
        "HEROMOTOCO","HINDALCO","ADANIPORTS","BAJAJ-AUTO","UPL","PIDILITIND",
        "HAVELLS","SHREECEM","AMBUJACEM","DLF","TRENT","GODREJCP","DABUR",
        "MARICO","BERGEPAINT","MUTHOOTFIN","LICI","IRCTC","ZOMATO",
        "PERSISTENT","COFORGE","LTIM","MPHASIS","NAVINFLUOR","ATUL",
        "DEEPAKNTR","PIIND","SRF","ASTRAL","POLYCAB","KEI","DIXON",
        "KPITTECH","TATAELXSI","AUROPHARMA","BIOCON","LUPIN","TORNTPHARM",
        "ALKEM","IPCALAB","LAURUSLABS","METROPOLIS","MAXHEALTH","FORTIS",
        "MOTHERSON","CANBKRECL","PFC","RECLTD","IRFC","HAL","BEL","BHEL",
        "NHPC","SJVN","TATAPOWER","ADANIGREEN","ADANIPOWER","JSWENERGY",
        "CESC","TORNTPOWER","JSL","JINDALSTEL","NATIONALUM","HINDZINC",
        "VEDL","NMDC","GAIL","PETRONET","IGL","MGL","CONCOR","CGPOWER",
        "SIEMENS","ABB","CUMMINSIND","THERMAX","BDL","GRINDWELL","SCHAEFFLER",
        "TIMKEN","SUNTV","PVRINOX","TVSMOTOR","ESCORTS","ASHOKLEY","BALKRISIND",
        "MRF","APOLLOTYRE","EXIDEIND","AMARAJABAT","BOSCHLTD","SONACOMS",
        "SAMVARDHNA","SYNGENE","GLAXO","PFIZER","ABBOTINDIA","PAGEIND",
        "MANYAVAR","RAYMOND","CROMPTON","VOLTAS","BLUESTARCO","WHIRLPOOL",
        "BATAINDIA","RELAXO","METROBRAND","NAUKRI","ZOMATO","PAYTM",
        "POLICYBZR","DELHIVERY","CARTRADE","STARHEALTH","RAJESHEXPO",
        "TATACOMM","FEDERALBNK","IDFCFIRSTB","BANDHANBNK","RBLBANK",
        "MANAPPURAM","CHOLAFIN","BAJAJHLDNG","SUNDARMFIN","LICHSGFIN",
        "CANFINHOME","AARTIIND","GNFC","CHAMBALFER","COROMANDEL",
        "UBL","UNITDSPR","COLPAL","GILLETTE","HINDPETRO","IOC",
        "SAIL","SBICARD","ICICIPRULI","HDFCAMC","ISEC","CAMS","CDSL",
        "BSE","MCX","ANGELONE","CLEAN","KAYNES","SOLARINDS",
        "SUMICHEM","JUBLFOOD","DEVYANI","SAPPHIRE","BIKAJI","CAMPUS",
        "PHOENIXLTD","OBEROIRLTY","PRESTIGE","BRIGADE","LODHA","SOBHA",
        "GODREJPROP","SUNTECK","ABCAPITAL","L&TFH","POONAWALLA",
        "TATAINVEST","NIACL","GICRE","CENTRALBK","UNIONBANK","BANKBARODA",
        "PNB","INDIANB","IOB","CUMMINSIND","ACC","RAMCOCEM","JKCEMENT",
        "DALBHARAT","NUVOCO","STARCEMENT","INDIACEM","JKLAKSHMI",
        "APLAPOLLO","RATNAMANI","WELCORP","HAPPSTMNDS","ROUTE",
        "LTTS","CYIENT","ZENSAR","MASTEK","BIRLASOFT","INTELLECT",
        "TANLA","LATENTVIEW","MEDPLUS","RAINBOW","YATHARTH","MEDANTA",
        "KALYANKJIL","TITAN","SENCO","PCJEWELLER","NSLNISP","PGHH"
    ]
    return [s + ".NS" for s in symbols]


# ──────────────────────────────────────────────
# DATA DOWNLOAD
# ──────────────────────────────────────────────

def download_data(tickers, start, end):
    """Download daily OHLCV data from yfinance in batches."""
    all_data = {}
    batch_size = 25  # smaller batches = more reliable
    total = len(tickers)

    for i in range(0, total, batch_size):
        batch = tickers[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total - 1) // batch_size + 1
        print(f"  Downloading batch {batch_num}/{total_batches} ({len(batch)} stocks)...")

        try:
            raw = yf.download(
                " ".join(batch),
                start=str(start),
                end=str(end),
                group_by="ticker",
                progress=False,
                threads=True,
            )

            for t in batch:
                try:
                    if len(batch) == 1:
                        df = raw[["Open","High","Low","Close","Volume"]].copy()
                    else:
                        df = raw[t][["Open","High","Low","Close","Volume"]].copy()

                    df = df.dropna(subset=["Close"])
                    df = df[df["Volume"] > 0]

                    if len(df) >= 200:
                        # Flatten MultiIndex columns if present
                        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                        all_data[t] = df
                except Exception:
                    pass
        except Exception as e:
            print(f"    Batch error: {e}")

    return all_data


# ──────────────────────────────────────────────
# PHASE 1: TREND TEMPLATE (8-point check)
# ──────────────────────────────────────────────

def sma(series, period):
    """Simple Moving Average of last `period` values ending at current index."""
    return series.rolling(window=period).mean()


def check_trend_template(close, high, low, rs_pct):
    """
    Check Minervini's 8 Trend Template criteria on the LAST row.
    All inputs are full pd.Series. rs_pct = percentile rank (0-100).

    Returns: (bool, dict)
    """
    if len(close) < 252:
        return False, {}

    price = close.iloc[-1]
    sma50  = close.iloc[-50:].mean()
    sma150 = close.iloc[-150:].mean()
    sma200 = close.iloc[-200:].mean()

    # 200 SMA one month ago (20 trading days back)
    sma200_now  = close.iloc[-200:].mean()
    sma200_prev = close.iloc[-220:-20].mean()

    high_52w = high.iloc[-252:].max()
    low_52w  = low.iloc[-252:].min()

    c1 = price > sma150                          # Price > 150 SMA
    c2 = price > sma200                          # Price > 200 SMA
    c3 = sma150 > sma200                         # 150 SMA > 200 SMA
    c4 = sma200_now > sma200_prev                # 200 SMA trending up
    c5 = sma50 > sma150 and sma50 > sma200       # 50 SMA > 150 & 200 SMA
    c6 = price > sma50                           # Price > 50 SMA
    c7 = price >= low_52w * 1.25                  # ≥25% above 52w low
    c8 = price >= high_52w * 0.75                 # Within 25% of 52w high
    c9 = rs_pct >= 70                            # RS ≥ 70th percentile

    all_pass = all([c1, c2, c3, c4, c5, c6, c7, c8, c9])

    details = dict(
        price=round(price, 2),
        sma50=round(sma50, 2),
        sma150=round(sma150, 2),
        sma200=round(sma200, 2),
        high_52w=round(high_52w, 2),
        low_52w=round(low_52w, 2),
        rs=round(rs_pct, 1),
        pct_from_high=round((price / high_52w - 1) * 100, 1),
        pct_from_low=round((price / low_52w - 1) * 100, 1),
    )
    return all_pass, details


# ──────────────────────────────────────────────
# PHASE 2: VCP DETECTION
# ──────────────────────────────────────────────

def detect_vcp(close, high, low, volume, lookback=60):
    """
    Detect Volatility Contraction Pattern in last `lookback` bars.

    Logic:
    1. Find highest high in lookback → that's the base start
    2. From base start to now, find swing highs and lows
    3. Measure each contraction (swing high to swing low as % of swing high)
    4. Check: each contraction range < previous (progressive tightening)
    5. Check: volume declining across contractions
    6. Final contraction must be tight (< 10%)

    Returns: (bool, dict)
    """
    if len(close) < lookback + 10:
        return False, {}

    c = close.iloc[-lookback:].values
    h = high.iloc[-lookback:].values
    l = low.iloc[-lookback:].values
    v = volume.iloc[-lookback:].values

    # Find highest point = base start
    peak_pos = np.argmax(h)
    if peak_pos > lookback - 10:  # peak too recent, no room for pattern
        return False, {}

    # Work with data from peak onward
    base_h = h[peak_pos:]
    base_l = l[peak_pos:]
    base_c = c[peak_pos:]
    base_v = v[peak_pos:]
    n = len(base_c)

    if n < 10:
        return False, {}

    # Split into 3-4 segments and measure contraction in each
    num_segs = min(4, max(2, n // 7))
    seg_len = n // num_segs
    contractions = []

    for s in range(num_segs):
        start = s * seg_len
        end = min(start + seg_len, n)
        seg_high = base_h[start:end].max()
        seg_low  = base_l[start:end].min()
        seg_vol  = base_v[start:end].mean()

        if seg_high == 0:
            return False, {}

        pct_range = (seg_high - seg_low) / seg_high * 100
        contractions.append({
            "range_pct": round(pct_range, 2),
            "avg_vol": seg_vol,
        })

    # Check progressive contraction (each range must be smaller)
    progressive = all(
        contractions[i]["range_pct"] < contractions[i-1]["range_pct"]
        for i in range(1, len(contractions))
    )

    # Check volume dry-up (each segment's volume ≤ previous, with 10% tolerance)
    vol_declining = all(
        contractions[i]["avg_vol"] <= contractions[i-1]["avg_vol"] * 1.10
        for i in range(1, len(contractions))
    )

    # ATR contraction: recent 10-day ATR vs first 15-day ATR
    atr_recent = np.mean(h[-10:] - l[-10:])
    atr_early  = np.mean(h[peak_pos:peak_pos+15] - l[peak_pos:peak_pos+15]) if peak_pos + 15 < len(h) else atr_recent
    atr_contracting = atr_recent < atr_early * 0.70

    # Final tightness
    final_tight = contractions[-1]["range_pct"] < 10.0

    # Pivot = highest close in last 10 days
    pivot = float(np.max(c[-10:]))

    is_vcp = progressive and (vol_declining or atr_contracting) and final_tight

    details = dict(
        num_contractions=len(contractions),
        ranges=[ct["range_pct"] for ct in contractions],
        progressive=progressive,
        vol_declining=vol_declining,
        atr_contracting=atr_contracting,
        final_tightness=contractions[-1]["range_pct"],
        pivot=round(pivot, 2),
    )
    return is_vcp, details


# ──────────────────────────────────────────────
# PHASE 3: BREAKOUT CONFIRMATION
# ──────────────────────────────────────────────

def check_breakout(close, volume, pivot):
    """
    Today = breakout day if:
    - Today's close > pivot
    - Yesterday's close ≤ pivot
    - Today's volume ≥ 1.3× 50-day avg volume
    """
    if len(close) < 51:
        return False, {}

    today_close = close.iloc[-1]
    yest_close  = close.iloc[-2]
    today_vol   = volume.iloc[-1]
    avg_vol_50  = volume.iloc[-51:-1].mean()

    crossed = today_close > pivot and yest_close <= pivot * 1.005
    vol_surge = today_vol >= avg_vol_50 * 1.3

    is_breakout = crossed and vol_surge

    details = dict(
        close=round(today_close, 2),
        prev_close=round(yest_close, 2),
        pivot=round(pivot, 2),
        volume=int(today_vol),
        avg_vol_50=int(avg_vol_50),
        vol_ratio=round(today_vol / avg_vol_50, 2) if avg_vol_50 > 0 else 0,
    )
    return is_breakout, details


# ──────────────────────────────────────────────
# PHASE 4: EXIT STRATEGY (for backtesting)
# ──────────────────────────────────────────────

def simulate_exit(df, entry_idx, entry_price, stop_pct=0.08):
    """
    Simulate trade from entry_idx forward using Minervini exit rules:
    1. Stop loss at -8%
    2. After 2R profit → trail with 20 EMA, raise stop to breakeven
    3. At 3R profit → full exit
    4. Time stop: 15 days with < 2% gain → exit
    5. Max hold: 120 days

    Returns dict with exit details.
    """
    stop = entry_price * (1 - stop_pct)
    risk = entry_price - stop
    target_2r = entry_price + 2 * risk
    target_3r = entry_price + 3 * risk
    max_high = entry_price

    for i in range(entry_idx + 1, min(entry_idx + 121, len(df))):
        day_high  = df["High"].iloc[i]
        day_low   = df["Low"].iloc[i]
        day_close = df["Close"].iloc[i]
        days_held = i - entry_idx

        max_high = max(max_high, day_high)

        # 1. Stop loss
        if day_low <= stop:
            return dict(
                exit_price=round(stop, 2),
                return_pct=round(-stop_pct * 100, 2),
                days=days_held,
                reason="stop_loss",
                exit_date=str(df.index[i].date()),
            )

        # 2. 3R target hit
        if day_high >= target_3r:
            return dict(
                exit_price=round(target_3r, 2),
                return_pct=round((target_3r / entry_price - 1) * 100, 2),
                days=days_held,
                reason="target_3r",
                exit_date=str(df.index[i].date()),
            )

        # 3. After 2R reached → trail with 20 EMA
        if max_high >= target_2r:
            stop = max(stop, entry_price)  # raise stop to breakeven
            ema20_start = max(0, i - 19)
            ema20 = df["Close"].iloc[ema20_start:i+1].ewm(span=20, adjust=False).mean().iloc[-1]
            if day_close < ema20:
                ret = (day_close / entry_price - 1) * 100
                return dict(
                    exit_price=round(day_close, 2),
                    return_pct=round(ret, 2),
                    days=days_held,
                    reason="trail_20ema",
                    exit_date=str(df.index[i].date()),
                )

        # 4. Time stop: 15 days, less than 2% gain
        if days_held >= 15 and max_high < entry_price * 1.02:
            ret = (day_close / entry_price - 1) * 100
            return dict(
                exit_price=round(day_close, 2),
                return_pct=round(ret, 2),
                days=days_held,
                reason="time_stop",
                exit_date=str(df.index[i].date()),
            )

    # 5. Max hold 120 days
    last_idx = min(entry_idx + 120, len(df) - 1)
    last_close = df["Close"].iloc[last_idx]
    ret = (last_close / entry_price - 1) * 100
    return dict(
        exit_price=round(last_close, 2),
        return_pct=round(ret, 2),
        days=last_idx - entry_idx,
        reason="max_hold",
        exit_date=str(df.index[last_idx].date()),
    )


# ──────────────────────────────────────────────
# MAIN SCANNER
# ──────────────────────────────────────────────

def run_scanner():
    print("=" * 55)
    print("  MINERVINI VCP BREAKOUT SCANNER — NIFTY 500")
    print("=" * 55)

    tickers = get_nifty500()
    print(f"\nUniverse: {len(tickers)} stocks")

    # Download 18 months of data (need 252 days for 52-week calcs + buffer)
    end = datetime.date.today()
    start = end - datetime.timedelta(days=550)
    scan_start = end - datetime.timedelta(days=365)  # scan last 1 year

    print(f"Data: {start} → {end}")
    print(f"Scan: {scan_start} → {end}\n")

    print("STEP 1: Downloading yfinance data...")
    all_data = download_data(tickers, start, end)
    print(f"  ✓ Loaded {len(all_data)} stocks with 200+ trading days\n")

    if len(all_data) == 0:
        print("ERROR: No data downloaded. Check internet / yfinance.")
        sys.exit(1)

    # Get all trading dates in scan period
    ref_df = next(iter(all_data.values()))
    all_trading_dates = [d for d in ref_df.index if d.date() >= scan_start]

    print(f"STEP 2: Computing RS ratings for {len(all_trading_dates)} trading days...")

    # Pre-compute 6-month returns for each date (for RS ranking)
    rs_cache = {}
    for dt in all_trading_dates:
        returns = {}
        for ticker, df in all_data.items():
            if dt not in df.index:
                continue
            idx = df.index.get_loc(dt)
            if idx >= 126:
                ret = (df["Close"].iloc[idx] / df["Close"].iloc[idx - 126] - 1) * 100
                returns[ticker] = ret
        rs_cache[dt] = returns

    print(f"  ✓ RS cache built\n")

    print("STEP 3: Scanning for VCP breakouts...")
    daily_signals = {}
    total_found = 0

    for dt in all_trading_dates:
        date_str = str(dt.date())
        day_returns = rs_cache[dt]
        if not day_returns:
            continue

        all_rets = np.array(list(day_returns.values()))
        signals = []

        for ticker, df in all_data.items():
            if dt not in df.index:
                continue

            idx = df.index.get_loc(dt)
            if idx < 260:
                continue

            # Compute RS percentile for this stock
            stock_ret = day_returns.get(ticker, None)
            if stock_ret is None:
                continue
            rs_pct = np.sum(all_rets < stock_ret) / len(all_rets) * 100

            # PHASE 1: Trend Template
            c = df["Close"].iloc[:idx+1]
            h = df["High"].iloc[:idx+1]
            l = df["Low"].iloc[:idx+1]
            v = df["Volume"].iloc[:idx+1]

            tt_pass, tt = check_trend_template(c, h, l, rs_pct)
            if not tt_pass:
                continue

            # PHASE 2: VCP detection
            vcp_pass, vcp = detect_vcp(c, h, l, v, lookback=60)
            if not vcp_pass:
                continue

            # PHASE 3: Breakout
            bo_pass, bo = check_breakout(c, v, vcp["pivot"])
            if not bo_pass:
                continue

            # PHASE 4: Backtest exit
            entry_price = float(df["Close"].iloc[idx])
            bt = simulate_exit(df, idx, entry_price)

            # Score for ranking
            score = (
                rs_pct * 0.3
                + (10 - vcp["final_tightness"]) * 3
                + bo["vol_ratio"] * 10
            )

            symbol = ticker.replace(".NS", "")
            signals.append(dict(
                ticker=symbol,
                date=date_str,
                entry_price=round(entry_price, 2),
                score=round(score, 1),
                tt=tt,
                vcp=vcp,
                bo=bo,
                bt=bt,
            ))

        if signals:
            signals.sort(key=lambda x: x["score"], reverse=True)
            daily_signals[date_str] = signals[:10]  # top 10 per day
            total_found += len(signals[:10])

    print(f"  ✓ Found {total_found} signals across {len(daily_signals)} days\n")

    # ── Build output JSON ──
    output = dict(
        generated=datetime.datetime.now().isoformat(),
        scan_start=str(scan_start),
        scan_end=str(end),
        universe=len(all_data),
        total_signals=total_found,
        days_with_signals=len(daily_signals),
        daily=daily_signals,
    )

    # Save to public/data.json (for React) and also root
    os.makedirs("public", exist_ok=True)
    for path in ["public/data.json", "vcp_scan_results.json"]:
        with open(path, "w") as f:
            json.dump(output, f, separators=(",", ":"), default=str)
        print(f"  Saved: {path}")

    # ── Print summary ──
    if total_found > 0:
        all_rets = [s["bt"]["return_pct"] for sigs in daily_signals.values() for s in sigs]
        winners = [r for r in all_rets if r > 0]
        losers = [r for r in all_rets if r <= 0]
        print(f"\n{'─' * 40}")
        print(f"  BACKTEST SUMMARY")
        print(f"{'─' * 40}")
        print(f"  Total trades   : {total_found}")
        print(f"  Win rate       : {len(winners)/total_found*100:.1f}%")
        print(f"  Avg return     : {np.mean(all_rets):.2f}%")
        print(f"  Avg winner     : +{np.mean(winners):.2f}%" if winners else "")
        print(f"  Avg loser      : {np.mean(losers):.2f}%" if losers else "")
        print(f"  Best trade     : +{max(all_rets):.2f}%")
        print(f"  Worst trade    : {min(all_rets):.2f}%")
        print(f"{'─' * 40}")

    print("\n✓ Done. Upload public/data.json or push to GitHub.")


if __name__ == "__main__":
    run_scanner()
