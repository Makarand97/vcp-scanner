#!/usr/bin/env python3
"""
Mark Minervini VCP (Volatility Contraction Pattern) Scanner for Nifty 500
=========================================================================
Run this script locally (requires: pip install yfinance niftystocks pandas numpy)
It generates a JSON file that the React frontend consumes.

Strategy:
- Trend Template (8 criteria for Stage 2 uptrend)
- VCP detection (progressive contractions + volume dry-up)
- Breakout confirmation (price above pivot on volume surge)

Exit Strategy:
- Stop Loss: 7-8% below entry OR below last contraction low
- Target: 2R-3R risk-reward
- Trailing Stop: 20-day EMA
- Time Stop: Exit if no progress in 15 trading days
"""

import json
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path

try:
    from niftystocks import ns
    NIFTY500 = ns.get_nifty500_with_ns()
except ImportError:
    print("niftystocks not installed. Using fallback Nifty 50 list.")
    NIFTY50_SYMBOLS = [
        "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN",
        "BHARTIARTL","ITC","KOTAKBANK","LT","HCLTECH","AXISBANK","ASIANPAINT",
        "MARUTI","SUNPHARMA","TITAN","BAJFINANCE","DMART","NESTLEIND",
        "NTPC","POWERGRID","ULTRACEMCO","WIPRO","ONGC","JSWSTEEL","TATAMOTORS",
        "ADANIENT","TATASTEEL","TECHM","HDFCLIFE","BAJAJFINSV","GRASIM",
        "INDUSINDBK","CIPLA","DIVISLAB","EICHERMOT","BPCL","COALINDIA",
        "DRREDDY","APOLLOHOSP","TATACONSUM","BRITANNIA","SBILIFE","M&M",
        "HEROMOTOCO","HINDALCO","ADANIPORTS","BAJAJ-AUTO","UPL"
    ]
    NIFTY500 = [s + ".NS" for s in NIFTY50_SYMBOLS]


def compute_rs_rating(stock_returns_6m, all_returns_6m):
    """Compute Relative Strength percentile rank vs universe."""
    if np.isnan(stock_returns_6m):
        return 0
    rank = np.sum(all_returns_6m < stock_returns_6m) / len(all_returns_6m) * 100
    return round(rank, 1)


def check_trend_template(df, idx, rs_rating):
    """
    Minervini's 8-point Trend Template check at a given index.
    Returns (pass: bool, details: dict)
    """
    if idx < 250 or idx >= len(df):
        return False, {}

    close = df['Close'].iloc[idx]
    sma50 = df['Close'].iloc[idx-49:idx+1].mean()
    sma150 = df['Close'].iloc[idx-149:idx+1].mean()
    sma200 = df['Close'].iloc[idx-199:idx+1].mean()
    sma200_prev = df['Close'].iloc[idx-220:idx-19].mean()  # ~1 month ago

    high_52w = df['High'].iloc[max(0,idx-251):idx+1].max()
    low_52w = df['Low'].iloc[max(0,idx-251):idx+1].min()

    c1 = close > sma150 and close > sma200  # Price > 150 & 200 SMA
    c2 = sma150 > sma200                    # 150 SMA > 200 SMA
    c3 = sma200 > sma200_prev               # 200 SMA trending up
    c4 = sma50 > sma150 and sma50 > sma200  # 50 SMA > 150 & 200 SMA
    c5 = close > sma50                      # Price > 50 SMA
    c6 = close >= low_52w * 1.25            # Price >= 25% above 52w low
    c7 = close >= high_52w * 0.75           # Price within 25% of 52w high
    c8 = rs_rating >= 70                    # RS rating >= 70

    passed = all([c1, c2, c3, c4, c5, c6, c7, c8])
    details = {
        'close': round(close, 2),
        'sma50': round(sma50, 2),
        'sma150': round(sma150, 2),
        'sma200': round(sma200, 2),
        'high_52w': round(high_52w, 2),
        'low_52w': round(low_52w, 2),
        'rs_rating': rs_rating,
        'criteria_met': sum([c1,c2,c3,c4,c5,c6,c7,c8]),
    }
    return passed, details


def detect_vcp(df, idx, lookback=60):
    """
    Detect VCP pattern: progressive contractions with volume dry-up.
    Returns (is_vcp: bool, vcp_details: dict)
    """
    if idx < lookback + 10 or idx >= len(df):
        return False, {}

    window = df.iloc[idx-lookback:idx+1]
    closes = window['Close'].values
    highs = window['High'].values
    lows = window['Low'].values
    volumes = window['Volume'].values

    # Find the highest point in the lookback (start of base)
    peak_idx = np.argmax(highs)
    if peak_idx < 5:  # Peak too early, not enough data
        return False, {}

    base_data = closes[peak_idx:]
    if len(base_data) < 10:
        return False, {}

    # Divide base into segments to find contractions
    seg_len = max(5, len(base_data) // 4)
    contractions = []
    for i in range(0, len(base_data) - seg_len + 1, seg_len):
        seg = base_data[i:i+seg_len]
        if len(seg) < 3:
            continue
        pct_range = (seg.max() - seg.min()) / seg.max() * 100
        avg_vol = volumes[peak_idx+i:peak_idx+i+seg_len].mean()
        contractions.append({'range_pct': pct_range, 'avg_volume': avg_vol})

    if len(contractions) < 2:
        return False, {}

    # Check progressive contraction (each range smaller than previous)
    progressive = True
    for i in range(1, len(contractions)):
        if contractions[i]['range_pct'] >= contractions[i-1]['range_pct']:
            progressive = False
            break

    # Check volume dry-up (declining volume)
    vol_declining = True
    for i in range(1, len(contractions)):
        if contractions[i]['avg_volume'] >= contractions[i-1]['avg_volume'] * 1.1:
            vol_declining = False
            break

    # Final contraction tightness (last contraction < 10%)
    final_tight = contractions[-1]['range_pct'] < 10

    # Pivot point: highest close in last 10 days
    recent = closes[-10:]
    pivot = float(np.max(recent))

    # ATR contraction check
    atr_recent = np.mean(highs[-10:] - lows[-10:])
    atr_lookback = np.mean(highs[:20] - lows[:20])
    atr_contracting = atr_recent < atr_lookback * 0.7

    is_vcp = progressive and (vol_declining or atr_contracting) and final_tight

    vcp_details = {
        'contractions': len(contractions),
        'ranges': [round(c['range_pct'], 2) for c in contractions],
        'progressive': progressive,
        'vol_declining': vol_declining,
        'atr_contracting': atr_contracting,
        'final_tightness': round(contractions[-1]['range_pct'], 2),
        'pivot': round(pivot, 2),
    }

    return is_vcp, vcp_details


def detect_breakout(df, idx, pivot):
    """Check if today is a breakout day (price crosses pivot on high volume)."""
    if idx < 50 or idx >= len(df):
        return False, {}

    close = df['Close'].iloc[idx]
    high = df['High'].iloc[idx]
    prev_close = df['Close'].iloc[idx-1]
    volume = df['Volume'].iloc[idx]
    avg_vol_50 = df['Volume'].iloc[idx-50:idx].mean()

    breakout = (close > pivot and prev_close <= pivot and
                volume > avg_vol_50 * 1.3)

    # Also accept if high breaks pivot with above-avg volume
    if not breakout:
        breakout = (high > pivot and prev_close <= pivot * 1.01 and
                    volume > avg_vol_50 * 1.2)

    details = {
        'close': round(close, 2),
        'pivot': round(pivot, 2),
        'volume': int(volume),
        'avg_volume_50': int(avg_vol_50),
        'volume_ratio': round(volume / avg_vol_50, 2) if avg_vol_50 > 0 else 0,
    }
    return breakout, details


def compute_exit(df, entry_idx, entry_price, stop_pct=0.08):
    """
    Compute exit using Minervini rules:
    - Initial stop: 7-8% below entry
    - Trail with 20 EMA after 2R profit
    - Time stop: 15 days no progress
    - Target: sell half at 2R, trail rest
    """
    stop_price = entry_price * (1 - stop_pct)
    risk = entry_price - stop_price
    target_2r = entry_price + 2 * risk
    target_3r = entry_price + 3 * risk

    max_price = entry_price
    exit_price = None
    exit_reason = None
    exit_idx = None
    holding_days = 0

    for i in range(entry_idx + 1, min(entry_idx + 120, len(df))):
        high = df['High'].iloc[i]
        low = df['Low'].iloc[i]
        close = df['Close'].iloc[i]

        max_price = max(max_price, high)
        holding_days += 1

        # Stop loss hit
        if low <= stop_price:
            exit_price = stop_price
            exit_reason = "stop_loss"
            exit_idx = i
            break

        # After reaching 2R, trail with 20 EMA
        if max_price >= target_2r:
            ema20 = df['Close'].iloc[max(0,i-19):i+1].ewm(span=20).mean().iloc[-1]
            if close < ema20:
                exit_price = close
                exit_reason = "trailing_stop_20ema"
                exit_idx = i
                break
            # Also raise stop to breakeven after 2R
            stop_price = max(stop_price, entry_price)

        # 3R target hit - take full profit
        if high >= target_3r:
            exit_price = target_3r
            exit_reason = "target_3r"
            exit_idx = i
            break

        # Time stop: 15 days with no new high
        if holding_days >= 15 and max_price <= entry_price * 1.02:
            exit_price = close
            exit_reason = "time_stop"
            exit_idx = i
            break

    # If still holding after 120 days, close at market
    if exit_price is None:
        exit_idx = min(entry_idx + 119, len(df) - 1)
        exit_price = df['Close'].iloc[exit_idx]
        exit_reason = "max_hold_120d"

    return_pct = (exit_price - entry_price) / entry_price * 100

    return {
        'entry_price': round(entry_price, 2),
        'exit_price': round(exit_price, 2),
        'return_pct': round(return_pct, 2),
        'holding_days': holding_days,
        'exit_reason': exit_reason,
        'exit_date': df.index[exit_idx].strftime('%Y-%m-%d') if exit_idx else None,
        'max_price': round(max_price, 2),
        'stop_price': round(entry_price * (1 - stop_pct), 2),
        'target_2r': round(target_2r, 2),
        'target_3r': round(target_3r, 2),
    }


def scan_stock(ticker, df, scan_dates, all_6m_returns):
    """Run VCP scan for a single stock across all scan dates."""
    signals = []

    for scan_date in scan_dates:
        if scan_date not in df.index:
            continue
        idx = df.index.get_loc(scan_date)
        if idx < 260:
            continue

        # Compute 6-month return
        ret_6m = (df['Close'].iloc[idx] / df['Close'].iloc[max(0, idx-126)] - 1) * 100
        rs = compute_rs_rating(ret_6m, all_6m_returns.get(scan_date.strftime('%Y-%m-%d'), np.array([0])))

        # Step 1: Trend Template
        tt_pass, tt_details = check_trend_template(df, idx, rs)
        if not tt_pass:
            continue

        # Step 2: VCP detection
        vcp_pass, vcp_details = detect_vcp(df, idx, lookback=60)
        if not vcp_pass:
            continue

        # Step 3: Breakout check
        pivot = vcp_details['pivot']
        bo_pass, bo_details = detect_breakout(df, idx, pivot)
        if not bo_pass:
            continue

        # Step 4: Compute exit/backtest
        entry_price = df['Close'].iloc[idx]
        exit_info = compute_exit(df, idx, entry_price)

        # Compute VCP score for ranking
        score = (
            tt_details['rs_rating'] * 0.3 +
            (10 - vcp_details['final_tightness']) * 3 +
            bo_details['volume_ratio'] * 10 +
            tt_details['criteria_met'] * 5
        )

        signal = {
            'ticker': ticker.replace('.NS', ''),
            'date': scan_date.strftime('%Y-%m-%d'),
            'entry_price': round(entry_price, 2),
            'score': round(score, 1),
            'trend_template': tt_details,
            'vcp': vcp_details,
            'breakout': bo_details,
            'backtest': exit_info,
        }
        signals.append(signal)

    return signals


def main():
    print("=" * 60)
    print("  Minervini VCP Scanner for Nifty 500")
    print("=" * 60)

    # Configuration
    lookback_years = 1.5  # Extra data for MA computation
    scan_period_days = 365  # Scan last 1 year

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=int(lookback_years * 365))
    scan_start = end_date - datetime.timedelta(days=scan_period_days)

    print(f"Data range: {start_date} to {end_date}")
    print(f"Scan range: {scan_start} to {end_date}")
    print(f"Stocks: {len(NIFTY500)}")
    print()

    # Download data in batches
    print("Downloading price data...")
    all_data = {}
    batch_size = 50
    for i in range(0, len(NIFTY500), batch_size):
        batch = NIFTY500[i:i+batch_size]
        tickers_str = " ".join(batch)
        print(f"  Batch {i//batch_size + 1}/{(len(NIFTY500)-1)//batch_size + 1}: {len(batch)} stocks...")
        try:
            data = yf.download(tickers_str, start=str(start_date), end=str(end_date),
                             group_by='ticker', progress=False, threads=True)
            for t in batch:
                try:
                    if len(batch) == 1:
                        stock_df = data.copy()
                    else:
                        stock_df = data[t].copy()
                    stock_df = stock_df.dropna(subset=['Close'])
                    if len(stock_df) > 200:
                        all_data[t] = stock_df
                except:
                    pass
        except Exception as e:
            print(f"    Error: {e}")

    print(f"\nLoaded data for {len(all_data)} stocks")

    # Get all trading dates in scan period
    sample_df = list(all_data.values())[0]
    scan_dates = [d for d in sample_df.index if d.date() >= scan_start]
    print(f"Scanning {len(scan_dates)} trading days")

    # Pre-compute 6-month returns for RS rating
    print("Computing RS ratings...")
    all_6m_returns = {}
    for scan_date in scan_dates:
        date_key = scan_date.strftime('%Y-%m-%d')
        returns = []
        for ticker, df in all_data.items():
            if scan_date in df.index:
                idx = df.index.get_loc(scan_date)
                if idx >= 126:
                    ret = (df['Close'].iloc[idx] / df['Close'].iloc[idx-126] - 1) * 100
                    returns.append(ret)
        all_6m_returns[date_key] = np.array(returns) if returns else np.array([0])

    # Scan all stocks
    print("\nScanning for VCP breakouts...")
    all_signals = []
    for i, (ticker, df) in enumerate(all_data.items()):
        if (i + 1) % 50 == 0:
            print(f"  Scanned {i+1}/{len(all_data)} stocks...")
        signals = scan_stock(ticker, df, scan_dates, all_6m_returns)
        all_signals.extend(signals)

    print(f"\nTotal VCP breakout signals found: {len(all_signals)}")

    # Group by date and rank top 10
    from collections import defaultdict
    daily_signals = defaultdict(list)
    for sig in all_signals:
        daily_signals[sig['date']].append(sig)

    # Sort each day's signals by score and keep top 10
    output_data = {}
    for date, sigs in sorted(daily_signals.items()):
        ranked = sorted(sigs, key=lambda x: x['score'], reverse=True)[:10]
        output_data[date] = ranked

    # Generate output
    output = {
        'generated_at': datetime.datetime.now().isoformat(),
        'scan_start': scan_start.isoformat(),
        'scan_end': end_date.isoformat(),
        'total_stocks': len(all_data),
        'total_signals': len(all_signals),
        'strategy': {
            'name': 'Minervini VCP Breakout Scanner',
            'trend_template': [
                'Price > 150 SMA & 200 SMA',
                '150 SMA > 200 SMA',
                '200 SMA trending up (1 month)',
                '50 SMA > 150 SMA & 200 SMA',
                'Price > 50 SMA',
                'Price >= 25% above 52-week low',
                'Price within 25% of 52-week high',
                'RS Rating >= 70',
            ],
            'vcp_criteria': [
                'Progressive contractions (each smaller than prior)',
                'Declining volume during contractions',
                'ATR contraction (recent ATR < 70% of base ATR)',
                'Final contraction tightness < 10%',
            ],
            'breakout': 'Price crosses pivot on 1.3x average volume',
            'exit': {
                'stop_loss': '8% below entry',
                'target': '2R-3R risk-reward',
                'trailing': '20 EMA after 2R reached',
                'time_stop': '15 days with no progress',
                'max_hold': '120 days',
            }
        },
        'daily_signals': output_data,
    }

    output_path = Path('vcp_scan_results.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")

    # Summary stats
    total_trades = sum(len(v) for v in output_data.values())
    if total_trades > 0:
        all_returns = [s['backtest']['return_pct'] for sigs in output_data.values() for s in sigs]
        winners = [r for r in all_returns if r > 0]
        losers = [r for r in all_returns if r <= 0]
        print(f"\n{'='*40}")
        print(f"BACKTEST SUMMARY")
        print(f"{'='*40}")
        print(f"Total signals: {total_trades}")
        print(f"Win rate: {len(winners)/total_trades*100:.1f}%")
        print(f"Avg return: {np.mean(all_returns):.2f}%")
        print(f"Avg winner: {np.mean(winners):.2f}%" if winners else "No winners")
        print(f"Avg loser: {np.mean(losers):.2f}%" if losers else "No losers")
        print(f"Best: {max(all_returns):.2f}%")
        print(f"Worst: {min(all_returns):.2f}%")


if __name__ == '__main__':
    main()
