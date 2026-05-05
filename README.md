# VCP Breakout Scanner — Deployment Guide

## What You Need (all free)
1. **GitHub account** — [github.com](https://github.com) (to store your code)
2. **Vercel account** — [vercel.com](https://vercel.com) (to host your website)
3. **Git** installed on your computer — [git-scm.com/downloads](https://git-scm.com/downloads)
4. **Node.js** installed — [nodejs.org](https://nodejs.org) (download the LTS version)
5. **Python 3** installed — [python.org](https://python.org) (for running the scanner)

---

## STEP 1: Create a GitHub Account (skip if you already have one)

1. Go to [github.com](https://github.com)
2. Click **Sign Up**
3. Follow the prompts to create your free account

---

## STEP 2: Install Git & Node.js (skip if already installed)

### Check if already installed:
Open **Terminal** (Mac) or **Command Prompt** (Windows) and type:
```
git --version
node --version
```
If you see version numbers, they're already installed.

### If not installed:
- **Git**: Download from [git-scm.com/downloads](https://git-scm.com/downloads), run installer, click Next through everything
- **Node.js**: Download from [nodejs.org](https://nodejs.org) (LTS version), run installer, click Next through everything

---

## STEP 3: Upload Code to GitHub

### Option A: Using GitHub Website (Easiest)
1. Go to [github.com](https://github.com) and log in
2. Click the **+** icon (top right) → **New repository**
3. Name it: `vcp-scanner`
4. Keep it **Public**
5. Click **Create repository**
6. On the next page, click **"uploading an existing file"** link
7. **Drag and drop ALL files** from the unzipped `vcp-scanner-app` folder:
   - `index.html`
   - `package.json`
   - `vite.config.js`
   - `.gitignore`
   - `src/` folder (containing `main.jsx` and `App.jsx`)
   - `public/` folder
   - `vcp_scanner.py`
8. Click **Commit changes**

### Option B: Using Terminal (if comfortable)
```bash
cd vcp-scanner-app
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/vcp-scanner.git
git push -u origin main
```

---

## STEP 4: Deploy on Vercel (Free Hosting)

1. Go to [vercel.com](https://vercel.com)
2. Click **Sign Up** → **Continue with GitHub**
3. Authorize Vercel to access your GitHub
4. Once logged in, click **"Add New..."** → **Project**
5. You'll see your repositories — find **vcp-scanner** and click **Import**
6. On the configure screen:
   - **Framework Preset**: It should auto-detect **Vite** (if not, select it)
   - Leave everything else as default
7. Click **Deploy**
8. Wait 1-2 minutes for build to complete
9. 🎉 **Your site is live!** You'll get a URL like `vcp-scanner.vercel.app`

---

## STEP 5: Run the Python Scanner (for real data)

This runs on YOUR computer to generate fresh Nifty 500 scan data.

### One-time setup:
```bash
pip install yfinance niftystocks pandas numpy
```

### Run the scanner:
```bash
python vcp_scanner.py
```
- Takes 15-30 minutes for full Nifty 500 scan
- Creates `vcp_scan_results.json` in the same folder

### Load data into the website:
1. Open your deployed website
2. Click the **IMPORT** tab
3. Open `vcp_scan_results.json` in Notepad/TextEdit
4. Copy ALL contents (Ctrl+A then Ctrl+C)
5. Paste into the text box on the website
6. Click **Load Data**

---

## STEP 6: (Optional) Auto-run Scanner Daily

### On Windows (Task Scheduler):
1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Basic Task**
3. Name: "VCP Scanner"
4. Trigger: Daily, set time (e.g., 7:00 PM after market close)
5. Action: Start a Program
6. Program: `python`
7. Arguments: `C:\path\to\vcp_scanner.py`
8. Finish

### On Mac/Linux (Cron):
```bash
crontab -e
```
Add this line (runs at 7 PM daily):
```
0 19 * * 1-5 /usr/bin/python3 /path/to/vcp_scanner.py
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `npm not found` | Install Node.js from nodejs.org |
| `git not found` | Install Git from git-scm.com |
| Vercel build fails | Check that `package.json` is in the root folder, not inside a subfolder |
| Python scanner errors | Run `pip install --upgrade yfinance` |
| No signals found | Normal — VCP breakouts are rare. Try a broader date range |
| Scanner is slow | It downloads data for 500 stocks. 15-30 min is normal |

---

## Project Structure
```
vcp-scanner-app/
├── index.html          ← HTML entry point
├── package.json        ← Dependencies
├── vite.config.js      ← Build config
├── .gitignore          ← Files to ignore in git
├── vcp_scanner.py      ← Python scanner (run locally)
├── public/             ← Static assets
└── src/
    ├── main.jsx        ← React entry
    └── App.jsx         ← Main dashboard app
```
