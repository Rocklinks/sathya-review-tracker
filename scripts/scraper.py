"""
Fixed Sathya Review Scraper
- Fix 1: Use gl=US to bypass limited view geo-blocking (India IPs get limited view without count)
- Fix 2: Increase wait after load to 8-10s, use wait_until load not networkidle
- Fix 3: Capture count from body inner_text + html + aria, with US locale
- Fix 4: Dual save to both docs/data/reviews.json and data/reviews.json for Pages compat
- Fix 5: Handle DATA_FILE robustly (find repo root even when run from different cwd)
- Fix 6: Re-enable backups, keep MAX_CONCURRENT=3 for stability, add stealth init script
- Fix 7: More detailed logging, distinguish scroll vs delta vs api
"""
import re, json, os, asyncio, traceback, sys, random, shutil
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright

# --- Robust path resolution ---
def find_data_file():
    # Try multiple candidates
    candidates = []
    # 1. Relative to this file (original)
    candidates.append(Path(__file__).resolve().parent / ".." / "docs" / "data" / "reviews.json")
    candidates.append(Path(__file__).resolve().parent / ".." / "data" / "reviews.json")
    # 2. Relative to cwd
    candidates.append(Path.cwd() / "docs" / "data" / "reviews.json")
    candidates.append(Path.cwd() / "data" / "reviews.json")
    # 3. Find git root
    try:
        import subprocess
        root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL).decode().strip()
        if root:
            candidates.append(Path(root) / "docs" / "data" / "reviews.json")
            candidates.append(Path(root) / "data" / "reviews.json")
    except: pass
    # Return first existing parent, else original
    for c in candidates:
        if c.parent.exists():
            return str(c.resolve())
    return str(candidates[0].resolve())

DATA_FILE = find_data_file()
# Dual save: also write to data/reviews.json if docs/data exists
DATA_FILE_ALT = str(Path(DATA_FILE).resolve().parent.parent.parent / "data" / "reviews.json") if "docs/data" in DATA_FILE else None
if DATA_FILE_ALT and Path(DATA_FILE_ALT).parent.exists():
    pass
else:
    # Try alt relative to repo root
    DATA_FILE_ALT = str(Path(__file__).resolve().parent / ".." / "data" / "reviews.json")
BACKUP_DIR = str(Path(DATA_FILE).parent / "backups")
MAX_CONCURRENT = 3
IST_OFFSET = timedelta(hours=5, minutes=30)

BRANCHES = [
    {"id":1, "name":"Tuticorin-1", "place_id":"ChIJ5zJNoJfvAzsR-bJE_3bbNYw", "agm":"Siva"},
    {"id":2, "name":"Tuticorin-2", "place_id":"ChIJH6gY4-PvAzsRJ50skTlx3cs", "agm":"Siva"},
    {"id":3, "name":"Thiruchendur-1", "place_id":"ChIJeXA4vJKRAzsRBovAtv6lMuQ", "agm":"Siva"},
    {"id":4, "name":"Thisayanvilai-1", "place_id":"ChIJVWkvdfh_BDsRdvtimKCLS5Y", "agm":"Siva"},
    {"id":5, "name":"Eral-2", "place_id":"ChIJbwAA0KGMAzsRkQilW5PceeA", "agm":"Siva"},
    {"id":6, "name":"Udankudi", "place_id":"ChIJPQAAACyEAzsRgjznQ1GLom0", "agm":"Siva"},
    {"id":7, "name":"Tirunelveli-1", "place_id":"ChIJ2RU2NvQRBDsRq-Fw7IVwx7k", "agm":"John"},
    {"id":8, "name":"Valliyur-1", "place_id":"ChIJcVNk6TtnBDsRBoP4zpExt5k", "agm":"John"},
    {"id":9, "name":"Ambasamudram-1", "place_id":"ChIJ9SGeIi85BDsRZk4QdyW9BSY", "agm":"John"},
    {"id":10, "name":"Anjugramam-1", "place_id":"ChIJ4yeJebLtBDsRDceoxujdGyc", "agm":"John"},
    {"id":11, "name":"Nagercoil", "place_id":"ChIJe1LZBiTxBDsRJFLjlbgZoIs", "agm":"Jeeva"},
    {"id":12, "name":"Marthandam", "place_id":"ChIJcWptCRdVBDsRlJh2q0-rnfY", "agm":"Jeeva"},
    {"id":13, "name":"Thuckalay-1", "place_id":"ChIJc9QgEub4BDsRoyDR4Wd6tYA", "agm":"Jeeva"},
    {"id":14, "name":"Colachel-1", "place_id":"ChIJgRkBLw39BDsR58D0lwNo5Ts", "agm":"Jeeva"},
    {"id":15, "name":"Kulasekharam-1", "place_id":"ChIJw0Ep-kNXBDsRe5ad32jAeAk", "agm":"Jeeva"},
    {"id":16, "name":"Monday Market", "place_id":"ChIJTceRGAD5BDsR65i3YNTcYHk", "agm":"Jeeva"},
    {"id":17, "name":"Karungal-1", "place_id":"ChIJfTP5ASr_BDsRgsBaeQltkw4", "agm":"Jeeva"},
    {"id":18, "name":"Kovilpatti", "place_id":"ChIJHY0o-26yBjsRt7wbXB1pDUE", "agm":"Seenivasan"},
    {"id":19, "name":"Ramnad", "place_id":"ChIJNVVVVaGiATsRnunSgOTvbE8", "agm":"Seenivasan"},
    {"id":20, "name":"Paramakudi", "place_id":"ChIJ-dgjBzQHATsRf27FWAJgmsA", "agm":"Seenivasan"},
    {"id":21, "name":"Sayalkudi-1", "place_id":"ChIJRTqudn9lATsR2fYyMmxlOrw", "agm":"Seenivasan"},
    {"id":22, "name":"Villathikullam", "place_id":"ChIJi_wAkwVbATsRtFl3_V5rGrY", "agm":"Seenivasan"},
    {"id":23, "name":"Sattur-2", "place_id":"ChIJNVVVVcHKBjsR7xMX97RFn8Q", "agm":"Seenivasan"},
    {"id":24, "name":"Sankarankovil-1", "place_id":"ChIJE1mKnhSXBjsRKMQ-9JKQf_c", "agm":"Seenivasan"},
    {"id":25, "name":"Kayathar-1", "place_id":"ChIJx5ebtUgRBDsRMquPZNUJVpw", "agm":"Seenivasan"},
    {"id":26, "name":"Ramnad-2", "place_id":"ChIJcWPpFSSZATsR1ai6lxBXkAw", "agm":"Seenivasan"},
    {"id":27, "name":"Thenkasi", "place_id":"ChIJuaqqquEpBDsRVITw0MMYklc", "agm":"Muthuselvam"},
    {"id":28, "name":"Thenkasi-2", "place_id":"ChIJiwqLye6DBjsRo9v1mWXaycI", "agm":"Muthuselvam"},
    {"id":29, "name":"Surandai-1", "place_id":"ChIJpb1_eEOdBjsRjL9IVCVJhi8", "agm":"Muthuselvam"},
    {"id":30, "name":"Puliyankudi-1", "place_id":"ChIJjZqoc46RBjsRQTGHnNC8xxA", "agm":"Muthuselvam"},
    {"id":31, "name":"Sengottai-1", "place_id":"ChIJw3zzKiaBBjsR9KDyGpn1nXU", "agm":"Muthuselvam"},
    {"id":32, "name":"Rajapalayam", "place_id":"ChIJW2ot-NDpBjsRMTfMF2IV-xE", "agm":"Muthuselvam"},
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
                print(f" [Data] Loaded {len(data['branches'])} branches from {DATA_FILE}")
                return data
        except Exception as e:
            print(f" [Data] {DATA_FILE} corrupted ({e})")
    # try alt
    if DATA_FILE_ALT and os.path.exists(DATA_FILE_ALT):
        try:
            with open(DATA_FILE_ALT, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("branches"):
                print(f" [Data] Loaded from alt {DATA_FILE_ALT}")
                return data
        except: pass
    print(" [Data] No valid data found — starting fresh.")
    return {"branches": {}, "daily": {}, "logs": []}

def save_data(data):
    for path in [DATA_FILE, DATA_FILE_ALT]:
        if not path: continue
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f" [Data] Saved {path}")
        except Exception as e:
            print(f" [Data] Failed to save {path}: {e}")
    # backups
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        today_str=(datetime.utcnow()+IST_OFFSET).strftime("%Y-%m-%d")
        with open(os.path.join(BACKUP_DIR,f"reviews_{today_str}.json"),"w",encoding="utf-8") as f:
            json.dump(data,f,indent=2,ensure_ascii=False)
        for fname in os.listdir(BACKUP_DIR):
            fpath=os.path.join(BACKUP_DIR,fname)
            try:
                if (datetime.utcnow()-datetime.fromtimestamp(os.path.getmtime(fpath))).days>90:
                    os.remove(fpath)
            except: pass
    except Exception as e:
        print(f" [Backup] {e}")

def resolve_date(rel, snap_date_str):
    if not rel: return ""
    r = rel.lower().strip()
    snap = datetime.strptime(snap_date_str, "%Y-%m-%d").date()
    today_ist = (datetime.utcnow() + IST_OFFSET).date()
    if any(x in r for x in ["just now", "second", "minute", "moment"]):
        return str(today_ist)
    if "hour" in r:
        m = re.search(r"(\d+)", r)
        hours = int(m.group(1)) if m else 1
        if hours <= 23: return str(snap)
        return str(snap - timedelta(days=1))
    if "1 day ago" in r or "a day ago" in r or "yesterday" in r:
        return str(snap - timedelta(days=1))
    if "day" in r:
        m = re.search(r"(\d+)", r); n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(days=n))
    if "week" in r:
        m = re.search(r"(\d+)", r); n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(weeks=n))
    if "month" in r:
        m = re.search(r"(\d+)", r); n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(days=n * 30))
    if "year" in r:
        m = re.search(r"(\d+)", r); n = int(m.group(1)) if m else 1
        return str(today_ist - timedelta(days=n * 365))
    for fmt in ["%b %d, %Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y","%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y","%b %d %Y", "%d %b %Y"]:
        try: return datetime.strptime(rel.strip(), fmt).strftime("%Y-%m-%d")
        except: pass
    if "edited" in r:
        cleaned = re.sub(r'^edited\s+', '', r).strip()
        return resolve_date(cleaned, snap_date_str)
    return ""

async def _get_overall_and_rating(page):
    count, stars = None, None
    # try body inner_text first (most reliable after US gl fix)
    try:
        body = await page.locator("body").inner_text(timeout=6000)
        # look for "7,812 reviews" pattern
        for pat in [r'([\d,]+)\s*reviews', r'([\d,]+)\s*Google\s+reviews']:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                v = int(m.group(1).replace(",",""))
                if v > 5:
                    count = v; break
        # stars in body like "4.9 |" or "4.9★"
        m = re.search(r'(\d\.\d)\s*[★|]', body)
        if m:
            try:
                v=float(m.group(1))
                if 1.0 <= v <= 5.0: stars=v
            except: pass
        if count and stars:
            return count, stars
    except: pass
    # aria labels
    try:
        aria_loc = page.locator("[aria-label]")
        n = await aria_loc.count()
        labs=[]
        for i in range(min(n, 300)):
            try:
                al = await aria_loc.nth(i).get_attribute("aria-label")
                if al: labs.append(al)
            except: continue
        aria_text="\n".join(labs)
        if count is None:
            for lbl in labs:
                m=re.search(r'([\d,]+)\s*reviews?', lbl, re.I)
                if m:
                    v=int(m.group(1).replace(",",""))
                    if v>5: count=v; break
        if stars is None:
            for lbl in labs:
                m=re.search(r'(\d\.\d)\s*stars?', lbl, re.I)
                if m:
                    try:
                        v=float(m.group(1))
                        if 1.0<=v<=5.0: stars=v; break
                    except: pass
    except: pass
    # html fallback
    if count is None or stars is None:
        try:
            html = await page.content()
            if count is None:
                for pat in [r'"userRatingCount"[:\s,]*(\d+)', r'"reviewCount"[:\s,]*(\d+)', r'([\d,]+)\s*reviews']:
                    m=re.search(pat, html, re.I)
                    if m:
                        v=int(m.group(1).replace(",",""))
                        if v>5: count=v; break
            if stars is None:
                for pat in [r'"ratingValue"[:\s,]*"?([\d.]+)"?', r'(\d\.\d)\s*stars']:
                    m=re.search(pat, html, re.I)
                    if m:
                        try:
                            v=float(m.group(1))
                            if 1.0<=v<=5.0: stars=v; break
                        except: pass
        except: pass
    return count, stars

async def _count_reviews_by_scroll(page, snap_date):
    # Click Reviews tab if present (US locale gives Overview|Reviews)
    for sel in ['button[aria-label="Reviews"]','button[aria-label*="Reviews"]','div[role="tab"]:has-text("Reviews")','button[data-tab-index="1"]','div[role="tab"][data-tab-index="1"]']:
        try:
            loc=page.locator(sel).first
            if await loc.count():
                await loc.click(timeout=4000)
                await page.wait_for_timeout(3000)
                break
        except: continue
    # Sort Newest
    for sel in ['button[aria-label="Sort reviews"]','button[aria-label*="Sort"]','button:has-text("Sort")']:
        try:
            loc=page.locator(sel).first
            if await loc.count():
                await loc.click(timeout=3000)
                await page.wait_for_timeout(1000)
                for ns in ['li[data-index="1"]','div[role="menuitemradio"]:has-text("Newest")','li:has-text("Newest")']:
                    try:
                        n=page.locator(ns).first
                        if await n.count():
                            await n.click(timeout=2000)
                            await page.wait_for_timeout(2000)
                            break
                    except: continue
                break
        except: continue
    # Find scroll panel
    panel=None
    for psel in ['div[role="feed"]','div.m6QErb[aria-label]','div.m6QErb']:
        try:
            p=page.locator(psel).first
            if await p.count(): panel=p; break
        except: continue
    for _ in range(2):
        try: await page.keyboard.press("End")
        except: pass
        await page.wait_for_timeout(1200)

    seen=set(); count=0; stop=False; no_new=0; attempts=0
    CARD_SELS=['div[data-review-id]','div.jftiEf']
    DATE_RE=re.compile(r'(?:\d+\s+(?:hour|minute|second|day|week|month|year)s?\s+ago|a\s+(?:day|week|month|year)\s+ago|yesterday|just\s+now|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})', re.I)
    while not stop and no_new < 7 and attempts < 22:
        attempts+=1
        cards=[]
        for cs in CARD_SELS:
            try:
                loc=page.locator(cs)
                n=await loc.count()
                for i in range(n): cards.append(loc.nth(i))
            except: pass
        uniq=[]
        seen_ids=set()
        for c in cards:
            try: rid=await c.get_attribute("data-review-id")
            except: rid=None
            rid=rid or f"id-{id(c)}"
            if rid not in seen_ids: seen_ids.add(rid); uniq.append(c)
        new=0
        for card in uniq:
            try: rid=await card.get_attribute("data-review-id")
            except: rid=None
            rid=rid or f"id-{id(card)}"
            if rid in seen: continue
            seen.add(rid); new+=1
            date_str=""
            try:
                txt=await card.inner_text(timeout=2000)
                for line in txt.split("\n"):
                    line=line.strip()
                    if DATE_RE.search(line) and not re.match(r'^[\d.★\s]+$', line):
                        date_str=line; break
            except: pass
            resolved=resolve_date(date_str, snap_date)
            if resolved==snap_date: count+=1
            elif resolved and resolved < snap_date: stop=True; break
        no_new=0 if new else no_new+1
        if not stop:
            scrolled=False
            if panel:
                try:
                    box=await panel.bounding_box()
                    if box:
                        await page.mouse.move(box["x"]+box["width"]/2, box["y"]+box["height"]/2)
                        await page.mouse.wheel(0, box["height"]*1.8)
                        scrolled=True
                except: pass
            if not scrolled:
                try: await page.keyboard.press("End")
                except: pass
            await page.wait_for_timeout(random.randint(900,1400))
    return count

async def scrape_branch(context, branch, snap_date, old_stars, data):
    name=branch["name"]; place_id=branch["place_id"]
    page=None
    result={"live":None,"stars":None,"daily":0,"method":"scroll","error":None}
    for attempt in range(1,4):
        result["error"]=None
        try:
            if attempt>1:
                await asyncio.sleep(attempt*2+random.randint(1,3))
            page=await context.new_page()
            # Capture preview responses for fallback
            captured=[]
            async def on_response(r):
                try:
                    url=r.url
                    if any(k in url for k in ['/maps/preview/place','/maps/rpc/listugc','/maps/preview/review']):
                        try:
                            txt=await r.text()
                            if len(txt)>200: captured.append(txt)
                        except: pass
                except: pass
            page.on("response", on_response)
            url=f"https://www.google.com/maps/place/?q=place_id:{place_id}&hl=en&gl=US"
            await page.goto(url, wait_until="load", timeout=45000)
            await page.wait_for_timeout(9000)
            # consent
            for sel in ['#L2AGLb','button:has-text("Accept all")','button:has-text("I agree")']:
                try:
                    btn=page.locator(sel).first
                    if await btn.count():
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        await page.goto(url, wait_until="load", timeout=45000)
                        await page.wait_for_timeout(8000)
                        break
                except: pass
            # tier 1: captured preview
            if captured:
                txt="\n".join(captured)
                for pat in [r'"userRatingCount"[:\s,]*(\d+)', r'"reviewCount"[:\s,]*(\d+)', r'"ratingCount"[:\s,]*(\d+)']:
                    m=re.search(pat, txt)
                    if m:
                        v=int(m.group(1))
                        if v>0: result["live"]=v; break
                for pat in [r'"ratingValue"[:\s,]*"?([\d.]+)"?', r'"averageRating"[:\s,]*"?([\d.]+)"?']:
                    m=re.search(pat, txt)
                    if m:
                        try:
                            v=float(m.group(1))
                            if 1.0<=v<=5.0: result["stars"]=v; break
                        except: pass
            # tier 2: DOM
            if result["live"] is None:
                live, stars = await _get_overall_and_rating(page)
                result["live"]=live
                if stars: result["stars"]=stars
            if not result["stars"]: result["stars"]=old_stars
            if result["live"] is None:
                # try scroll to get count from header after clicking Reviews
                try:
                    # click Reviews to expose count
                    for sel in ['div[role="tab"]:has-text("Reviews")','button[aria-label*="Reviews"]']:
                        try:
                            loc=page.locator(sel).first
                            if await loc.count():
                                await loc.click(timeout=3000)
                                await page.wait_for_timeout(3000)
                                break
                        except: pass
                    live2, _ = await _get_overall_and_rating(page)
                    if live2: result["live"]=live2; result["method"]="scroll-header"
                except: pass
            if result["live"] is None:
                result["error"]="all methods failed (limited view or bot check)"
                continue
            # daily count via scroll
            try:
                daily = await _count_reviews_by_scroll(page, snap_date)
                result["daily"]=daily
                result["method"]="scroll" if result["method"]=="scroll" else result["method"]
            except Exception as e:
                result["daily"]=0
            if result["method"]=="scroll": pass
            else: result["method"]="api"
            break
        except Exception as e:
            result["error"]=str(e)
        finally:
            if page:
                try: await page.close()
                except: pass
            page=None
    return result

async def run():
    from datetime import timezone
    now_utc=datetime.now(timezone.utc)
    now_ist=now_utc+IST_OFFSET
    snap_date=(now_ist.date()-timedelta(days=1)).strftime("%Y-%m-%d")
    run_time=now_utc.isoformat()
    print(f"=== Sathya Review Scraper (FIXED) ===")
    print(f"DATA_FILE   : {DATA_FILE}")
    print(f"DATA_ALT    : {DATA_FILE_ALT}")
    print(f"Snap date   : {snap_date}")
    print(f"Run time IST: {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"Concurrency : {MAX_CONCURRENT}")
    print(f"Branches    : {TOTAL_BRANCHES}\n")
    data=load_data()
    all_dates=sorted(data.get("daily",{}).keys())
    dates_before=[d for d in all_dates if d < snap_date]
    baseline=dates_before[-1] if dates_before else None
    baseline_snap=data["daily"].get(baseline,{}) if baseline else {}
    if baseline:
        gap=(datetime.strptime(snap_date,"%Y-%m-%d")-datetime.strptime(baseline,"%Y-%m-%d")).days
        if gap>1: print(f"⚠ Gap {gap} days ({baseline}→{snap_date}) daily will be {gap}-day sum")
    if snap_date not in data["daily"]: data["daily"][snap_date]={}
    snap_month=snap_date[:7]
    month_before=sorted([d for d in all_dates if d.startswith(snap_month) and d < snap_date])
    results={}; success=0; failed=[]
    async with async_playwright() as p:
        import shutil as _shutil, glob as _glob
        from pathlib import Path as _Path
        brave=_shutil.which("brave") or _shutil.which("brave-browser") or _shutil.which("google-chrome") or _shutil.which("chromium")
        if not brave:
            cands=_glob.glob(str(_Path.home()/".cache/ms-playwright/chromium-*/chrome-linux/chrome"))
            if not cands: cands=_glob.glob(str(_Path.home()/".cache/ms-playwright/chromium-*/chrome-linux/chromium"))
            if cands: brave=cands[0]
        if not brave:
            print("[FATAL] No browser. Run: playwright install chromium"); sys.exit(1)
        browser=await p.chromium.launch(executable_path=brave, headless=True, args=["--no-sandbox","--disable-gpu","--disable-dev-shm-usage","--disable-blink-features=AutomationControlled"])
        context=await browser.new_context(locale="en-US", viewport={"width":1366,"height":768}, extra_http_headers={"Accept-Language":"en-US,en;q=0.9"}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); window.chrome = { runtime: {} };")
        print(f" [browser] {brave} ✓")
        try:
            wp=await context.new_page()
            await wp.goto("https://www.google.com/maps?hl=en&gl=US", wait_until="load", timeout=20000)
            await wp.wait_for_timeout(2000)
            for sel in ['#L2AGLb','button:has-text("Accept all")']:
                try:
                    btn=wp.locator(sel).first
                    if await btn.count(): await btn.click(); await wp.wait_for_timeout(1000); break
                except: pass
            await wp.close()
            print(" [warm-up] ✓")
        except: print(" [warm-up] skip")
        sem=asyncio.Semaphore(MAX_CONCURRENT)
        async def bounded(b):
            nonlocal success
            async with sem:
                bid=str(b["id"]); old=data.get("branches",{}).get(bid,{}).get("star_rating",0)
                prev=baseline_snap.get(bid,{}).get("total_snap", data.get("branches",{}).get(bid,{}).get("overall",0))
                print(f" [{b['id']:02d}/{TOTAL_BRANCHES}] {b['name']:<25}", end=" ", flush=True)
                try: res=await scrape_branch(context, b, snap_date, old, data)
                except Exception as e: res={"live":None,"stars":None,"daily":0,"method":"error","error":str(e)}
                if res["error"]:
                    failed.append(b["name"]); print(f"→ FAILED: {res['error']} ✗")
                else:
                    results[bid]=res
                    delta=res["live"]-prev if res["live"] and prev and res["live"]>prev else res["daily"]
                    print(f"→ {res['live']:,} total +{delta} new {res['stars']}★ ✓ ({res['method']})")
                    success+=1
                await asyncio.sleep(random.randint(1,3))
        await asyncio.gather(*[bounded(b) for b in BRANCHES])
        await browser.close()
    for b in BRANCHES:
        bid=str(b["id"])
        if bid not in results: continue
        r=results[bid]
        prev=baseline_snap.get(bid,{}).get("total_snap", data["branches"].get(bid,{}).get("overall",0))
        if r["daily"]>0: daily=r["daily"]
        elif r["live"] and prev and r["live"]>prev: daily=r["live"]-prev; r["method"]="delta"
        else: daily=max(0, r["daily"])
        month_sum=sum((data["daily"].get(d,{}).get(bid,{}).get("daily_count",0) for d in month_before),0)
        monthly=month_sum+daily
        data["daily"][snap_date][bid]={"total_snap":r["live"],"daily_count":daily,"monthly":monthly,"star_rating":r["stars"] or 0,"method":r["method"]}
        data["branches"][bid]={"id":b["id"],"name":b["name"],"agm":b["agm"],"overall":r["live"],"star_rating":r["stars"] or 0,"monthly":monthly}
    data.setdefault("logs",[]).insert(0,{"ran_at":run_time,"snap_date":snap_date,"baseline_date":baseline,"success":success,"failed":len(failed),"failed_names":failed})
    data["logs"]=data["logs"][:50]
    data["last_updated"]=run_time
    save_data(data)
    print(f"\nDone: {success}/{TOTAL_BRANCHES} for {snap_date} (failed: {failed})")

if __name__=="__main__":
    try: asyncio.run(run())
    except Exception as e:
        print(f"\n[FATAL] {e}"); traceback.print_exc(); sys.exit(1)
