"""
Sathya Review Scraper - Fast Async Parallel Version
Scrapes 36 branches in ~30 seconds using controlled concurrency.
"""

import re
import json
import os
import asyncio
import traceback
import sys
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "reviews.json")
BACKUP_DIR = os.path.join(os.path.dirname(DATA_FILE), "backups")

# Optimal concurrency for GitHub Actions (fast + stable)
MAX_CONCURRENT = 8

BRANCHES = [
    # ── Siva (6 branches) ──────────────────────────────────────────
    {"id":1, "name":"Tuticorin-1", "place_id":"ChIJ5zJNoJfvAzsR-bJE_3bbNYw", "agm":"Siva"},
    {"id":2, "name":"Tuticorin-2", "place_id":"ChIJH6gY4-PvAzsRJ50skTlx3cs", "agm":"Siva"},
    {"id":3, "name":"Thiruchendur-1", "place_id":"ChIJeXA4vJKRAzsRBovAtv6lMuQ", "agm":"Siva"},
    {"id":4, "name":"Thisayanvilai-1", "place_id":"ChIJVWkvdfh_BDsRdvtimKCLS5Y", "agm":"Siva"},
    {"id":5, "name":"Eral-2", "place_id":"ChIJbwAA0KGMAzsRkQilW5PceeA", "agm":"Siva"},
    {"id":6, "name":"Udankudi", "place_id":"ChIJPQAAACyEAzsRgjznQ1GLom0", "agm":"Siva"},
    # ── John (4 branches) ──────────────────────────────────────────
    {"id":7, "name":"Tirunelveli-1", "place_id":"ChIJ2RU2NvQRBDsRq-Fw7IVwx7k", "agm":"John"},
    {"id":8, "name":"Valliyur-1", "place_id":"ChIJcVNk6TtnBDsRBoP4zpExt5k", "agm":"John"},
    {"id":9, "name":"Ambasamudram-1", "place_id":"ChIJ9SGeIi85BDsRZk4QdyW9BSY", "agm":"John"},
    {"id":10, "name":"Anjugramam-1", "place_id":"ChIJ4yeJebLtBDsRDceoxujdGyc", "agm":"John"},
    # ── Jeeva (7 branches) ─────────────────────────────────────────
    {"id":11, "name":"Nagercoil", "place_id":"ChIJe1LZBiTxBDsRJFLjlbgZoIs", "agm":"Jeeva"},
    {"id":12, "name":"Marthandam", "place_id":"ChIJcWptCRdVBDsRlJh2q0-rnfY", "agm":"Jeeva"},
    {"id":13, "name":"Thuckalay-1", "place_id":"ChIJc9QgEub4BDsRoyDR4Wd6tYA", "agm":"Jeeva"},
    {"id":14, "name":"Colachel-1", "place_id":"ChIJgRkBLw39BDsR58D0lwNo5Ts", "agm":"Jeeva"},
    {"id":15, "name":"Kulasekharam-1", "place_id":"ChIJw0Ep-kNXBDsRe5ad32jAeAk", "agm":"Jeeva"},
    {"id":16, "name":"Monday Market", "place_id":"ChIJTceRGAD5BDsR65i3YNTcYHk", "agm":"Jeeva"},
    {"id":17, "name":"Karungal-1", "place_id":"ChIJfTP5ASr_BDsRgsBaeQltkw4", "agm":"Jeeva"},
    # ── Seenivasan (8 branches) ────────────────────────────────────
    {"id":18, "name":"Kovilpatti", "place_id":"ChIJHY0o-26yBjsRt7wbXB1pDUE", "agm":"Seenivasan"},
    {"id":19, "name":"Ramnad", "place_id":"ChIJNVVVVaGiATsRnunSgOTvbE8", "agm":"Seenivasan"},
    {"id":20, "name":"Paramakudi", "place_id":"ChIJ-dgjBzQHATsRf27FWAJgmsA", "agm":"Seenivasan"},
    {"id":21, "name":"Sayalkudi-1", "place_id":"ChIJRTqudn9lATsR2fYyMmxlOrw", "agm":"Seenivasan"},
    {"id":22, "name":"Villathikullam", "place_id":"ChIJi_wAkwVbATsRtFl3_V5rGrY", "agm":"Seenivasan"},
    {"id":23, "name":"Sattur-2", "place_id":"ChIJNVVVVcHKBjsR7xMX97RFn8Q", "agm":"Seenivasan"},
    {"id":24, "name":"Sankarankovil-1", "place_id":"ChIJE1mKnhSXBjsRKMQ-9JKQf_c", "agm":"Seenivasan"},
    {"id":25, "name":"Kayathar-1", "place_id":"ChIJx5ebtUgRBDsRMquPZNUJVpw", "agm":"Seenivasan"},
    # ── Muthuselvam (6 branches) ───────────────────────────────────
    {"id":26, "name":"Thenkasi", "place_id":"ChIJuaqqquEpBDsRVITw0MMYklc", "agm":"Muthuselvam"},
    {"id":27, "name":"Thenkasi-2", "place_id":"ChIJiwqLye6DBjsRo9v1mWXaycI", "agm":"Muthuselvam"},
    {"id":28, "name":"Surandai-1", "place_id":"ChIJPb1_eEOdBjsRjL9IVCVJhi8", "agm":"Muthuselvam"},
    {"id":29, "name":"Puliyankudi-1", "place_id":"ChIJjZqoc46RBjsRQTGHnNC8xxA", "agm":"Muthuselvam"},
    {"id":30, "name":"Sengottai-1", "place_id":"ChIJw3zzKiaBBjsR9KDyGpn1nXU", "agm":"Muthuselvam"},
    {"id":31, "name":"Rajapalayam", "place_id":"ChIJW2ot-NDpBjsRMTfMF2IV-xE", "agm":"Muthuselvam"},
    # ── Venkatesh (5 branches) ─────────────────────────────────────
    {"id":32, "name":"Virudhunagar", "place_id":"ChIJN3jzNJgsATsRCU3nrB5ntKE", "agm":"Venkatesh"},
    {"id":33, "name":"Virudhunagar-2", "place_id":"ChIJPezaX7wtATsR9sHhFOG6A1c", "agm":"Venkatesh"},
    {"id":34, "name":"Aruppukottai", "place_id":"ChIJy6qqqgYwATsRbcp-hXnoruM", "agm":"Venkatesh"},
    {"id":35, "name":"Aruppukottai-2", "place_id":"ChIJY04wY58xATsRuoJSichVQQE", "agm":"Venkatesh"},
    {"id":36, "name":"Sivakasi", "place_id":"ChIJI2JvEePOBjsREh8b-x4WF4U", "agm":"Venkatesh"},
]

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("branches"):
                print(f" [Data] Loaded {len(data['branches'])} branches from reviews.json")
                return data
        except Exception as e:
            print(f" [Data] reviews.json corrupted ({e}) — checking backups...")

    if os.path.exists(BACKUP_DIR):
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")], reverse=True)
        for backup_file in backups:
            backup_path = os.path.join(BACKUP_DIR, backup_file)
            try:
                with open(backup_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("branches"):
                    print(f" [Data] RESTORED from backup: {backup_file}")
                    return data
            except Exception:
                continue

    print(" [Data] No valid data found — starting fresh.")
    return {"branches": {}, "daily": {}, "logs": []}


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    backup_path = os.path.join(BACKUP_DIR, f"reviews_{today_str}.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f" [Data] Backup saved: backups/reviews_{today_str}.json")

    # Clean old backups (>90 days)
    cutoff = datetime.utcnow()
    cleaned = 0
    for fname in os.listdir(BACKUP_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(BACKUP_DIR, fname)
        age_days = (cutoff - datetime.fromtimestamp(os.path.getmtime(fpath))).days
        if age_days > 90:
            os.remove(fpath)
            cleaned += 1
    if cleaned:
        print(f" [Data] Cleaned {cleaned} old backups")


async def _try_scrape(page, place_id, wait_ms=3000):
    url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    count = None
    stars = None

    await page.goto(url, wait_until="domcontentloaded", timeout=35000)
    await page.wait_for_timeout(wait_ms)

    content = await page.content()

    # Review count via aria-label
    for sel in ['[aria-label*="reviews"]', '[aria-label*="Reviews"]', 'button[jsaction*="review"]']:
        els = await page.locator(sel).all()
        for el in els:
            label = await el.get_attribute("aria-label") or ""
            m = re.search(r"([\d,]+)", label)
            if m:
                count = int(m.group(1).replace(",", ""))
                break
        if count:
            break

    # Star rating via aria-label
    for sel in ['[aria-label*="stars"]', 'span[aria-label*="stars"]', '[aria-label*="star rating"]']:
        els = await page.locator(sel).all()
        for el in els:
            label = await el.get_attribute("aria-label") or ""
            m = re.search(r"(\d\.\d)", label)
            if m:
                stars = float(m.group(1))
                break
        if stars:
            break

    # Fallback for count
    if not count:
        for pat in [r'([\d,]+)\s*reviews?', r'"reviewCount"["\s:]+(\d+)', r'(\d[\d,]{2,})\s*Google review']:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                v = int(m.group(1).replace(",", ""))
                if v > 10:
                    count = v
                    break

    # Fallback for stars
    if not stars:
        for pat in [r'"ratingValue":"([\d.]+)"', r'(\d\.\d)\s*(?:stars|out of 5)', r'"aggregateRating".*?"ratingValue":\s*"?([\d.]+)']:
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


async def scrape_place(context, place_id, name, max_retries=3):
    wait_times = [3000, 5000, 8000]
    pause_times = [0, 3, 5]

    for attempt in range(1, max_retries + 1):
        page = None
        try:
            if attempt > 1:
                print(f" ↺ Retry {attempt} for {name}...", flush=True)
                await asyncio.sleep(pause_times[attempt - 1])

            page = await context.new_page()
            count, stars = await _try_scrape(page, place_id, wait_ms=wait_times[attempt - 1])

            if count is not None:
                await page.close()
                return count, stars

            print(f" ⚠ Attempt {attempt}: no count for {name}", flush=True)
        except Exception as e:
            print(f" ⚠ Attempt {attempt} error for {name}: {e}", flush=True)
        finally:
            if page:
                await page.close()

    return None, None


async def run():
    IST_OFFSET = timedelta(hours=5, minutes=30)
    now_ist = datetime.utcnow() + IST_OFFSET
    snap_date = (now_ist.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    run_time = datetime.utcnow().isoformat()

    print(f"=== Sathya Review Scraper (Async Parallel) ===")
    print(f"Snap date     : {snap_date}")
    print(f"Run time (IST): {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"Concurrency   : {MAX_CONCURRENT}\n")

    data = load_data()

    # Find baseline
    all_dates_before = sorted([d for d in data.get("daily", {}) if d < snap_date], reverse=True)
    baseline_date = all_dates_before[0] if all_dates_before else None
    baseline_snap = data["daily"].get(baseline_date, {}) if baseline_date else {}

    baseline = {}
    for b in BRANCHES:
        bid = str(b["id"])
        baseline[bid] = baseline_snap.get(bid, {}).get("total_snap", 
                        data.get("branches", {}).get(bid, {}).get("overall", 0))

    results = {}
    success = 0
    failed = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu"
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            locale="en-IN",
            viewport={"width": 1280, "height": 800}
        )

        # Warm-up
        try:
            page = await context.new_page()
            await page.goto("https://www.google.com/maps", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            await page.close()
            print(" [warm-up] Browser ready ✓")
        except Exception:
            print(" [warm-up] Skipped")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def bounded_scrape(branch):
            async with semaphore:
                bid = str(branch["id"])
                name = branch["name"]
                print(f" [{branch['id']:02d}/36] {name:<25}", end=" ", flush=True)

                live, stars = await scrape_place(context, branch["place_id"], name)

                if live is not None:
                    prev = baseline.get(bid, 0)
                    daily = live - prev
                    results[bid] = {"live": live, "stars": stars, "daily_count": daily}
                    delta_str = f"+{daily}" if daily >= 0 else str(daily)
                    stars_str = f"{stars}★" if stars else "—"
                    print(f"→ {live:,} total {delta_str} new {stars_str} ✓")
                    nonlocal success
                    success += 1
                else:
                    failed.append(name)
                    print("→ FAILED ✗")
                await asyncio.sleep(0.6)

        tasks = [bounded_scrape(b) for b in BRANCHES]
        await asyncio.gather(*tasks)

        await browser.close()

    # ── Process and save results (exact same logic as your original) ──
    if snap_date not in data["daily"]:
        data["daily"][snap_date] = {}

    snap_month = snap_date[:7]
    same_month_dates = sorted([d for d in data.get("daily", {}) if d.startswith(snap_month) and d < snap_date], reverse=True)
    monthly_baseline_date = same_month_dates[0] if same_month_dates else None
    monthly_daily_snap = data["daily"].get(monthly_baseline_date, {}) if monthly_baseline_date else {}

    for b in BRANCHES:
        bid = str(b["id"])
        if bid not in results:
            continue

        r = results[bid]
        live = r["live"]
        stars = r["stars"]
        daily = r["daily_count"]

        old_stars = data["branches"].get(bid, {}).get("star_rating", 0)
        final_stars = stars if stars else old_stars

        prev_monthly = monthly_daily_snap.get(bid, {}).get("monthly", 0)
        monthly = prev_monthly + daily

        data["daily"][snap_date][bid] = {
            "total_snap": live,
            "daily_count": daily,
            "monthly": monthly,
            "star_rating": final_stars,
        }

        data["branches"][bid] = {
            "id": b["id"],
            "name": b["name"],
            "agm": b["agm"],
            "overall": live,
            "star_rating": final_stars,
            "monthly": monthly,
        }

    data.setdefault("logs", []).insert(0, {
        "ran_at": run_time,
        "snap_date": snap_date,
        "baseline_date": baseline_date,
        "success": success,
        "failed": len(failed),
        "failed_names": failed,
    })
    data["logs"] = data["logs"][:50]
    data["last_updated"] = run_time

    save_data(data)
    print(f"\nDone: {success}/36 branches saved for {snap_date}")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as e:
        print(f"\n[FATAL] Scraper crashed: {e}")
        traceback.print_exc()
        sys.exit(1)
