# VCP Scanner — Deploy in 5 Steps

You need: GitHub account (free) + Vercel account (free). That's it.

---

## Step 1: Create GitHub Repo

1. Go to github.com → click **+** → **New repository**
2. Name: `vcp-scanner`, keep Public, click **Create**
3. On next page click **"uploading an existing file"**
4. Drag-drop ALL files from the unzipped folder (including `.github` folder)
5. Click **Commit changes**

**Important**: Files must be at root level. Your repo should show `package.json`, `scanner.py`, `index.html` etc. directly — NOT inside a subfolder.

---

## Step 2: Deploy on Vercel

1. Go to vercel.com → Sign up with GitHub
2. Click **Add New → Project**
3. Import `vcp-scanner` repo
4. Framework: should auto-detect **Vite**
5. Click **Deploy** → wait 2 min → your site is live!

---

## Step 3: Enable Auto-Scanner

The GitHub Action needs permission to push commits:

1. In your GitHub repo → **Settings** tab (top)
2. Left sidebar → **Actions** → **General**
3. Scroll to **Workflow permissions**
4. Select **"Read and write permissions"**
5. Click **Save**

---

## Step 4: Run First Scan

1. In your GitHub repo → **Actions** tab (top)
2. Click **"Daily VCP Scan"** on the left
3. Click **"Run workflow"** button (right side) → **Run workflow**
4. Wait 15-30 minutes for it to complete
5. Once done, check `public/data.json` — it should have real data
6. Vercel auto-deploys within 1 min → your site shows real data!

---

## Step 5: Done!

- Scanner runs automatically Mon-Fri at 4:30 PM IST
- Results appear on your website within minutes
- No manual work needed after this

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Action fails with permission error | Step 3 — enable "Read and write permissions" |
| Site shows "No data.json found" | Run the Action manually (Step 4) |
| Vercel 404 error | In Vercel Settings → make sure Root Directory is empty (not a subfolder) |
| Scanner finds 0 signals | Normal — VCP breakouts are rare on some days |
| Action not visible | Make sure `.github/workflows/scan.yml` was uploaded |
