"""
Sathya Review Scraper - Parallel + Actual Review Counting
- Runs at 12:00 AM IST (18:30 UTC)
- snap_date = yesterday IST
- Counts actual reviews by scrolling Newest sort, stopping when date < snap_date
- Keeps parallel architecture (MAX_CONCURRENT=4 for scroll stability)
- Falls back to snapshot diff if scroll fails
"""
import re, json, os, asyncio, traceback, sys, random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "reviews.json")
BACKUP_DIR = os.path.join(os.path.dirname(DATA_FILE), "backups")
MAX_CONCURRENT = 4  # Lower than before — scrolling needs more memory per tab

BRANCHES = [
    {"id":1,  "name":"Tuticorin-1",     "place_id":"ChIJ5zJNoJfvAzsR-bJE_3bbNYw",  "agm":"Sivaperumal"},
    {"id":2,  "name":"Tuticorin-2",     "place_id":"ChIJH6gY4-PvAzsRJ50skTlx3cs",  "agm":"Sivaperumal"},
    {"id":3,  "name":"Thiruchendur-1",  "place_id":"ChIJeXA4vJKRAzsRBovAtv6lMuQ",  "agm":"Sivaperumal"},
    {"id":4,  "name":"Thisayanvilai-1", "place_id":"ChIJVWkvdfh_BDsRdvtimKCLS5Y",  "agm":"Sivaperumal"},
    {"id":5,  "name":"Eral-2",          "place_id":"ChIJbwAA0KGMAzsRkQilW5PceeA",   "agm":"Sivaperumal"},
    {"id":6,  "name":"Udankudi",        "place_id":"ChIJPQAAACyEAzsRgjznQ1GLom0",   "agm":"Sivaperumal"},
    {"id":7,  "name":"Tirunelveli-1",   "place_id":"ChIJ2RU2NvQRBDsRq-Fw7IVwx7k",  "agm":"Johnson"},
    {"id":8,  "name":"Valliyur-1",      "place_id":"ChIJcVNk6TtnBDsRBoP4zpExt5k",  "agm":"Johnson"},
    {"id":9,  "name":"Ambasamudram-1",  "place_id":"ChIJ9SGeIi85BDsRZk4QdyW9BSY",  "agm":"Johnson"},
    {"id":10, "name":"Anjugramam-1",    "place_id":"ChIJ4yeJebLtBDsRDceoxujdGyc",   "agm":"Johnson"},
    {"id":11, "name":"Nagercoil",       "place_id":"ChIJe1LZBiTxBDsRJFLjlbgZoIs",  "agm":"Jeeva"},
    {"id":12, "name":"Marthandam",      "place_id":"ChIJcWptCRdVBDsRlJh2q0-rnfY",  "agm":"Jeeva"},
    {"id":13, "name":"Thuckalay-1",     "place_id":"ChIJc9QgEub4BDsRoyDR4Wd6tYA",  "agm":"Jeeva"},
    {"id":14, "name":"Colachel-1",      "place_id":"ChIJgRkBLw39BDsR58D0lwNo5Ts",  "agm":"Jeeva"},
    {"id":15, "name":"Kulasekharam-1",  "place_id":"ChIJw0Ep-kNXBDsRe5ad32jAeAk",  "agm":"Jeeva"},
    {"id":16, "name":"Monday Market",   "place_id":"ChIJTceRGAD5BDsR65i3YNTcYHk",  "agm":"Jeeva"},
    {"id":17, "name":"Karungal-1",      "place_id":"ChIJfTP5ASr_BDsRgsBaeQltkw4",  "agm":"Jeeva"},
    {"id":18, "name":"Kovilpatti",      "place_id":"ChIJHY0o-26yBjsRt7wbXB1pDUE",  "agm":"Seenivasan"},
    {"id":19, "name":"Ramnad",          "place_id":"ChIJNVVVVaGiATsRnunSgOTvbE8",   "agm":"Seenivasan"},
    {"id":20, "name":"Paramakudi",      "place_id":"ChIJ-dgjBzQHATsRf27FWAJgmsA",  "agm":"Seenivasan"},
    {"id":21, "name":"Sayalkudi-1",     "place_id":"ChIJRTqudn9lATsR2fYyMmxlOrw",  "agm":"Seenivasan"},
    {"id":22, "name":"Villathikullam",  "place_id":"ChIJi_wAkwVbATsRtFl3_V5rGrY",  "agm":"Seenivasan"},
    {"id":23, "name":"Sattur-2",        "place_id":"ChIJNVVVVcHKBjsR7xMX97RFn8Q",   "agm":"Seenivasan"},
    {"id":24, "name":"Sankarankovil-1", "place_id":"ChIJE1mKnhSXBjsRKMQ-9JKQf_c",  "agm":"Seenivasan"},
    {"id":25, "name":"Kayathar-1",      "place_id":"ChIJx5ebtUgRBDsRMquPZNUJVpw",  "agm":"Seenivasan"},
    {"id":26, "name":"Thenkasi",        "place_id":"ChIJuaqqquEpBDsRVITw0MMYklc",   "agm":"Muthuselvam"},
    {"id":27, "name":"Thenkasi-2",      "place_id":"ChIJiwqLye6DBjsRo9v1mWXaycI",  "agm":"Muthuselvam"},
    {"id":28, "name":"Surandai-1",      "place_id":"ChIJPb1_eEOdBjsRjL9IVCVJhi8",  "agm":"Muthuselvam"},
    {"id":29, "name":"Puliyankudi-1",   "place_id":"ChIJjZqoc46RBjsRQTGHnNC8xxA",  "agm":"Muthuselvam"},
    {"id":30, "name":"Sengottai-1",     "place_id":"ChIJw3zzKiaBBjsR9KDyGpn1nXU",  "agm":"Muthuselvam"},
    {"id":31, "name":"Rajapalayam",     "place_id":"ChIJW2ot-NDpBjsRMTfMF2IV-xE",  "agm":"Muthuselvam"},
    {"id":32, "name":"Virudhunagar",    "place_id":"ChIJN3jzNJgsATsRCU3nrB5ntKE",  "agm":"Venkadesan"},
    {"id":33, "name":"Virudhunagar-2",  "place_id":"ChIJPezaX7wtATsR9sHhFOG6A1c",  "agm":"Venkadesan"},
    {"id":34, "name":"Aruppukottai",    "place_id":"ChIJy6qqqgYwATsRbcp-hXnoruM",  "agm":"Venkadesan"},
    {"id":35, "name":"Aruppukottai-2",  "place_id":"ChIJY04wY58xATsRuoJSichVQQE",  "agm":"Venkadesan"},
    {"id":36, "name":"Sivakasi",        "place_id":"ChIJI2JvEePOBjsREh8b-x4WF4U",  "agm":"Venkadesan"},
]

IST_OFFSET = timedelta(hours=5, minutes=30)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r",encoding="utf-8") as f:
                data=json.load(f)
            if data.get("branches"): return data
        except: pass
    if os.path.exists(BACKUP_DIR):
        for bf in sorted(os.listdir(BACKUP_DIR),reverse=True):
            if not bf.endswith(".json"): continue
            try:
                with open(os.path.join(BACKUP_DIR,bf),"r",encoding="utf-8") as f:
                    data=json.load(f)
                if data.get("branches"):
                    print(f"[Data] Restored from {bf}")
                    return data
            except: continue
    return {"branches":{},"daily":{},"logs":[]}

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE),exist_ok=True)
    with open(DATA_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)
    os.makedirs(BACKUP_DIR,exist_ok=True)
    today_str=(datetime.utcnow()+IST_OFFSET).strftime("%Y-%m-%d")
    with open(os.path.join(BACKUP_DIR,f"reviews_{today_str}.json"),"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)
    # Clean >90 day backups
    for fname in os.listdir(BACKUP_DIR):
        fpath=os.path.join(BACKUP_DIR,fname)
        try:
            if (datetime.utcnow()-datetime.fromtimestamp(os.path.getmtime(fpath))).days>90:
                os.remove(fpath)
        except: pass

def resolve_date(rel, snap_date_str):
    """Convert Google relative date to YYYY-MM-DD. snap_date is yesterday IST."""
    if not rel: return ""
    r = rel.lower().strip()
    snap = datetime.strptime(snap_date_str, "%Y-%m-%d").date()
    today_ist = (datetime.utcnow() + IST_OFFSET).date()  # actual today (scraper runs at 12AM)

    # Reviews from snap_date (yesterday) show as:
    # "X hours ago" (if scraper runs at 12AM, yesterday's reviews = 1-23h ago)
    # "a day ago" or "1 day ago" for reviews from 2 days ago
    if any(x in r for x in ["just now","second","minute","moment"]):
        return str(today_ist)  # actually today — posted after midnight
    if "hour" in r:
        m = re.search(r"(\d+)", r)
        hours = int(m.group(1)) if m else 1
        if hours <= 23: return str(snap)  # posted yesterday, shows as X hours ago at midnight
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
        return str(today_ist - timedelta(days=n*30))
    if "year" in r:
        m = re.search(r"(\d+)", r)
        n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(days=n*365))
    for fmt in ["%b %d, %Y","%d %B %Y","%B %d, %Y","%d %b %Y","%Y-%m-%d"]:
        try: return datetime.strptime(rel.strip(), fmt).strftime("%Y-%m-%d")
        except: pass
    return ""

async def get_overall_and_rating(page):
    count, stars = None, None
    content = await page.content()
    # Overall count
    for sel in ['[aria-label*="reviews"]','[aria-label*="Reviews"]']:
        els = await page.locator(sel).all()
        for el in els:
            label = await el.get_attribute("aria-label") or ""
            m = re.search(r"([\d,]+)", label)
            if m:
                v = int(m.group(1).replace(",",""))
                if v > 10: count = v; break
        if count: break
    if not count:
        for pat in [r'([\d,]+)\s*reviews?',r'"reviewCount"["\s:]+(\d+)']:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                v = int(m.group(1).replace(",",""))
                if v > 10: count = v; break
    # Stars
    for sel in ['[aria-label*="stars"]','[aria-label*="star rating"]']:
        els = await page.locator(sel).all()
        for el in els:
            label = await el.get_attribute("aria-label") or ""
            m = re.search(r"(\d\.\d)", label)
            if m: stars = float(m.group(1)); break
        if stars: break
    if not stars:
        for pat in [r'"ratingValue":"([\d.]+)"',r'(\d\.\d)\s*(?:stars|out of 5)']:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                try:
                    v = float(m.group(1))
                    if 1.0 <= v <= 5.0: stars = v; break
                except: pass
    return count, stars

async def count_reviews_by_scroll(page, snap_date):
    """
    Click Reviews tab, sort Newest, scroll and count reviews dated snap_date.
    Stop when we hit a review older than snap_date.
    Returns: (count, method)
    """
    # Click Reviews tab
    for sel in ['button[aria-label="Reviews"]','button[data-tab-index="1"]','div[role="tab"]:has-text("Reviews")']:
        try:
            t = await page.wait_for_selector(sel, timeout=4000)
            if t: await t.click(); await page.wait_for_timeout(1500); break
        except: continue

    # Sort by Newest
    for sel in ['button[aria-label="Sort reviews"]','button[data-value="Sort"]','button:has-text("Sort")']:
        try:
            sb = await page.wait_for_selector(sel, timeout=4000)
            if sb:
                await sb.click(); await page.wait_for_timeout(800)
                for ns in ['li[data-index="1"]','li:has-text("Newest")','div[role="menuitemradio"]:has-text("Newest")']:
                    try:
                        n = await page.wait_for_selector(ns, timeout=2000)
                        if n: await n.click(); await page.wait_for_timeout(1500); break
                    except: continue
                break
        except: continue

    seen, count, stop, no_new = set(), 0, False, 0

    while not stop and no_new < 5:
        cards = await page.query_selector_all('div[data-review-id],div.jftiEf')
        new = 0
        for card in cards:
            rid = await card.get_attribute("data-review-id") or id(card)
            if rid in seen: continue
            seen.add(rid); new += 1

            # Get date string
            date_str = ""
            for dsel in ['span.rsqaWe','span[class*="DU9Pgb"]','span[class*="xRkPPb"]']:
                de = await card.query_selector(dsel)
                if de: date_str = (await de.inner_text()).strip(); break

            resolved = resolve_date(date_str, snap_date)

            if resolved == snap_date:
                count += 1
            elif resolved and resolved < snap_date:
                stop = True; break  # older than target date, stop

        no_new = 0 if new else no_new + 1
        if not stop:
            try:
                pane = await page.query_selector('div.m6QErb[tabindex="-1"],div.m6QErb')
                if pane: await pane.evaluate("el=>el.scrollBy(0,2000)")
                else: await page.keyboard.press("End")
            except: pass
            await page.wait_for_timeout(random.randint(600,1200))

    return count

async def scrape_branch(context, branch, snap_date, prev_total, old_stars):
    name = branch["name"]
    page = None
    result = {"live":None,"stars":None,"daily":0,"method":"scroll","error":None}
    try:
        page = await context.new_page()
        url = f"https://www.google.com/maps/place/?q=place_id:{branch['place_id']}"
        await page.goto(url, wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(random.randint(2500,4000))

        live, stars = await get_overall_and_rating(page)
        result["live"] = live
        result["stars"] = stars if stars else old_stars

        if live is None:
            result["error"] = "no count"; return result

        # Try scroll counting
        try:
            count = await count_reviews_by_scroll(page, snap_date)
            result["daily"] = count
            result["method"] = "scroll"
            print(f"  [✓] {name}: overall={live} today={count} ★{result['stars']} (scroll)")
        except Exception as se:
            # Fallback to snapshot diff
            raw = live - prev_total if prev_total else 0
            result["daily"] = max(0, raw)
            result["method"] = "diff"
            print(f"  [!] {name}: scroll failed ({se}), diff={result['daily']} (diff)")

    except Exception as e:
        result["error"] = str(e)
        print(f"  [✗] {name}: {e}")
    finally:
        if page:
            try: await page.close()
            except: pass
    return result

async def run():
    now_ist = datetime.utcnow() + IST_OFFSET
    snap_date = (now_ist.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    run_time = datetime.utcnow().isoformat()

    print(f"=== Sathya Review Scraper (Parallel+Scroll) ===")
    print(f"Snap date  : {snap_date} (reviews posted on this date)")
    print(f"Run time   : {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"Concurrent : {MAX_CONCURRENT}\n")

    data = load_data()
    all_dates_before = sorted([d for d in data.get("daily",{}) if d < snap_date], reverse=True)
    baseline_date = all_dates_before[0] if all_dates_before else None
    baseline_snap = data["daily"].get(baseline_date,{}) if baseline_date else {}

    if baseline_date:
        gap = (datetime.strptime(snap_date,"%Y-%m-%d") - datetime.strptime(baseline_date,"%Y-%m-%d")).days
        if gap > 1:
            print(f"⚠ Gap: baseline is {gap} days old ({baseline_date})")

    if snap_date not in data["daily"]: data["daily"][snap_date] = {}

    snap_month = snap_date[:7]
    same_month = sorted([d for d in data.get("daily",{}) if d.startswith(snap_month) and d < snap_date], reverse=True)
    monthly_snap = data["daily"].get(same_month[0],{}) if same_month else {}

    results = {}; success = 0; failed = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled","--disable-gpu"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            locale="en-IN", viewport={"width":1280,"height":800}
        )
        # Warm up
        try:
            wp = await context.new_page()
            await wp.goto("https://www.google.com/maps",wait_until="domcontentloaded",timeout=20000)
            await wp.wait_for_timeout(1500)
            await wp.close()
            print("[warm-up] ✓")
        except: pass

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def bounded(branch):
            nonlocal success
            async with semaphore:
                bid = str(branch["id"])
                prev_total = baseline_snap.get(bid,{}).get("total_snap",
                             data.get("branches",{}).get(bid,{}).get("overall",0))
                old_stars = data.get("branches",{}).get(bid,{}).get("star_rating",0)
                print(f" [{branch['id']:02d}/36] {branch['name']:<25}", end=" ", flush=True)
                res = await scrape_branch(context, branch, snap_date, prev_total, old_stars)
                if res["error"]:
                    failed.append(branch["name"])
                else:
                    results[bid] = res; success += 1
                await asyncio.sleep(0.5)

        await asyncio.gather(*[bounded(b) for b in BRANCHES])
        await browser.close()

    # Save results
    for b in BRANCHES:
        bid = str(b["id"])
        if bid not in results: continue
        r = results[bid]
        prev_monthly = monthly_snap.get(bid,{}).get("monthly",0)
        monthly = prev_monthly + r["daily"]
        raw_delta = (r["live"] - baseline_snap.get(bid,{}).get("total_snap",
                    data.get("branches",{}).get(bid,{}).get("overall",0)))

        data["daily"][snap_date][bid] = {
            "total_snap":  r["live"],
            "daily_count": r["daily"],
            "raw_delta":   raw_delta,
            "has_deletion":raw_delta < 0,
            "monthly":     monthly,
            "star_rating": r["stars"] or 0,
            "method":      r["method"],
        }
        data["branches"][bid] = {
            "id":b["id"],"name":b["name"],"agm":b["agm"],
            "overall":r["live"],"star_rating":r["stars"] or 0,"monthly":monthly,
        }

    data.setdefault("logs",[]).insert(0,{
        "ran_at":run_time,"snap_date":snap_date,"baseline_date":baseline_date,
        "success":success,"failed":len(failed),"failed_names":failed,
    })
    data["logs"] = data["logs"][:50]
    data["last_updated"] = run_time
    save_data(data)
    print(f"\nDone: {success}/36 for {snap_date}")

if __name__ == "__main__":
    try: asyncio.run(run())
    except Exception as e:
        print(f"\n[FATAL] {e}"); traceback.print_exc(); sys.exit(1)
