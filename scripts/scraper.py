"""
scraper.py
Runs on GitHub Actions every night at 6:30 PM UTC = 12:00 AM IST.
Scrapes Google Maps for all 36 branches.
Saves results to data/reviews.json which gets committed back to the repo.
"""
import re, time, json, os
from datetime import date, datetime, timedelta
from playwright.sync_api import sync_playwright

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "reviews.json")

BRANCHES = [
    # ── Siva (6 branches) ──────────────────────────────────────────
    {"id":1,  "name":"Tuticorin-1",     "place_id":"ChIJ5zJNoJfvAzsR-bJE_3bbNYw",  "agm":"Siva"},
    {"id":2,  "name":"Tuticorin-2",     "place_id":"ChIJH6gY4-PvAzsRJ50skTlx3cs",  "agm":"Siva"},
    {"id":3,  "name":"Thiruchendur-1",  "place_id":"ChIJeXA4vJKRAzsRBovAtv6lMuQ",  "agm":"Siva"},
    {"id":4,  "name":"Thisayanvilai-1", "place_id":"ChIJVWkvdfh_BDsRdvtimKCLS5Y",  "agm":"Siva"},
    {"id":5,  "name":"Eral-2",          "place_id":"ChIJbwAA0KGMAzsRkQilW5PceeA",   "agm":"Siva"},
    {"id":6,  "name":"Udankudi",        "place_id":"ChIJPQAAACyEAzsRgjznQ1GLom0",   "agm":"Siva"},
    # ── John (4 branches) ──────────────────────────────────────────
    {"id":7,  "name":"Tirunelveli-1",   "place_id":"ChIJ2RU2NvQRBDsRq-Fw7IVwx7k",  "agm":"John"},
    {"id":8,  "name":"Valliyur-1",      "place_id":"ChIJcVNk6TtnBDsRBoP4zpExt5k",  "agm":"John"},
    {"id":9,  "name":"Ambasamudram-1",  "place_id":"ChIJ9SGeIi85BDsRZk4QdyW9BSY",  "agm":"John"},
    {"id":10, "name":"Anjugramam-1",    "place_id":"ChIJ4yeJebLtBDsRDceoxujdGyc",  "agm":"John"},
    # ── Jeeva (7 branches) ─────────────────────────────────────────
    {"id":11, "name":"Nagercoil",       "place_id":"ChIJe1LZBiTxBDsRJFLjlbgZoIs",  "agm":"Jeeva"},
    {"id":12, "name":"Marthandam",      "place_id":"ChIJcWptCRdVBDsRlJh2q0-rnfY",  "agm":"Jeeva"},
    {"id":13, "name":"Thuckalay-1",     "place_id":"ChIJc9QgEub4BDsRoyDR4Wd6tYA",  "agm":"Jeeva"},
    {"id":14, "name":"Colachel-1",      "place_id":"ChIJgRkBLw39BDsR58D0lwNo5Ts",  "agm":"Jeeva"},
    {"id":15, "name":"Kulasekharam-1",  "place_id":"ChIJw0Ep-kNXBDsRe5ad32jAeAk",  "agm":"Jeeva"},
    {"id":16, "name":"Monday Market",   "place_id":"ChIJTceRGAD5BDsR65i3YNTcYHk",  "agm":"Jeeva"},
    {"id":17, "name":"Karungal-1",      "place_id":"ChIJfTP5ASr_BDsRgsBaeQltkw4",  "agm":"Jeeva"},
    # ── Seenivasan (8 branches) ────────────────────────────────────
    {"id":18, "name":"Kovilpatti",      "place_id":"ChIJHY0o-26yBjsRt7wbXB1pDUE",  "agm":"Seenivasan"},
    {"id":19, "name":"Ramnad",          "place_id":"ChIJNVVVVaGiATsRnunSgOTvbE8",  "agm":"Seenivasan"},
    {"id":20, "name":"Paramakudi",      "place_id":"ChIJ-dgjBzQHATsRf27FWAJgmsA",  "agm":"Seenivasan"},
    {"id":21, "name":"Sayalkudi-1",     "place_id":"ChIJRTqudn9lATsR2fYyMmxlOrw",  "agm":"Seenivasan"},
    {"id":22, "name":"Villathikullam",  "place_id":"ChIJi_wAkwVbATsRtFl3_V5rGrY",  "agm":"Seenivasan"},
    {"id":23, "name":"Sattur-2",        "place_id":"ChIJNVVVVcHKBjsR7xMX97RFn8Q",  "agm":"Seenivasan"},
    {"id":24, "name":"Sankarankovil-1", "place_id":"ChIJE1mKnhSXBjsRKMQ-9JKQf_c", "agm":"Seenivasan"},
    {"id":25, "name":"Kayathar-1",      "place_id":"ChIJx5ebtUgRBDsRMquPZNUJVpw",  "agm":"Seenivasan"},
    # ── Muthuselvam (6 branches) ───────────────────────────────────
    {"id":26, "name":"Thenkasi",        "place_id":"ChIJuaqqquEpBDsRVITw0MMYklc",  "agm":"Muthuselvam"},
    {"id":27, "name":"Thenkasi-2",      "place_id":"ChIJiwqLye6DBjsRo9v1mWXaycI",  "agm":"Muthuselvam"},
    {"id":28, "name":"Surandai-1",      "place_id":"ChIJPb1_eEOdBjsRjL9IVCVJhi8",  "agm":"Muthuselvam"},
    {"id":29, "name":"Puliyankudi-1",   "place_id":"ChIJjZqoc46RBjsRQTGHnNC8xxA",  "agm":"Muthuselvam"},
    {"id":30, "name":"Sengottai-1",     "place_id":"ChIJw3zzKiaBBjsR9KDyGpn1nXU",  "agm":"Muthuselvam"},
    {"id":31, "name":"Rajapalayam",     "place_id":"ChIJW2ot-NDpBjsRMTfMF2IV-xE",  "agm":"Muthuselvam"},
    # ── Venkatesh (5 branches) ─────────────────────────────────────
    {"id":32, "name":"Virudhunagar",    "place_id":"ChIJN3jzNJgsATsRCU3nrB5ntKE",  "agm":"Venkatesh"},
    {"id":33, "name":"Virudhunagar-2",  "place_id":"ChIJPezaX7wtATsR9sHhFOG6A1c",  "agm":"Venkatesh"},
    {"id":34, "name":"Aruppukottai",    "place_id":"ChIJy6qqqgYwATsRbcp-hXnoruM",   "agm":"Venkatesh"},
    {"id":35, "name":"Aruppukottai-2",  "place_id":"ChIJY04wY58xATsRuoJSichVQQE",  "agm":"Venkatesh"},
    {"id":36, "name":"Sivakasi",        "place_id":"ChIJI2JvEePOBjsREh8b-x4WF4U",  "agm":"Venkatesh"},
]


BACKUP_DIR = os.path.join(os.path.dirname(DATA_FILE), "backups")


def load_data():
    """
    Load existing data. If reviews.json is empty/missing/corrupted,
    try to restore from the most recent backup automatically.
    Never returns an empty branches dict if backups exist.
    """
    # Try main file first
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # If branches exist and have real data, use it
            if data.get("branches"):
                print(f"  [Data] Loaded {len(data['branches'])} branches from reviews.json")
                return data
            else:
                print("  [Data] reviews.json is empty — checking backups...")
        except Exception as e:
            print(f"  [Data] reviews.json corrupted ({e}) — checking backups...")

    # Try to restore from most recent backup
    if os.path.exists(BACKUP_DIR):
        backups = sorted([
            f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")
        ], reverse=True)  # most recent first

        for backup_file in backups:
            backup_path = os.path.join(BACKUP_DIR, backup_file)
            try:
                with open(backup_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("branches"):
                    print(f"  [Data] RESTORED from backup: {backup_file}")
                    print(f"  [Data] Restored {len(data['branches'])} branches, {len(data.get('daily',{}))} days of history")
                    return data
            except Exception:
                continue

    print("  [Data] No data or backups found — starting fresh.")
    return {"branches": {}, "daily": {}, "logs": []}


def save_data(data):
    """
    Save data to reviews.json AND create a dated backup.
    Backups are kept for 90 days then auto-cleaned.
    """
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    # 1. Save main file
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 2. Save dated backup
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today_str   = datetime.utcnow().strftime("%Y-%m-%d")
    backup_path = os.path.join(BACKUP_DIR, f"reviews_{today_str}.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  [Data] Backup saved: backups/reviews_{today_str}.json")

    # 3. Clean backups older than 90 days
    cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0)
    cleaned = 0
    for fname in os.listdir(BACKUP_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(BACKUP_DIR, fname)
        age_days = (datetime.utcnow() - datetime.fromtimestamp(os.path.getmtime(fpath))).days
        if age_days > 90:
            os.remove(fpath)
            cleaned += 1
    if cleaned:
        print(f"  [Data] Cleaned {cleaned} old backups (>90 days)")


def _try_scrape(page, place_id, wait_ms=3000):
    """Single scrape attempt. Returns (count, stars) — either may be None."""
    url   = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    count = None
    stars = None

    page.goto(url, wait_until="domcontentloaded", timeout=35000)
    page.wait_for_timeout(wait_ms)

    # ── Review count via aria-label ──────────────────────────
    for sel in ['[aria-label*="reviews"]', '[aria-label*="Reviews"]',
                'button[jsaction*="review"]']:
        for el in page.locator(sel).all():
            label = el.get_attribute("aria-label") or ""
            m = re.search(r"([\d,]+)", label)
            if m:
                count = int(m.group(1).replace(",", ""))
                break
        if count:
            break

    # ── Star rating via aria-label ───────────────────────────
    for sel in ['[aria-label*="stars"]', 'span[aria-label*="stars"]',
                '[aria-label*="star rating"]']:
        for el in page.locator(sel).all():
            label = el.get_attribute("aria-label") or ""
            m = re.search(r"(\d\.\d)", label)
            if m:
                stars = float(m.group(1))
                break
        if stars:
            break

    content = page.content()

    # ── Fallback: count from page source ─────────────────────
    if not count:
        for pat in [r'([\d,]+)\s*reviews?',
                    r'"reviewCount"["\s:]+(\d+)',
                    r'(\d[\d,]{2,})\s*Google review']:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                v = int(m.group(1).replace(",", ""))
                if v > 10:
                    count = v
                    break

    # ── Fallback: stars from page source ─────────────────────
    if not stars:
        for pat in [r'"ratingValue":"([\d.]+)"',
                    r'(\d\.\d)\s*(?:stars|out of 5)',
                    r'"aggregateRating".*?"ratingValue":\s*"?([\d.]+)']:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                try:
                    v = float(m.group(1))
                    if 1.0 <= v <= 5.0:
                        stars = v
                        break
                except ValueError:
                    pass

    return count, stars


def scrape_place(page, place_id, name, max_retries=3):
    """
    Scrape with automatic retry on failure.
    Attempt 1: normal (3s wait)
    Attempt 2: longer wait (5s) after 3s pause
    Attempt 3: extra long wait (8s) after 5s pause — fresh page reload
    Returns (count, stars) — either may be None if all retries fail.
    """
    wait_times  = [3000, 5000, 8000]
    pause_times = [0,    3,    5]    # seconds to sleep before each retry

    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"    ↺ Retry {attempt}/{max_retries} for {name} "
                      f"(waiting {pause_times[attempt-1]}s)...", flush=True)
                time.sleep(pause_times[attempt - 1])
                # Navigate away first to force a clean reload
                page.goto("about:blank", timeout=5000)
                time.sleep(1)

            count, stars = _try_scrape(page, place_id, wait_ms=wait_times[attempt - 1])

            if count is not None:
                return count, stars
            # count is None — will retry
            print(f"    ⚠ Attempt {attempt}: no count found", flush=True)

        except Exception as e:
            print(f"    ⚠ Attempt {attempt} error: {e}", flush=True)
            if attempt == max_retries:
                break

    return None, None


def run():
    """
    DATE LOGIC — critical to understand:
    ──────────────────────────────────────────────────────────────
    Workflow runs at 6:30 PM UTC = 12:00 AM IST (next day).

    When GitHub Actions runs on 2026-02-28 at 6:30 PM UTC:
      - UTC date  = 2026-02-28
      - IST date  = 2026-03-01 (already next day in IST)

    We want to capture reviews for the day just ended in IST.
    So snap_date  = UTC date       = 2026-02-28
       baseline   = UTC date - 1  = 2026-02-27 total_snap

    daily_count(28-Feb) = live_total_scraped_now - total_snap(27-Feb)
    monthly(28-Feb)     = monthly(27-Feb) + daily_count(28-Feb)
    """
    # DATE LOGIC (IST-aware):
    # Workflow scheduled at 6:30 PM UTC = 12:00 AM IST next day.
    # Manual runs can happen at any IST time.
    # snap_date = yesterday IST  → the full day we are recording
    # baseline  = most recent daily entry before snap_date (walks back if a
    #             day was missed due to workflow failure)
    IST_OFFSET    = timedelta(hours=5, minutes=30)
    now_ist       = datetime.utcnow() + IST_OFFSET
    snap_date     = (now_ist.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    run_time      = datetime.utcnow().isoformat()

    print(f"=== Sathya Review Scraper ===")
    print(f"Snap date      : {snap_date}  (recording reviews for this date)")
    print(f"Run time (IST) : {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"Run time (UTC) : {run_time} UTC")
    print()

    data = load_data()

    # ── Find the most recent date with data before snap_date ──────────
    # Normally yesterday. But if a workflow run was missed
    # (workflow failed on 02-Mar), a manual run on 04-Mar for
    # snap_date=03-Mar should walk back to 01-Mar, not use empty 02-Mar.
    all_dates_before = sorted(
        [d for d in data.get("daily", {}) if d < snap_date],
        reverse=True
    )
    baseline_date = all_dates_before[0] if all_dates_before else None

    print(f"Baseline date  : {baseline_date or 'none (first run)'}  (most recent data before snap_date)")

    # ── Freeze baseline totals BEFORE scraping ────────────────
    baseline_snap = data["daily"].get(baseline_date, {}) if baseline_date else {}
    baseline = {}
    for b in BRANCHES:
        bid = str(b["id"])
        if baseline_snap.get(bid, {}).get("total_snap", 0) > 0:
            baseline[bid] = baseline_snap[bid]["total_snap"]
        else:
            baseline[bid] = data.get("branches", {}).get(bid, {}).get("overall", 0)

    success = 0
    failed  = []
    results = {}   # collect ALL scraped values before writing anything

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled", "--disable-gpu"]
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-IN", viewport={"width":1280,"height":800}
        )
        page = ctx.new_page()

        # ── WARM-UP ───────────────────────────────────────────
        # Dummy load to fully initialise the browser before real scraping.
        # Result discarded. Prevents Tuticorin-1 (first branch) from always
        # failing due to cold browser.
        print("  [warm-up] Initialising browser...", end=" ", flush=True)
        try:
            page.goto("https://www.google.com/maps", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            print("ready ✓")
        except Exception:
            print("skipped (timeout — continuing anyway)")
        time.sleep(1)

        # ── SCRAPE ALL BRANCHES ───────────────────────────────
        for b in BRANCHES:
            bid  = str(b["id"])
            name = b["name"]
            print(f"  [{b['id']:02d}/36] {name:<25}", end=" ", flush=True)

            live, stars = scrape_place(page, b["place_id"], name)

            if live is not None:
                prev  = baseline.get(bid, 0)
                daily = max(0, live - prev)
                results[bid] = {"live": live, "stars": stars, "daily_count": daily}
                stars_str = f"{stars}★" if stars else "—"
                print(f"→ {live:,} total  +{daily} new  {stars_str}  ✓")
                success += 1
            else:
                failed.append(name)
                print("→ FAILED ✗")

            time.sleep(1.5)

        browser.close()

    # ── WRITE ALL RESULTS (after all scraping is done) ─────────────
    # Each date's snapshot is PERMANENT once written:
    #   total_snap  = live overall reviews as of this date
    #   daily_count = reviews received ON this date (total_snap - baseline)
    #   monthly     = previous date monthly + daily_count  (cumulative)
    #   star_rating = live star rating as of this date
    #
    # Past snapshots are NEVER modified by future runs.

    if snap_date not in data["daily"]:
        data["daily"][snap_date] = {}

    # ── Find the most recent same-month date for monthly chaining ──
    # If baseline_date is in a previous month (month boundary) or missing,
    # we need the most recent entry in snap_date's month for monthly.
    # If no entry exists yet in this month, prev_monthly = 0 (fresh month start).
    snap_month = snap_date[:7]
    same_month_dates = sorted(
        [d for d in data.get("daily", {}) if d.startswith(snap_month) and d < snap_date],
        reverse=True
    )
    monthly_baseline_date = same_month_dates[0] if same_month_dates else None
    baseline_daily_snap   = data["daily"].get(baseline_date, {}) if baseline_date else {}
    monthly_daily_snap    = data["daily"].get(monthly_baseline_date, {}) if monthly_baseline_date else {}

    for b in BRANCHES:
        bid = str(b["id"])
        if bid not in results:
            continue   # scrape failed — do not touch existing data for this branch

        r           = results[bid]
        live        = r["live"]
        stars       = r["stars"]
        daily       = r["daily_count"]
        old_stars   = data["branches"].get(bid, {}).get("star_rating", 0)
        final_stars = stars if stars else old_stars

        # monthly = most recent same-month entry's monthly + today's daily_count
        # If no same-month entry exists yet → fresh month, start from 0
        prev_monthly = monthly_daily_snap.get(bid, {}).get("monthly", 0)
        monthly      = prev_monthly + daily

        # Write permanent snapshot for snap_date
        data["daily"][snap_date][bid] = {
            "total_snap":  live,
            "daily_count": daily,
            "monthly":     monthly,
            "star_rating": final_stars,
        }

        # Update branches{} — just latest values for quick dashboard access
        data["branches"][bid] = {
            "id":          b["id"],
            "name":        b["name"],
            "agm":         b["agm"],
            "overall":     live,
            "star_rating": final_stars,
            "monthly":     monthly,
        }

    data.setdefault("logs", []).insert(0, {
        "ran_at":        run_time,
        "snap_date":     snap_date,
        "baseline_date": baseline_date,
        "success":       success,
        "failed":        len(failed),
        "failed_names":  failed,
    })
    data["logs"]         = data["logs"][:50]
    data["last_updated"] = run_time

    save_data(data)
    print(f"\nDone: {success}/36 saved for {snap_date}")

if __name__ == "__main__":
    import sys
    import traceback
    try:
        run()
    except Exception as e:
        print(f"\n[FATAL] Scraper crashed: {e}")
        traceback.print_exc()
        # Exit 0 so workflow doesn't mark as failure —
        # the commit step will still run and save whatever data exists.
        sys.exit(0)
