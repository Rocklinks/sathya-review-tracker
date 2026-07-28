"""
Sathya Review Scraper - Async Parallel + Scroll-Only Counting
Scrapes 37 branches using controlled concurrency.
Uses ONLY the scroll method to count reviews by date (no diff fallback).
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

MAX_CONCURRENT = 4
TOTAL_BRANCHES = 37
IST_OFFSET = timedelta(hours=5, minutes=30)

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
    # ── Seenivasan (8 branches)
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
    """Extract overall review count and star rating from a Google Maps page.

    Uses multiple strategies in order:
      1. aria-label selectors (various Google Maps label patterns)
      2. Regex on rendered DOM text content
      3. Regex on page HTML source (structured data, meta, inline JSON)
      4. JavaScript context extraction (window.__NEXT_DATA__, etc.)
    """
    count, stars = None, None
    content = await page.content()

    # ── STRATEGY 1: aria-label selectors ──
    # Google Maps uses aria-labels on buttons/links that contain the review count
    # e.g. "7,366 reviews", "4.9 stars", " Reviews "
    review_label_sels = [
        '[aria-label*="reviews"]',
        '[aria-label*="Reviews"]',
        '[aria-label*="review"]',
        'button[aria-label*="reviews"]',
        'a[aria-label*="reviews"]',
        'span[aria-label*="reviews"]',
        'div[aria-label*="reviews"]',
        '[data-tab-index] [aria-label*="review"]',
    ]
    for sel in review_label_sels:
        try:
            els = await page.locator(sel).all()
            for el in els:
                label = await el.get_attribute("aria-label") or ""
                m = re.search(r"([\d,]+)", label)
                if m:
                    v = int(m.group(1).replace(",", ""))
                    if v > 0:
                        count = max(count, v) if count else v
        except Exception:
            pass
        if count:
            break

    # ── STRATEGY 2: Find elements whose text contains "reviews" with a number ──
    if not count:
        try:
            all_text_els = await page.locator('span, button, a, div').all()
            for el in all_text_els:
                try:
                    txt = (await el.inner_text()).strip()
                except Exception:
                    continue
                if not txt or len(txt) > 60:
                    continue
                # Match patterns like "7,366 reviews" or "(7,366)" near "reviews"
                m = re.search(r"([\d,]+)\s*(?:reviews?|Google\s+reviews?)", txt, re.IGNORECASE)
                if not m:
                    m = re.search(r"([\d,]{3,})", txt)
                if m:
                    v = int(m.group(1).replace(",", ""))
                    if v > 10:
                        count = v
                        break
        except Exception:
            pass

    # ── STRATEGY 3: Regex on full page HTML ──
    if not count:
        for pat in [
            r'([\d,]+)\s*reviews?',
            r'([\d,]+)\s*Google\s+reviews?',
            r'"reviewCount"["\s:]+(\d+)',
            r'"review_count"["\s:]+(\d+)',
            r'"totalReviewCount"["\s:]+(\d+)',
            r'"reviewsCount"["\s:]+(\d+)',
            r'reviewCount["\s:]+(\d+)',
            r'(\d[\d,]{2,})\s*reviews',
            r'(\d[\d,]{2,})\s*Google review',
            r'"numReviews"["\s:]+(\d+)',
            r'aria-label="[^"]*?(\d[\d,]+)\s*review',
        ]:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                v = int(m.group(1).replace(",", ""))
                if v > 10:
                    count = v
                    break

    # ── STRATEGY 4: JavaScript context extraction ──
    if not count:
        try:
            js_data = await page.evaluate("""() => {
                // Try various global data structures Google Maps may use
                const results = {};
                try { results.initState = JSON.stringify(window.APP_INITIALIZATION_STATE || []); } catch(e) {}
                try { results.preloadData = JSON.stringify(window.__PRELOADED_STATE__ || {}); } catch(e) {}
                try { results.nextData = JSON.stringify(window.__NEXT_DATA__ || {}); } catch(e) {}
                try { results.wizData = JSON.stringify(window.WIZ_global_data || {}); } catch(e) {}
                // Also try to find review data from any global variable
                try {
                    const scripts = document.querySelectorAll('script');
                    for (const s of scripts) {
                        const t = s.textContent || '';
                        if (t.includes('reviewCount') || t.includes('ratingValue')) {
                            results.scriptData = t.substring(0, 5000);
                            break;
                        }
                    }
                } catch(e) {}
                return results;
            }""")
            js_str = json.dumps(js_data)
            for pat in [
                r'"reviewCount"["\s:]+(\d+)',
                r'"totalReviewCount"["\s:]+(\d+)',
                r'"review_count"["\s:]+(\d+)',
                r'"numReviews"["\s:]+(\d+)',
                r'"reviewsCount"["\s:]+(\d+)',
                r'reviewCount["\s:]+(\d+)',
            ]:
                m = re.search(pat, js_str, re.IGNORECASE)
                if m:
                    v = int(m.group(1).replace(",", ""))
                    if v > 10:
                        count = v
                        break
        except Exception:
            pass

    # ── STRATEGY 5: Try clicking the reviews button which may reveal count ──
    if not count:
        for sel in [
            'button[aria-label*="Reviews"]',
            'button[data-tab-index="1"]',
            'div[role="tab"]:has-text("Reviews")',
            'button:has-text("Reviews")',
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.count():
                    txt = (await btn.inner_text()).strip()
                    m = re.search(r"([\d,]+)", txt)
                    if m:
                        v = int(m.group(1).replace(",", ""))
                        if v > 10:
                            count = v
                            break
            except Exception:
                pass
            if count:
                break

    # ── STAR RATING: aria-label selectors ──
    star_label_sels = [
        '[aria-label*="stars"]',
        '[aria-label*="star"]',
        'span[aria-label*="stars"]',
        '[aria-label*="star rating"]',
        '[aria-label*="Rated"]',
        '[aria-label*="rated"]',
        'div[role="img"][aria-label*="star"]',
    ]
    for sel in star_label_sels:
        try:
            els = await page.locator(sel).all()
            for el in els:
                label = await el.get_attribute("aria-label") or ""
                m = re.search(r"(\d\.\d)", label)
                if m:
                    v = float(m.group(1))
                    if 1.0 <= v <= 5.0:
                        stars = v
                        break
        except Exception:
            pass
        if stars:
            break

    # ── STAR RATING: text content near "star" ──
    if not stars:
        try:
            all_text_els = await page.locator('span, div').all()
            for el in all_text_els:
                try:
                    txt = (await el.inner_text()).strip()
                except Exception:
                    continue
                if not txt or len(txt) > 40:
                    continue
                m = re.search(r"(\d\.\d)\s*(?:stars?|out\s+of\s+5)", txt, re.IGNORECASE)
                if m:
                    v = float(m.group(1))
                    if 1.0 <= v <= 5.0:
                        stars = v
                        break
        except Exception:
            pass

    # ── STAR RATING: regex on HTML ──
    if not stars:
        for pat in [
            r'"ratingValue"["\s:]+["\']?([\d.]+)',
            r'"aggregateRating".*?"ratingValue"["\s:]+["\']?([\d.]+)',
            r'"starRating"["\s:]+["\']?([\d.]+)',
            r'"rating"["\s:]+["\']?([\d.]+)',
            r'(\d\.\d)\s*(?:stars|out of 5|/5)',
            r'aria-label="[^"]*?(\d\.\d)\s*star',
        ]:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                try:
                    v = float(m.group(1))
                    if 1.0 <= v <= 5.0:
                        stars = v
                        break
                except ValueError:
                    pass

    # ── STAR RATING: JS context ──
    if not stars:
        try:
            js_str = json.dumps(await page.evaluate("() => JSON.stringify(window.APP_INITIALIZATION_STATE || [])"))
            for pat in [
                r'"ratingValue"["\s:]+["\']?([\d.]+)',
                r'"starRating"["\s:]+["\']?([\d.]+)',
                r'"rating"["\s:]+["\']?([\d.]+)',
            ]:
                m = re.search(pat, js_str, re.IGNORECASE)
                if m:
                    try:
                        v = float(m.group(1))
                        if 1.0 <= v <= 5.0:
                            stars = v
                            break
                    except ValueError:
                        pass
        except Exception:
            pass

    return count, stars


async def _count_reviews_by_scroll(page, snap_date):
    """Click Reviews tab, sort Newest, scroll and count reviews dated snap_date."""
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

    while not stop and no_new < 8:
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
                    await pane.evaluate("el=>el.scrollBy(0,2000)")
                else:
                    await page.keyboard.press("End")
            except Exception:
                pass
            await page.wait_for_timeout(random.randint(800, 1500))

    return count


async def scrape_branch(context, branch, snap_date, old_stars):
    """Scrape a single branch using scroll-only counting (no diff fallback)."""
    name = branch["name"]
    place_id = branch["place_id"]
    page = None
    result = {"live": None, "stars": None, "daily": 0, "method": "scroll", "error": None}

    for attempt in range(1, 6):
        try:
            if attempt > 1:
                await asyncio.sleep(attempt * 3)

            page = await context.new_page()
            url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            await page.goto(url, wait_until="networkidle", timeout=45000)
            # Wait longer for JS-rendered content to appear
            await page.wait_for_timeout(random.randint(4000, 6000))

            # Try to wait for a review-related element to appear
            for wait_sel in [
                '[aria-label*="reviews"]', '[aria-label*="Reviews"]',
                'button[aria-label*="Reviews"]', 'div[role="main"]',
            ]:
                try:
                    await page.wait_for_selector(wait_sel, timeout=5000)
                    break
                except Exception:
                    pass

            live, stars = await _get_overall_and_rating(page)
            result["live"] = live
            result["stars"] = stars if stars else old_stars

            if live is None:
                result["error"] = "no count"
                # Debug: dump first 2000 chars of visible text for troubleshooting
                try:
                    debug_text = await page.evaluate("() => document.body.innerText.substring(0, 2000)")
                    print(f"    [debug] Page text preview: {debug_text[:300]}...")
                except Exception:
                    pass
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
    print(f"Branches      : {TOTAL_BRANCHES}\n")

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
        [
            d
            for d in data.get("daily", {})
            if d.startswith(snap_month) and d < snap_date
        ],
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
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-web-security",
            ],
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            locale="en-IN",
            viewport={"width": 1366, "height": 768},
            java_script_enabled=True,
            bypass_csp=True,
        )

        # Stealth: remove webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)

        try:
            # Accept Google consent cookie if present
            wp = await context.new_page()
            await wp.goto(
                "https://www.google.com/maps",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            await wp.wait_for_timeout(1500)
            # Try to accept consent/cookie dialog
            for consent_sel in [
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("Agree")',
                'button[aria-label="Accept all"]',
                '#L2AGLb',  # Google's consent button ID
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

                res = await scrape_branch(context, branch, snap_date, old_stars)

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

                await asyncio.sleep(0.5)

        tasks = [bounded_scrape(b) for b in BRANCHES]
        await asyncio.gather(*tasks)

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
