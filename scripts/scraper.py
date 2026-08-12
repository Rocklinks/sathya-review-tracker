"""
Reviews Scraper.
"""
import re
import io
import json
import os
import asyncio
import traceback
import sys
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Pixel/OCR method — screenshot + tesseract, no selectors/evaluate/API keys.
# Setup once: apt-get install -y tesseract-ocr && pip install pytesseract pillow
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "reviews.json")
BACKUP_DIR = None  # backups disabled
MAX_CONCURRENT = 6
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
    {"id":33, "name":"Virudhunagar", "place_id":"ChIJN3jzNJgsATsRCU3nrB5ntKE", "agm":"Venkatesh"},
    {"id":34, "name":"Virudhunagar-2", "place_id":"ChIJPezaX7wtATsR9sHhFOG6A1c", "agm":"Venkatesh"},
    {"id":35, "name":"Aruppukottai", "place_id":"ChIJy6qqqgYwATsRbcp-hXnoruM", "agm":"Venkatesh"},
    {"id":36, "name":"Aruppukottai -2", "place_id":"ChIJY04wY58xATsRuoJSichVQQE", "agm":"Venkatesh"},
    {"id":37, "name":"Sivakasi", "place_id":"ChIJI2JvEePOBjsREh8b-x4WF4U", "agm":"Venkatesh"},
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
            print(f" [Data] reviews.json corrupted ({e})")
    print(" [Data] No valid data found — starting fresh.")
    return {"branches": {}, "daily": {}, "logs": []}


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f" [Data] Saved reviews.json")


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
    # Try absolute date formats
    for fmt in [
        "%b %d, %Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y",
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
        "%b %d %Y", "%d %b %Y",
    ]:
        try:
            return datetime.strptime(rel.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Handle "Edited" prefix
    if "edited" in r:
        cleaned = re.sub(r'^edited\s+', '', r).strip()
        return resolve_date(cleaned, snap_date_str)
    return ""


async def _ocr_overview(page):
    """PIXEL METHOD: screenshot header region, OCR text, regex parse.
    No selectors, no evaluate, no HTML parsing — reads what a human sees.
    Sidesteps class-name churn / obfuscated markup entirely."""
    if not OCR_AVAILABLE:
        return None, None
    count, stars = None, None
    try:
        png = await page.screenshot(clip={"x": 0, "y": 0, "width": 500, "height": 500})
        img = Image.open(io.BytesIO(png))
        text = pytesseract.image_to_string(img)
    except Exception:
        return None, None

    for pat in [
        r'([\d,]+)\s*Google\s+reviews?',
        r'([\d,]+)\s*reviews?',
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            v = int(m.group(1).replace(",", "").replace(".", ""))
            if v > 5:
                count = v
                break

    for pat in [r'(\d[.,]\d)\s', r'(\d[.,]\d)$']:
        m = re.search(pat, text.strip())
        if m:
            try:
                v = float(m.group(1).replace(",", "."))
                if 1.0 <= v <= 5.0:
                    stars = v
                    break
            except ValueError:
                pass
    return count, stars


async def _get_overall_and_rating(page):
    """Extract overall review count and star rating.
    Uses only native Playwright APIs: page.content(), locator().inner_text(),
    locator().get_attribute(). NO page.evaluate().
    """
    count, stars = None, None

    # ── Raw HTML via CDP ──
    try:
        html = await page.content()
    except Exception:
        html = ""

    # ── Try JSON-LD structured data first (most reliable) ──
    for ld_match in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
        ld_text = ld_match.group(1)
        # Extract aggregateRating
        for pat in [
            r'"aggregateRating"\s*:\s*\{[^}]*"ratingCount"\s*:\s*(\d+)',
            r'"aggregateRating"\s*:\s*\{[^}]*"reviewCount"\s*:\s*(\d+)',
            r'"aggregateRating"\s*:\s*\{[^}]*"ratingValue"\s*:\s*"?([\d.]+)"?',
        ]:
            m = re.search(pat, ld_text)
            if m:
                try:
                    v = float(m.group(1))
                    if v > 5:
                        count = int(v)
                    elif 1.0 <= v <= 5.0:
                        stars = v
                except ValueError:
                    pass
        if count or stars:
            return count, stars

    # ── Visible body text via locator ──
    body_text = ""
    try:
        body_text = await page.locator("body").inner_text(timeout=8000)
    except Exception:
        pass

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

    # ── Extract review count ──
    for pat in [
        r'"userRatingCount"[:\s,]*(\d+)',
        r'"reviewCount"[:\s,]*(\d+)',
        r'"ratingCount"[:\s,]*(\d+)',
        r'"totalReviewCount"[:\s,]*(\d+)',
        r'"numReviews"[:\s,]*(\d+)',
        r'"reviewsCount"[:\s,]*(\d+)',
        r'"review_total"[:\s,]*(\d+)',
        r'([\d,]+)\s*Google\s+reviews?',
        r'([\d,]+)\s*reviews?',
    ]:
        m = re.search(pat, combined, re.IGNORECASE)
        if m:
            v = int(m.group(1).replace(",", ""))
            if v > 5:
                count = v
                break

    # ── Extract star rating ──
    for pat in [
        r'"ratingValue"[:\s,]*"?([\d.]+)"?',
        r'"starRating"[:\s,]*"?([\d.]+)"?',
        r'"averageRating"[:\s,]*"?([\d.]+)"?',
        r'"score"[:\s,]*"?([\d.]+)"?',
        r'(\d\.\d)\s*stars?',
        r'(\d\.\d)\s*out\s+of\s+5',
        r'Rated\s+(\d\.\d)',
        r'"rating"[:\s,]*"?([\d.]+)"?',
        r'(\d\.\d)\s*Google\s+reviews',
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

    # ── Fallback: look for "X reviews" pattern in aria-labels ──
    if count is None:
        for label in aria_text.split("\n"):
            m = re.search(r'([\d,]+)\s*reviews?', label, re.IGNORECASE)
            if m:
                v = int(m.group(1).replace(",", ""))
                if v > 5:
                    count = v
                    break

    return count, stars


async def _count_reviews_by_scroll(page, snap_date):
    """Click Reviews tab, sort Newest, scroll the review PANEL and count
    reviews dated snap_date. Uses locator API only (no evaluate)."""

    # ── 1. Click the Reviews tab ──
    reviews_clicked = False
    for sel in [
        'button[aria-label="Reviews"]',
        'button[aria-label*="Reviews"]',
        'button[data-tab-index="1"]',
        'div[role="tab"][data-tab-index="1"]',
        'div[role="tab"]:has-text("Reviews")',
        'button:has-text("Reviews")',
        'a:has-text("Reviews")',
        '[data-tab-id="1"]',
    ]:
        try:
            t = page.locator(sel).first
            if await t.count():
                await t.click(timeout=4000)
                await page.wait_for_timeout(2000)
                reviews_clicked = True
                break
        except Exception:
            continue

    if not reviews_clicked:
        return 0

    # ── 2. Sort by Newest ──
    sort_clicked = False
    for sel in [
        'button[aria-label="Sort reviews"]',
        'button[aria-label*="Sort reviews"]',
        'button[aria-label*="Sort by"]',
        'button[data-value="Sort"]',
        'button:has-text("Sort")',
        'div[role="button"]:has-text("Sort")',
        'span:has-text("Sort by"):not([class])',
    ]:
        try:
            sb = page.locator(sel).first
            if await sb.count():
                await sb.click(timeout=3000)
                await page.wait_for_timeout(1000)
                sort_clicked = True
                break
        except Exception:
            continue

    if sort_clicked:
        for ns in [
            'li[data-index="1"]',
            'li:has-text("Newest")',
            'div[role="menuitemradio"]:has-text("Newest")',
            'div[role="option"]:has-text("Newest")',
            'div[role="menuitem"]:has-text("Newest")',
            'span:has-text("Newest"):not([class])',
        ]:
            try:
                n = page.locator(ns).first
                if await n.count():
                    await n.click(timeout=2000)
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

    # ── 3. Find the scrollable review panel ──
    review_panel = None
    for psel in [
        'div.m6QErb.DxyBCb.kA9KIf.dS8AEf',   # classic review scrollable
        'div[role="main"] div.m6QErb.DxyBCb',
        'div.m6QErb[aria-label]',
        'div[role="feed"]',
        'div.m6QErb',
    ]:
        try:
            p = page.locator(psel).first
            if await p.count():
                review_panel = p
                break
        except Exception:
            continue

    # ── 4. Initial scroll inside the review panel ──
    for _ in range(3):
        try:
            if review_panel:
                await review_panel.evaluate("el => el.scrollTop = el.scrollHeight")
            else:
                await page.evaluate("() => { const el = document.querySelector('div.m6QErb.DxyBCb'); if(el) el.scrollTop = el.scrollHeight; }")
        except Exception:
            try:
                await page.keyboard.press("End")
            except Exception:
                pass
        await page.wait_for_timeout(1500)

    # ── 5. Scroll loop ──
    seen, count, stop, no_new = set(), 0, False, 0
    max_scroll_attempts = 25
    scroll_attempts = 0

    # Modern selectors for review cards
    CARD_SELECTORS = [
        'div[data-review-id]',
        'div.jftiEf',
        'div[data-href*="review"]',
        'div[aria-label*="review by"]',
        'div[jscontroller][data-review-id]',
    ]

    # Date patterns to match inside review card text (relative + absolute)
    DATE_REL_PATTERNS = re.compile(
        r'(?:\d+\s+(?:hour|minute|second|day|week|month|year)s?\s+ago'
        r'|a\s+(?:day|week|month|year)\s+ago'
        r'|yesterday'
        r'|just\s+now'
        r'|(?:\d{1,2}\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}'
        r'|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}'
        r'|\d{4}[-/]\d{2}[-/]\d{2})',
        re.IGNORECASE,
    )

    while not stop and no_new < 8 and scroll_attempts < max_scroll_attempts:
        scroll_attempts += 1

        # Collect cards from all selectors
        cards = []
        for cs in CARD_SELECTORS:
            try:
                found = await page.query_selector_all(cs)
                cards.extend(found)
            except Exception:
                pass
        # Deduplicate by data-review-id or element ref
        seen_ids = set()
        unique_cards = []
        for card in cards:
            rid = await card.get_attribute("data-review-id") or str(id(card))
            if rid not in seen_ids:
                seen_ids.add(rid)
                unique_cards.append(card)

        new = 0
        for card in unique_cards:
            rid = await card.get_attribute("data-review-id") or str(id(card))
            if rid in seen:
                continue
            seen.add(rid)
            new += 1

            date_str = ""
            try:
                card_text = await card.inner_text(timeout=3000)
                for line in card_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # Check if this line contains a date-like pattern
                    if DATE_REL_PATTERNS.search(line):
                        # Skip lines that are just ratings like "4.5" or "⭐ 4"
                        if re.match(r'^[\d.★\s]+$', line):
                            continue
                        date_str = line
                        break
                # Also try individual child spans for more precise matching
                if not date_str:
                    for tag in ['span', 'time', 'div']:
                        elements = await card.query_selector_all(tag)
                        for el in elements:
                            try:
                                txt = (await el.inner_text(timeout=1000)).strip()
                                if txt and DATE_REL_PATTERNS.search(txt) and not re.match(r'^[\d.★\s]+$', txt):
                                    date_str = txt
                                    break
                            except Exception:
                                continue
                        if date_str:
                            break
            except Exception:
                pass

            resolved = resolve_date(date_str, snap_date)
            if resolved == snap_date:
                count += 1
            elif resolved and resolved < snap_date:
                stop = True
                break

        no_new = 0 if new else no_new + 1

        if not stop:
            try:
                if review_panel:
                    await review_panel.evaluate("el => el.scrollTop = el.scrollHeight")
                else:
                    await page.evaluate("() => { const el = document.querySelector('div.m6QErb.DxyBCb'); if(el) el.scrollTop = el.scrollHeight; }")
            except Exception:
                try:
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
                        '/maps/place/', '/maps/preview',
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
            url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            await page.goto(url, wait_until="load", timeout=45000)
            # Wait for API responses to arrive
            await page.wait_for_timeout(6000)

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
                        await page.goto(url, wait_until="load", timeout=45000)
                        await page.wait_for_timeout(6000)
                        break
                except Exception:
                    pass

            await page.wait_for_timeout(random.randint(2000, 4000))

            # ── Tier 1: Parse captured API responses ──
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

            # ── Tier 2: OCR screenshot method ──
            if result["live"] is None:
                live, stars = await _ocr_overview(page)
                if live:
                    result["live"] = live
                    result["method"] = "pixel"
                if stars:
                    result["stars"] = stars

            # ── Tier 3: DOM / HTML parsing ──
            if result["live"] is None:
                live, stars = await _get_overall_and_rating(page)
                result["live"] = live
                if stars:
                    result["stars"] = stars

            if not result["stars"]:
                result["stars"] = old_stars

            # ── Tier 4: Fallback to previous data ──
            if result["live"] is None:
                old_overall = data.get("branches", {}).get(str(branch["id"]), {}).get("overall", 0)
                if old_overall and old_overall > 0:
                    result["live"] = old_overall
                    result["stars"] = old_stars if old_stars else result["stars"]
                    result["method"] = "fallback"
                    result["error"] = None
                else:
                    result["error"] = "no count"
                    continue

            # ── Count daily reviews via scroll ──
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
        # Launch browser directly — Obscura can't render Google Maps JS.
        import shutil as _shutil
        brave = (
            _shutil.which("brave") or _shutil.which("brave-browser")
            or _shutil.which("google-chrome") or _shutil.which("chromium")
        )
        if not brave:
            # Fallback: find Playwright's installed Chromium
            import glob as _glob
            from pathlib import Path as _Path
            candidates = _glob.glob(
                str(_Path.home() / ".cache" / "ms-playwright" / "chromium-*" / "chrome-linux" / "chrome")
            )
            if not candidates:
                candidates = _glob.glob(
                    str(_Path.home() / ".cache" / "ms-playwright" / "chromium-*" / "chrome-linux" / "chromium")
                )
            if candidates:
                brave = candidates[0]
        if not brave:
            print("[FATAL] No browser found. Install brave, google-chrome, or run: playwright install chromium")
            sys.exit(1)

        browser = await p.chromium.launch(
            executable_path=brave,
            headless=True,
            args=[
                "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            locale="en-IN",
            viewport={"width": 1366, "height": 768},
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/136.0.7103.25 Safari/537.36"
            ),
        )
        print(f" [browser] Launched {brave} ✓")

        try:
            wp = await context.new_page()
            await wp.goto(
                "https://www.google.com/maps",
                wait_until="load",
                timeout=20000,
            )
            await wp.wait_for_timeout(2000)
            for consent_sel in [
                '#L2AGLb',
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("Reject all")',
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
                    # Show delta from previous total for accurate daily count
                    prev = data.get("branches", {}).get(bid, {}).get("overall", 0)
                    if res["live"] and prev and res["live"] > prev:
                        delta = res["live"] - prev
                    else:
                        delta = res["daily"]
                    delta_str = f"+{delta}" if delta >= 0 else str(delta)
                    stars_str = f"{res['stars']}★" if res["stars"] else "—"
                    print(
                        f"→ {res['live']:,} total {delta_str} new {stars_str} ✓"
                    )
                    success += 1
                await asyncio.sleep(random.randint(1, 3))

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
        old_overall = data["branches"].get(bid, {}).get("overall", 0)
        old_stars = data["branches"].get(bid, {}).get("star_rating", 0)
        final_stars = stars if stars else old_stars

        # Compute daily count from total_snap delta (scroll date extraction is unreliable)
        if live and old_overall and live > old_overall:
            daily = live - old_overall
            r["method"] = "delta"
        else:
            daily = r["daily"]

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
