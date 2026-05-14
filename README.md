# VCP Scanner v2 — Optimized for Positive Returns

## What's New in v2

- **Breakout-confirmed entry** — waits for price > pivot on high volume (not blind entry)
- **Trailing stop-loss** — locks profits after 5% gain, trails at 8% below peak
- **ATR contraction check** — validates volatility is actually contracting
- **EMA momentum filter** — EMA 8 > EMA 21 required
- **Tighter defaults** — RS ≥ 80, within 15% of 52W high
- **Multi-date backtest** — aggregate stats across dozens of scan dates
- **Auto-optimizer** — tests 6,500+ parameter combos, finds best settings
- **Floating charts** — click any stock symbol to see 1-year chart with pivot/SL lines

---

## Deploy (Free, 5 Minutes)

### Step 1: GitHub
- Create account at https://github.com
- New repository → name `vcp-scanner` → Public → Create

### Step 2: Upload Files
- Click "uploading an existing file"
- Drag: `app.py`, `scanner.py`, `requirements.txt`
- Commit changes

### Step 3: Streamlit Cloud
- Go to https://share.streamlit.io
- Sign in with GitHub
- New app → select `vcp-scanner` repo → main file: `app.py` → Deploy

### Done!
App is live. Share the URL with anyone.

---

## Run Locally

```bash
pip install streamlit yfinance pandas numpy plotly requests
streamlit run app.py
```

---

## Recommended First Steps

1. Go to **Optimize** tab → run optimizer on 1-year data (takes 10-30 min)
2. Note the best parameters → set them in sidebar
3. Run **Multi-Date Backtest** to validate
4. When satisfied with metrics → run **Live Scan** daily

---

## Target Metrics

| Metric | Aim For |
|--------|---------|
| Win Rate | > 45% |
| Avg Return | > 2% per trade |
| Profit Factor | > 1.5 |
| Avg Loser | < -5% |

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI (5 tabs: scan, backtest, multi-backtest, optimize, guide) |
| `scanner.py` | Engine (trend template, VCP detection, trade simulation, optimizer) |
| `requirements.txt` | Dependencies |

---

## Cost: INR 0
Streamlit Cloud + yfinance + GitHub = all free.
