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
    LOGIC — how dates work:
    ─────────────────────────────────────────────────────────────
    Scraper runs at 12:00 AM midnight on DATE X.

    At that moment, Google shows the LIVE total which includes
    everything up to 11:59 PM of DATE X-1.

    So:
      snap_date    = yesterday  (X-1)  → the day we are accounting for
      baseline     = day before yesterday (X-2) total_snap
      daily_count  = live_total_now  -  baseline_total
                   = all reviews received during snap_date (12AM-11:59PM)
      monthly      = sum of all daily_counts in same month up to snap_date

    Example running at midnight on 28-Feb-2026:
      snap_date = 27-Feb-2026
      baseline  = 26-Feb-2026 total_snap
      daily     = reviews received on 27-Feb (12AM to 11:59PM)
    """
    snap_date      = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    baseline_date  = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    run_time       = datetime.utcnow().isoformat()

    print(f"=== Sathya Review Scraper ===")
    print(f"Accounting for : {snap_date}  (12:00 AM to 11:59 PM)")
    print(f"Baseline from  : {baseline_date}  (end-of-day total)")
    print(f"Run time       : {run_time} UTC")
    print()

    data = load_data()

    # ── Freeze baseline BEFORE scraping ───────────────────────
    # Use baseline_date total_snap as the subtraction point.
    # Frozen upfront so mid-loop updates don't corrupt each other.
    baseline_snap = data.get("daily", {}).get(baseline_date, {})
    baseline = {}
    for bid, b in data["branches"].items():
        if baseline_snap.get(bid, {}).get("total_snap", 0) > 0:
            baseline[bid] = baseline_snap[bid]["total_snap"]
        else:
            # First ever run — no baseline_date snap yet
            baseline[bid] = b.get("overall", 0)

    success = 0
    failed  = []
    results = {}   # collect ALL results before writing anything

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled", "--disable-gpu"]
        )
        ctx  = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-IN", viewport={"width":1280,"height":800}
        )
        page = ctx.new_page()

        # ── WARM-UP: dummy scrape to initialise the browser ───────
        # The very first Google Maps request always fails or times out
        # because the browser (cookies, JS engine, network) isn't
        # ready yet. We scrape a well-known public Google Maps page,
        # throw the result away, then start the real scraping.
        # This means Tuticorin-1 (branch 1) gets a fair first attempt.
        print("  [warm-up] Initialising browser...", end=" ", flush=True)
        try:
            page.goto("https://www.google.com/maps", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            print("ready ✓")
        except Exception:
            print("skipped (timeout — continuing anyway)")
        time.sleep(1)

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

    # ── Write ALL results after scraping is fully done ─────────
    if snap_date not in data["daily"]:
        data["daily"][snap_date] = {}

    for b in BRANCHES:
        bid = str(b["id"])
        if bid not in results:
            continue   # failed — leave existing data unchanged

        r     = results[bid]
        live  = r["live"]
        stars = r["stars"]
        daily = r["daily_count"]
        old_stars = data["branches"].get(bid, {}).get("star_rating", 0)

        # Update branch master record
        data["branches"][bid] = {
            "id":          b["id"],
            "name":        b["name"],
            "agm":         b["agm"],
            "overall":     live,
            "star_rating": stars if stars else old_stars,
        }

        # Write snap_date daily entry
        data["daily"][snap_date][bid] = {
            "daily_count": daily,
            "total_snap":  live,
            "star_rating": stars if stars else old_stars,
        }

    # ── Monthly = sum of daily_counts in same month ≤ snap_date ──
    year_month = snap_date[:7]
    for b in BRANCHES:
        bid = str(b["id"])
        if bid not in data["branches"]:
            continue
        data["branches"][bid]["monthly"] = sum(
            data["daily"].get(d, {}).get(bid, {}).get("daily_count", 0)
            for d in data["daily"]
            if d.startswith(year_month) and d <= snap_date
        )

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
    run()
