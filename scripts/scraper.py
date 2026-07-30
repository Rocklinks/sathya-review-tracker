"""
Sathya Review Scraper - Async Parallel + Scroll-Only Counting
Scrapes 37 branches using controlled concurrency.
Uses ONLY the scroll method to count reviews by date (no diff fallback).

Routes through Obscura (stealth browser, CDP) instead of launching a
vanilla Chromium — vanilla Chromium gets fingerprinted/blocked by Google
Maps, which is why every branch was timing out on networkidle.
Also removes all page.evaluate() usage — Obscura returns {} for JS
evaluate calls, so extraction now relies only on native Playwright
locator APIs (page.content(), locator().inner_text(), get_attribute()).
"""
import re
import json
import os
import asyncio
import traceback
import sys
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "reviews.json")
BACKUP_DIR = os.path.join(os.path.dirname(DATA_FILE), "backups")
MAX_CONCURRENT = 6
IST_OFFSET = timedelta(hours=5, minutes=30)

# Obscura serves a CDP endpoint locally. Confirm/adjust the port to match
# how you're running Obscura — override via env var if it differs.
OBSCURA_CDP_URL = os.environ.get("OBSCURA_CDP_URL", "http://127.0.0.1:9222")

BRANCHES = [
    # ── Siva (6 branches)
    {"id":1, "name":"Tuticorin-1", "place_id":"ChIJ5zJNoJfvAzsR-bJE_3bbNYw", "agm":"Siva"},
    {"id":2, "name":"Tuticorin-2", "place_id":"ChIJH6gY4-PvAzsRJ50skTlx3cs", "agm":"Siva"},
    {"id":3, "name":"Thiruchendur-1", "place_id":"ChIJeXA4vJKRAzsRBovAtv6lMuQ", "agm":"Siva"},
    {"id":4, "name":"Thisayanvilai-1", "place_id":"ChIJVWkvdfh_BDsRdvtimKCLS5Y", "agm":"Siva"},
    {"id":5, "name":"Eral-2", "place_id":"ChIJbwAA0KGMAzsRkQilW5PceeA", "agm":"Siva"},
    {"id":6, "name":"Udankudi", "place_id":"ChIJPQAAACyEAzsRgjznQ1GLom0", "agm":"Siva"},
    # ── John (4 branches)
    {"id":7, "name":"Tirunelveli-1", "place_id":"ChIJ2RU2NvQRBDsRq-Fw7IVwx7k", "agm":"John"},
    {"id":8, "name":"Valliyur-1", "place_id":"ChIJcVNk6TtnBDsRBoP4zpExt5k", "agm":"John"},
    {"id":9, "name":"Ambasamudram-1", "place_id":"ChIJ9SGeIi85BDsRZk4QdyW9BSY", "agm":"John"},
    {"id":10, "name":"Anjugramam-1", "place_id":"ChIJ4yeJebLtBDsRDceoxujdGyc", "agm":"John"},
    # ── Jeeva (7 branches)
    {"id":11, "name":"Nagercoil", "place_id":"ChIJe1LZBiTxBDsRJFLjlbgZoIs", "agm":"Jeeva"},
    {"id":12, "name":"Marthandam", "place_id":"ChIJcWptCRdVBDsRlJh2q0-rnfY", "agm":"Jeeva"},
    {"id":13, "name":"Thuckalay-1", "place_id":"ChIJc9QgEub4BDsRoyDR4Wd6tYA", "agm":"Jeeva"},
    {"id":14, "name":"Colachel-1", "place_id":"ChIJgRkBLw39BDsR58D0lwNo5Ts", "agm":"Jeeva"},
    {"id":15, "name":"Kulasekharam-1", "place_id":"ChIJw0Ep-kNXBDsRe5ad32jAeAk", "agm":"Jeeva"},
    {"id":16, "name":"Monday Market", "place_id":"ChIJTceRGAD5BDsR65i3YNTcYHk", "agm":"Jeeva"},
    {"id":17, "name":"Karungal-1", "place_id":"ChIJfTP5ASr_BDsRgsBaeQltkw4", "agm":"Jeeva"},
    # ── Seenivasan (9 branches)
    {"id":18, "name":"Kovilpatti", "place_id":"ChIJHY0o-26yBjsRt7wbXB1pDUE", "agm":"Seenivasan"},
    {"id":19, "name":"Ramnad", "place_id":"ChIJNVVVVaGiATsRnunSgOTvbE8", "agm":"Seenivasan"},
    {"id":20, "name":"Paramakudi", "place_id":"ChIJ-dgjBzQHATsRf27FWAJgmsA", "agm":"Seenivasan"},
    {"id":21, "name":"Sayalkudi-1", "place_id":"ChIJRTqudn9lATsR2fYyMmxlOrw", "agm":"Seenivasan"},
    {"id":22, "name":"Villathikullam", "place_id":"ChIJi_wAkwVbATsRtFl3_V5rGrY", "agm":"Seenivasan"},
    {"id":23, "name":"Sattur-2", "place_id":"ChIJNVVVVcHKBjsR7xMX97RFn8Q", "agm":"Seenivasan"},
    {"id":24, "name":"Sankarankovil-1", "place_id":"ChIJE1mKnhSXBjsRKMQ-9JKQf_c", "agm":"Seenivasan"},
    {"id":25, "name":"Kayathar-1", "place_id":"ChIJx5ebtUgRBDsRMquPZNUJVpw", "agm":"Seenivasan"},
    {"id":26, "name":"Ramnad-2", "place_id":"ChIJcWPpFSSZATsR1ai6lxBXkAw", "agm":"Seenivasan"},
    # ── Muthuselvam (6 branches)
    {"id":27, "name":"Thenkasi", "place_id":"ChIJuaqqquEpBDsRVITw0MMYklc", "agm":"Muthuselvam"},
    {"id":28, "name":"Thenkasi-2", "place_id":"ChIJiwqLye6DBjsRo9v1mWXaycI", "agm":"Muthuselvam"},
    {"id":29, "name":"Surandai-1", "place_id":"ChIJPb1_eEOdBjsRjL9IVCVJhi8", "agm":"Muthuselvam"},
    {"id":30, "name":"Puliyankudi-1", "place_id":"ChIJjZqoc46RBjsRQTGHnNC8xxA", "agm":"Muthuselvam"},
    {"id":31, "name":"Sengottai-1", "place_id":"ChIJw3zzKiaBBjsR9KDyGpn1nXU", "agm":"Muthuselvam"},
    {"id":32, "name":"Rajapalayam", "place_id":"ChIJW2ot-NDpBjsRMTfMF2IV-xE", "agm":"Muthuselvam"},
    # ── Venkadesan (5 branches)
    {"id":33, "name":"Virudhunagar", "place_id":"ChIJN3jzNJgsATsRCU3nrB5ntKE", "agm":"Venkadesan"},
    {"id":34, "name":"Virudhunagar-2", "place_id":"ChIJPezaX7wtATsR9sHhFOG6A1c", "agm":"Venkadesan"},
    {"id":35, "name":"Aruppukottai", "place_id":"ChIJy6qqqgYwATsRbcp-hXnoruM", "agm":"Venkadesan"},
    {"id":36, "name":"Aruppukottai-2", "place_id":"ChIJY04wY58xATsRuoJSichVQQE", "agm":"Venkadesan"},
    {"id":37, "name":"Sivakasi", "place_id":"ChIJI2JvEePOBjsREh8b-x4WF4U", "agm":"Venkadesan"},
]

TOTAL_BRANCHES = len(BRANCHES)


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
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")], reverse=True
        )
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
    today_str = (datetime.utcnow() + IST_OFFSET).strftime("%Y-%m-%d")
    backup_path = os.path.join(BACKUP_DIR, f"reviews_{today_str}.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f" [Data] Backup saved: backups/reviews_{today_str}.json")
    cutoff = datetime.utcnow()
    cleaned = 0
    for fname in os.listdir(BACKUP_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(BACKUP_DIR, fname)
        try:
            age_days = (cutoff - datetime.fromtimestamp(os.path.getmtime(fpath))).days
            if age_days > 90:
                os.remove(fpath)
                cleaned += 1
        except Exception:
            pass
    if cleaned:
        print(f" [Data] Cleaned {cleaned} old backups")


def resolve_date(rel, snap_date_str):
    """Convert Google relative date string to YYYY-MM-DD."""
    if not rel:
        return ""
    r = rel.lower().strip()
    snap = datetime.strptime(snap_date_str, "%Y-%m-%d").date()
    today_ist = (datetime.utcnow() + IST_OFFSET).date()
    if any(x in r for x in ["just now", "second", "minute", "moment"]):
        return str(today_ist)
    if "hour" in r:
        m = re.search(r"(\d+)", r)
        hours = int(m.group(1)) if m else 1
        if hours <= 23:
            return str(snap)
        return str(snap - timedelta(days=1))
    if "1 day ago" in r or "a day ago" in r or "yesterday" in r:
        return str(snap - timedelta(days=1))
    if "day" in r:
        m = re.search(r"(\d+)", r)
        n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(days=n))
    if "week" in r:
        m = re.search(r"(\d+)", r)
        n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(weeks=n))
    if "month" in r:
        m = re.search(r"(\d+)", r)
        n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(days=n * 30))
    if "year" in r:
        m = re.search(r"(\d+)", r)
        n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(days=n * 365))
    for fmt in ["%b %d, %Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(rel.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


async def _get_overall_and_rating(page):
    """Extract overall review count and star rating.
    NO page.evaluate() anywhere — Obscura returns {} for JS-evaluate calls.
    Uses only native Playwright APIs: page.content(), locator().inner_text(),
    locator().get_attribute().
    """
    count, stars = None, None

    # ── Raw HTML via CDP (not JS evaluate) ──
    try:
        html = await page.content()
    except Exception:
        html = ""

    # ── Visible body text via locator (not evaluate/treewalker) ──
    try:
        body_text = await page.locator("body").inner_text(timeout=5000)
    except Exception:
        body_text = ""

    # ── aria-label values via locator API ──
    aria_text = ""
    try:
        aria_locator = page.locator("[aria-label]")
        n = await aria_locator.count()
        labels = []
        for i in range(min(n, 300)):
            try:
                al = await aria_locator.nth(i).get_attribute("aria-label")
                if al:
                    labels.append(al)
            except Exception:
                continue
        aria_text = "\n".join(labels)
    except Exception:
        pass

    combined = "\n".join([html, body_text, aria_text])

    for pat in [
        r'"userRatingCount"[:\s,]*(\d+)',
        r'"reviewCount"[:\s,]*(\d+)',
        r'"ratingCount"[:\s,]*(\d+)',
        r'"totalReviewCount"[:\s,]*(\d+)',
        r'"numReviews"[:\s,]*(\d+)',
        r'"reviewsCount"[:\s,]*(\d+)',
        r'([\d,]+)\s*Google\s+reviews?',
        r'([\d,]+)\s*reviews?',
    ]:
        m = re.search(pat, combined, re.IGNORECASE)
        if m:
            v = int(m.group(1).replace(",", ""))
            if v > 5:
                count = v
                break

    for pat in [
        r'"ratingValue"[:\s,]*"?([\d.]+)"?',
        r'"starRating"[:\s,]*"?([\d.]+)"?',
        r'"averageRating"[:\s,]*"?([\d.]+)"?',
        r'"score"[:\s,]*"?([\d.]+)"?',
        r'(\d\.\d)\s*stars?',
        r'(\d\.\d)\s*out\s+of\s+5',
        r'Rated\s+(\d\.\d)',
        r'"rating"[:\s,]*"?([\d.]+)"?',
    ]:
        m = re.search(pat, combined, re.IGNORECASE)
        if m:
            try:
                v = float(m.group(1))
                if 1.0 <= v <= 5.0:
                    stars = v
                    break
            except ValueError:
                pass

    return count, stars


async def _count_reviews_by_scroll(page, snap_date):
    """Click Reviews tab, sort Newest, scroll and count reviews dated snap_date.
    Locator-only, no evaluate."""
    for sel in [
        'button[aria-label="Reviews"]',
        'button[aria-label*="Reviews"]',
        'button[data-tab-index="1"]',
        'div[role="tab"]:has-text("Reviews")',
        'button:has-text("Reviews")',
        'a:has-text("Reviews")',
        '[data-tab-id="1"]',
    ]:
        try:
            t = await page.wait_for_selector(sel, timeout=4000)
            if t:
                await t.click()
                await page.wait_for_timeout(1500)
                break
        except Exception:
            continue

    for sel in [
        'button[aria-label="Sort reviews"]',
        'button[aria-label*="Sort"]',
        'button[data-value="Sort"]',
        'button:has-text("Sort")',
        'div[role="button"]:has-text("Sort")',
        'span:has-text("Newest"):not([class])',
    ]:
        try:
            sb = await page.wait_for_selector(sel, timeout=4000)
            if sb:
                await sb.click()
                await page.wait_for_timeout(800)
                for ns in [
                    'li[data-index="1"]',
                    'li:has-text("Newest")',
                    'div[role="menuitemradio"]:has-text("Newest")',
                    'div[role="option"]:has-text("Newest")',
                    'div:has-text("Newest"):not([class])',
                ]:
                    try:
                        n = await page.wait_for_selector(ns, timeout=2000)
                        if n:
                            await n.click()
                            await page.wait_for_timeout(1500)
                            break
                    except Exception:
                        continue
                break
        except Exception:
            continue

    seen, count, stop, no_new = set(), 0, False, 0
    max_scroll_attempts = 20
    scroll_attempts = 0
    while not stop and no_new < 8 and scroll_attempts < max_scroll_attempts:
        scroll_attempts += 1
        cards = await page.query_selector_all(
            'div[data-review-id], div.jftiEf, div[data-href*="review"], '
            'div.gMBQx, div.Svr5Qb, div[class*="review"]'
        )
        if not cards:
            cards = await page.query_selector_all('div.jftiEf, div[data-review-id]')
        new = 0
        for card in cards:
            rid = await card.get_attribute("data-review-id") or str(id(card))
            if rid in seen:
                continue
            seen.add(rid)
            new += 1
            date_str = ""
            for dsel in [
                'span.rsqaWe', 'span[class*="DU9Pgb"]', 'span[class*="xRkPPb"]',
                'span[class*="rsqaWe"]', 'span[class*="deyGud"]', 'span.fYySGc',
                'span[datetime]', 'span[class*="date"]', 'span[class*="time"]',
            ]:
                de = await card.query_selector(dsel)
                if de:
                    date_str = (await de.inner_text()).strip()
                    if not date_str:
                        date_str = await de.get_attribute("datetime") or ""
                    break
            resolved = resolve_date(date_str, snap_date)
            if resolved == snap_date:
                count += 1
            elif resolved and resolved < snap_date:
                stop = True
                break
        no_new = 0 if new else no_new + 1
        if not stop:
            try:
                pane = await page.query_selector(
                    'div.m6QErb[tabindex="-1"], div.m6QErb, '
                    'div[role="main"] div[tabindex="-1"], '
                    'div.m6QErb.DxyBCb, div.m6QErb.KFu5E'
                )
                if pane:
                    await page.mouse.wheel(0, 2000)
                else:
                    await page.keyboard.press("End")
            except Exception:
                pass
            await page.wait_for_timeout(random.randint(800, 1500))
    return count


async def scrape_branch(context, branch, snap_date, old_stars, data):
    """Scrape a single branch. `data` is passed in explicitly (not a global)."""
    name = branch["name"]
    place_id = branch["place_id"]
    page = None
    result = {"live": None, "stars": None, "daily": 0, "method": "scroll", "error": None}
    for attempt in range(1, 6):
        result["error"] = None
        try:
            if attempt > 1:
                wait = attempt * 3 + random.randint(1, 4)
                print(f"    retry in {wait}s...", end=" ", flush=True)
                await asyncio.sleep(wait)
            page = await context.new_page()
            captured_responses = []

            async def on_response(response):
                try:
                    url = response.url
                    if any(kw in url for kw in [
                        '/maps/preview/place', '/maps/preview/review',
                        '/maps/api/js', '/place', '/review',
                    ]):
                        try:
                            body = await response.text()
                            if len(body) > 50:
                                captured_responses.append(body)
                        except Exception:
                            pass
                except Exception:
                    pass

            page.on("response", on_response)
            url = f"https://www.google.com/maps/search/?api=1&place_id={place_id}"
            await page.goto(url, wait_until="networkidle", timeout=45000)

            for consent_sel in [
                '#L2AGLb',
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("Reject all")',
            ]:
                try:
                    btn = page.locator(consent_sel).first
                    if await btn.count():
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        await page.goto(url, wait_until="networkidle", timeout=45000)
                        break
                except Exception:
                    pass

            await page.wait_for_timeout(random.randint(2000, 4000))

            if captured_responses:
                api_text = "\n".join(captured_responses)
                for pat in [
                    r'"userRatingCount"[:\s,]*(\d+)',
                    r'"reviewCount"[:\s,]*(\d+)',
                    r'"ratingCount"[:\s,]*(\d+)',
                    r'"totalReviewCount"[:\s,]*(\d+)',
                    r'"numReviews"[:\s,]*(\d+)',
                ]:
                    m = re.search(pat, api_text)
                    if m:
                        v = int(m.group(1))
                        if v > 0:
                            result["live"] = v
                            break
                for pat in [
                    r'"ratingValue"[:\s,]*"?([\d.]+)"?',
                    r'"averageRating"[:\s,]*"?([\d.]+)"?',
                    r'"starRating"[:\s,]*"?([\d.]+)"?',
                    r'"score"[:\s,]*"?([\d.]+)"?',
                    r'"rating"[:\s,]*"?([\d.]+)"?',
                ]:
                    m = re.search(pat, api_text)
                    if m:
                        try:
                            v = float(m.group(1))
                            if 1.0 <= v <= 5.0:
                                result["stars"] = v
                                break
                        except ValueError:
                            pass

            if result["live"] is None:
                live, stars = await _get_overall_and_rating(page)
                result["live"] = live
                if stars:
                    result["stars"] = stars

            if not result["stars"]:
                result["stars"] = old_stars

            if result["live"] is None:
                old_overall = data.get("branches", {}).get(str(branch["id"]), {}).get("overall", 0)
                if old_overall and old_overall > 0:
                    result["live"] = old_overall
                    result["stars"] = old_stars if old_stars else result["stars"]
                    result["method"] = "fallback"
                    result["error"] = None
                    count = await _count_reviews_by_scroll(page, snap_date)
                    result["daily"] = count
                    break
                result["error"] = "no count"
                continue

            count = await _count_reviews_by_scroll(page, snap_date)
            result["daily"] = count
            result["method"] = "scroll"
            break
        except Exception as e:
            result["error"] = str(e)
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            page = None
    return result


async def run():
    now_ist = datetime.utcnow() + IST_OFFSET
    snap_date = (now_ist.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    run_time = datetime.utcnow().isoformat()
    print(f"=== Sathya Review Scraper (Async Parallel + Scroll) ===")
    print(f"Snap date     : {snap_date}")
    print(f"Run time (IST): {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"Concurrency   : {MAX_CONCURRENT}")
    print(f"Branches      : {TOTAL_BRANCHES}")
    print(f"Obscura CDP   : {OBSCURA_CDP_URL}\n")

    data = load_data()
    all_dates_before = sorted(
        [d for d in data.get("daily", {}) if d < snap_date], reverse=True
    )
    baseline_date = all_dates_before[0] if all_dates_before else None
    if baseline_date:
        gap = (
            datetime.strptime(snap_date, "%Y-%m-%d")
            - datetime.strptime(baseline_date, "%Y-%m-%d")
        ).days
        if gap > 1:
            print(
                f"⚠ WARNING: Baseline is {gap} days old ({baseline_date} → {snap_date})."
            )
            print(f"  Daily counts will reflect {gap} days of reviews, not 1.")

    if snap_date not in data["daily"]:
        data["daily"][snap_date] = {}

    snap_month = snap_date[:7]
    same_month_dates = sorted(
        [d for d in data.get("daily", {}) if d.startswith(snap_month) and d < snap_date],
        reverse=True,
    )
    monthly_baseline_date = same_month_dates[0] if same_month_dates else None
    monthly_daily_snap = (
        data["daily"].get(monthly_baseline_date, {}) if monthly_baseline_date else {}
    )

    results = {}
    success = 0
    failed = []

    async with async_playwright() as p:
        # Connect to Obscura's CDP endpoint instead of launching vanilla
        # Chromium. Vanilla Chromium gets fingerprinted/blocked by Google
        # Maps — that's why every branch previously timed out on networkidle.
        try:
            browser = await p.chromium.connect_over_cdp(OBSCURA_CDP_URL)
        except Exception as e:
            print(f"[FATAL] Could not connect to Obscura at {OBSCURA_CDP_URL}: {e}")
            print("        Confirm Obscura is running and OBSCURA_CDP_URL is correct.")
            sys.exit(1)

        # Use Obscura's existing context — it already manages its own
        # fingerprint/stealth profile, so we don't override UA/viewport here.
        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        try:
            wp = await context.new_page()
            await wp.goto(
                "https://www.google.com/maps",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            await wp.wait_for_timeout(1500)
            for consent_sel in [
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("Agree")',
                'button[aria-label="Accept all"]',
                '#L2AGLb',
            ]:
                try:
                    btn = wp.locator(consent_sel).first
                    if await btn.count():
                        await btn.click()
                        await wp.wait_for_timeout(1000)
                        break
                except Exception:
                    pass
            await wp.close()
            print(" [warm-up] Browser ready ✓")
        except Exception:
            print(" [warm-up] Skipped")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def bounded_scrape(branch):
            nonlocal success
            async with semaphore:
                bid = str(branch["id"])
                name = branch["name"]
                old_stars = data.get("branches", {}).get(bid, {}).get("star_rating", 0)
                print(
                    f" [{branch['id']:02d}/{TOTAL_BRANCHES}] {name:<25}",
                    end=" ",
                    flush=True,
                )
                res = await scrape_branch(context, branch, snap_date, old_stars, data)
                if res["error"]:
                    failed.append(name)
                    print(f"→ FAILED: {res['error']} ✗")
                else:
                    results[bid] = res
                    delta = res["daily"]
                    delta_str = f"+{delta}" if delta >= 0 else str(delta)
                    stars_str = f"{res['stars']}★" if res["stars"] else "—"
                    method_str = f"({res['method']})"
                    print(
                        f"→ {res['live']:,} total {delta_str} new {stars_str} {method_str} ✓"
                    )
                    success += 1
                await asyncio.sleep(random.randint(1, 3))

        tasks = [bounded_scrape(b) for b in BRANCHES]
        await asyncio.gather(*tasks)
        # Don't close a browser we don't own — just disconnect.
        await browser.close()

    for b in BRANCHES:
        bid = str(b["id"])
        if bid not in results:
            continue
        r = results[bid]
        live = r["live"]
        stars = r["stars"]
        daily = r["daily"]
        old_stars = data["branches"].get(bid, {}).get("star_rating", 0)
        final_stars = stars if stars else old_stars
        prev_monthly = monthly_daily_snap.get(bid, {}).get("monthly", 0)
        monthly = max(0, prev_monthly + daily)
        data["daily"][snap_date][bid] = {
            "total_snap": live,
            "daily_count": daily,
            "monthly": monthly,
            "star_rating": final_stars,
            "method": r["method"],
        }
        data["branches"][bid] = {
            "id": b["id"],
            "name": b["name"],
            "agm": b["agm"],
            "overall": live,
            "star_rating": final_stars,
            "monthly": monthly,
        }

    data.setdefault("logs", []).insert(
        0,
        {
            "ran_at": run_time,
            "snap_date": snap_date,
            "baseline_date": baseline_date,
            "success": success,
            "failed": len(failed),
            "failed_names": failed,
        },
    )
    data["logs"] = data["logs"][:50]
    data["last_updated"] = run_time
    save_data(data)
    print(f"\nDone: {success}/{TOTAL_BRANCHES} branches saved for {snap_date}")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as e:
        print(f"\n[FATAL] Scraper crashed: {e}")
        traceback.print_exc()
        sys.exit(1)
