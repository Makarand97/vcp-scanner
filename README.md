# VCP Scanner — Deploy Guide

A web application to scan Indian (NSE) stocks using Mark Minervini's VCP strategy.  
**No coding required to deploy.**

---

## What This App Does

- Scans Nifty 500 stocks daily using Trend Template + VCP pattern detection
- Shows entry price, stop-loss, and VCP quality score
- Backtest any past date: see top 5 picks and their actual returns with stop-loss tracking

---

## Option A: Deploy Free on Streamlit Cloud (Recommended)

### Step 1: Create a GitHub Account
- Go to https://github.com and sign up (free)

### Step 2: Create a New Repository
- Click the **+** icon (top right) → **New repository**
- Name: `vcp-scanner`
- Set to **Public**
- Click **Create repository**

### Step 3: Upload Files
- On the repository page, click **uploading an existing file**
- Drag and drop these 3 files:
  - `app.py`
  - `scanner.py`
  - `requirements.txt`
- Click **Commit changes**

### Step 4: Deploy on Streamlit Cloud
- Go to https://share.streamlit.io
- Sign in with your GitHub account
- Click **New app**
- Select your repository: `your-username/vcp-scanner`
- Branch: `main`
- Main file path: `app.py`
- Click **Deploy!**

### Step 5: Done!
- Your app will be live at `https://your-username-vcp-scanner.streamlit.app`
- Share the link with anyone
- It will auto-update when you update files on GitHub

---

## Option B: Run Locally on Your Computer

### Step 1: Install Python
- Download Python 3.10+ from https://www.python.org/downloads/
- During install, **check "Add Python to PATH"**

### Step 2: Open Terminal
- **Windows:** Search for "Command Prompt" or "PowerShell"
- **Mac:** Open "Terminal" from Applications

### Step 3: Install Dependencies
```
pip install streamlit yfinance pandas numpy requests
```

### Step 4: Run the App
Navigate to the folder containing the files and run:
```
cd path/to/vcp-scanner
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## How to Use

### Live Scan
1. Click **Run Live Scan** button
2. Wait 3-8 minutes (first run fetches data for 500 stocks)
3. Results are cached for 1 hour — subsequent runs are instant
4. Review the top stocks sorted by VCP Score

### Backtest
1. Go to the **Backtest** tab
2. Pick a historical date (at least 5 days ago)
3. Click **Run Backtest**
4. See top 5 picks with 5/10/20/40-day returns
5. Stop-loss tracking shows if SL was triggered

### Parameters
Use the **sidebar** to adjust:
- RS Rating threshold (higher = stricter)
- Base depth/length
- Number of contractions required
- Volume decline sensitivity
- Tightness and pivot proximity

---

## Entry & Stop-Loss Rules

| Rule | Details |
|------|---------|
| **Entry** | Buy on breakout above pivot price. If already near pivot, enter at current close. |
| **Stop-Loss** | 1% below last contraction low. Maximum 8% from entry. |
| **Position Size** | Risk 1-2% of capital. Example: INR 10L capital, 2% risk = INR 20K max loss per trade. If SL is 5%, position size = INR 20K / 5% = INR 4L. |
| **Target** | Sell 50% at 20% profit. Trail remainder with 10-day low. |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No stocks passed" | Relax parameters: lower RS to 60, increase base depth to 40%, increase pivot proximity to 15% |
| Slow first run | Normal — fetching 500 stocks takes time. Cached after first run. |
| yfinance errors | yfinance is free but rate-limited. Wait 5 min and retry. |
| Fewer than 500 stocks | NSE symbol list fetch may fail. App falls back to Nifty 50. Upload custom list if needed. |
| Deploy fails | Ensure `requirements.txt` is in the repo root alongside `app.py` and `scanner.py` |

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit web interface (UI, tabs, charts) |
| `scanner.py` | Core scanning engine (Trend Template, VCP detection, backtest) |
| `requirements.txt` | Python package dependencies |
| `README.md` | This file |

---

## Cost

- **Streamlit Cloud:** Free
- **yfinance data:** Free
- **GitHub:** Free
- **Total: INR 0**
