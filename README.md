# Sathya Agencies — Google Review Tracker
**100% Free · No server · No credit card · Runs on GitHub**

---

## How It Works

```
Every night 12:00 AM IST
        ↓
GitHub Actions wakes up
        ↓
Scrapes Google Maps for all 36 branches (headless Chrome)
        ↓
Saves data to data/reviews.json
        ↓
Commits it back to this repo
        ↓
Your GitHub Pages website shows updated data
```

---

## Setup (One Time — 10 minutes)

### Step 1 — Create GitHub Account
Go to https://github.com and sign up (free).

### Step 2 — Create a New Repository
1. Click the **+** button → **New repository**
2. Name it: `sathya-review-tracker`
3. Set it to **Public** (required for free GitHub Pages)
4. Click **Create repository**

### Step 3 — Upload These Files
Upload all files from this ZIP keeping the same folder structure:
```
.github/
  workflows/
    scrape.yml       ← the automation schedule
scripts/
  scraper.py         ← the Google Maps scraper
docs/
  index.html         ← your live dashboard website
data/
  reviews.json       ← data file (auto-updated nightly)
README.md
```

To upload: In your repo click **Add file → Upload files** and drag everything in.

### Step 4 — Enable GitHub Pages
1. Go to your repo **Settings**
2. Click **Pages** in the left sidebar
3. Under **Source** select: **Deploy from a branch**
4. Branch: **main** | Folder: **/docs**
5. Click **Save**

After ~2 minutes your dashboard will be live at:
```
https://YOUR-USERNAME.github.io/sathya-review-tracker/
```

### Step 5 — Give Actions Permission to Write
1. Go to repo **Settings → Actions → General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Click **Save**

---

## That's It!

- Dashboard URL: `https://YOUR-USERNAME.github.io/sathya-review-tracker/`
- Data updates: Every night at **12:00 AM IST** automatically
- You can also trigger it manually: Go to **Actions tab → Nightly Review Scraper → Run workflow**

---

## Dashboard Features
- Live KPI cards (total reviews, daily, monthly, avg star rating)
- Branch-wise table with sorting and search
- View by AGM (who manages which branches)
- Date picker to see any past day's data
- Full history view
- Scrape logs (see when it ran, what succeeded/failed)
- Export to Excel/CSV with one click

---

## FAQ

**Q: Is this really free?**
Yes. GitHub Actions gives 2,000 free minutes/month. Your scraper takes ~10 minutes per run × 30 days = 300 minutes. Well within the free limit.

**Q: What if a branch fails to scrape?**
It retries next night. Failed branches show in the Scrape Logs view.

**Q: Can I trigger it manually?**
Yes. Go to **Actions tab → Nightly Review Scraper → Run workflow → Run workflow**.

**Q: How do I add more branches?**
Edit `scripts/scraper.py` and add to the `BRANCHES` list with the Google Maps Place ID.

**Q: What is a Place ID?**
It's Google's unique ID for each business location. Find it at:
https://developers.google.com/maps/documentation/places/web-service/place-id
(search your branch name, copy the Place ID)
