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
    {"id":1,  "name":"Tirunelveli-1",   "place_id":"ChIJ2RU2NvQRBDsRq-Fw7IVwx7k", "agm":"John"},
    {"id":2,  "name":"Tuticorin-1",     "place_id":"ChIJ5zJNoJfvAzsR-bJE_3bbNYw",  "agm":"Siva"},
    {"id":3,  "name":"Thenkasi",        "place_id":"ChIJuaqqquEpBDsRVITw0MMYklc",  "agm":"Muthuselvam"},
    {"id":4,  "name":"Tuticorin-2",     "place_id":"ChIJH6gY4-PvAzsRJ50skTlx3cs",  "agm":"Siva"},
    {"id":5,  "name":"Thenkasi-2",      "place_id":"ChIJiwqLye6DBjsRo9v1mWXaycI",  "agm":"Muthuselvam"},
    {"id":6,  "name":"Ramnad",          "place_id":"ChIJNVVVVaGiATsRnunSgOTvbE8",  "agm":"Seenivasan"},
    {"id":7,  "name":"Nagercoil",       "place_id":"ChIJe1LZBiTxBDsRJFLjlbgZoIs",  "agm":"Jeeva"},
    {"id":8,  "name":"Rajapalayam",     "place_id":"ChIJW2ot-NDpBjsRMTfMF2IV-xE",  "agm":"Muthuselvam"},
    {"id":9,  "name":"Thiruchendur-1",  "place_id":"ChIJeXA4vJKRAzsRBovAtv6lMuQ",  "agm":"Siva"},
    {"id":10, "name":"Virudhunagar-2",  "place_id":"ChIJPezaX7wtATsR9sHhFOG6A1c",  "agm":"Venkatesh"},
    {"id":11, "name":"Aruppukottai",    "place_id":"ChIJy6qqqgYwATsRbcp-hXnoruM",   "agm":"Venkatesh"},
    {"id":12, "name":"Surandai-1",      "place_id":"ChIJPb1_eEOdBjsRjL9IVCVJhi8",  "agm":"Muthuselvam"},
    {"id":13, "name":"Kovilpatti",      "place_id":"ChIJHY0o-26yBjsRt7wbXB1pDUE",  "agm":"Seenivasan"},
    {"id":14, "name":"Puliyankudi-1",   "place_id":"ChIJjZqoc46RBjsRQTGHnNC8xxA",  "agm":"Muthuselvam"},
    {"id":15, "name":"Udankudi",        "place_id":"ChIJPQAAACyEAzsRgjznQ1GLom0",   "agm":"Siva"},
    {"id":16, "name":"Aruppukottai-2",  "place_id":"ChIJY04wY58xATsRuoJSichVQQE",  "agm":"Venkatesh"},
    {"id":17, "name":"Sivakasi",        "place_id":"ChIJI2JvEePOBjsREh8b-x4WF4U",  "agm":"Venkatesh"},
    {"id":18, "name":"Kulasekharam-1",  "place_id":"ChIJw0Ep-kNXBDsRe5ad32jAeAk",  "agm":"Jeeva"},
    {"id":19, "name":"Sattur-2",        "place_id":"ChIJNVVVVcHKBjsR7xMX97RFn8Q",  "agm":"Seenivasan"},
    {"id":20, "name":"Ambasamudram-1",  "place_id":"ChIJ9SGeIi85BDsRZk4QdyW9BSY",  "agm":"John"},
    {"id":21, "name":"Anjugramam-1",    "place_id":"ChIJ4yeJebLtBDsRDceoxujdGyc",  "agm":"John"},
    {"id":22, "name":"Eral-2",          "place_id":"ChIJbwAA0KGMAzsRkQilW5PceeA",   "agm":"Siva"},
    {"id":23, "name":"Kayathar-1",      "place_id":"ChIJx5ebtUgRBDsRMquPZNUJVpw",  "agm":"Seenivasan"},
    {"id":24, "name":"Virudhunagar",    "place_id":"ChIJN3jzNJgsATsRCU3nrB5ntKE",  "agm":"Venkatesh"},
    {"id":25, "name":"Thuckalay-1",     "place_id":"ChIJc9QgEub4BDsRoyDR4Wd6tYA",  "agm":"Jeeva"},
    {"id":26, "name":"Sayalkudi-1",     "place_id":"ChIJRTqudn9lATsR2fYyMmxlOrw",  "agm":"Seenivasan"},
    {"id":27, "name":"Valliyur-1",      "place_id":"ChIJcVNk6TtnBDsRBoP4zpExt5k",  "agm":"John"},
    {"id":28, "name":"Marthandam",      "place_id":"ChIJcWptCRdVBDsRlJh2q0-rnfY",  "agm":"Jeeva"},
    {"id":29, "name":"Sengottai-1",     "place_id":"ChIJw3zzKiaBBjsR9KDyGpn1nXU",  "agm":"Muthuselvam"},
    {"id":30, "name":"Karungal-1",      "place_id":"ChIJfTP5ASr_BDsRgsBaeQltkw4",  "agm":"Jeeva"},
    {"id":31, "name":"Colachel-1",      "place_id":"ChIJgRkBLw39BDsR58D0lwNo5Ts",  "agm":"Venkatesh"},
    {"id":32, "name":"Sankarankovil-1", "place_id":"ChIJE1mKnhSXBjsRKMQ-9JKQf_c", "agm":"Seenivasan"},
    {"id":33, "name":"Thisayanvilai-1", "place_id":"ChIJVWkvdfh_BDsRdvtimKCLS5Y",  "agm":"Siva"},
    {"id":34, "name":"Paramakudi",      "place_id":"ChIJ-dgjBzQHATsRf27FWAJgmsA",  "agm":"Seenivasan"},
    {"id":35, "name":"Monday Market",   "place_id":"ChIJTceRGAD5BDsR65i3YNTcYHk",  "agm":"Jeeva"},
    {"id":36, "name":"Villathikullam",  "place_id":"ChIJi_wAkwVbATsRtFl3_V5rGrY",  "agm":"Seenivasan"},
]


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"branches": {}, "daily": {}, "logs": []}


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def scrape_place(page, place_id, name):
    url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    count, stars = None, None
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        for sel in ['[aria-label*="reviews"]', '[aria-label*="Reviews"]']:
            for el in page.locator(sel).all():
                label = el.get_attribute("aria-label") or ""
                m = re.search(r"([\d,]+)", label)
                if m:
                    count = int(m.group(1).replace(",", ""))
                    break
            if count:
                break

        for sel in ['[aria-label*="stars"]', 'span[aria-label*="stars"]']:
            for el in page.locator(sel).all():
                label = el.get_attribute("aria-label") or ""
                m = re.search(r"(\d\.\d)", label)
                if m:
                    stars = float(m.group(1))
                    break
            if stars:
                break

        content = page.content()
        if not count:
            for pat in [r'([\d,]+)\s*reviews?', r'"reviewCount"["\s:]+(\d+)']:
                m = re.search(pat, content, re.IGNORECASE)
                if m:
                    v = int(m.group(1).replace(",", ""))
                    if v > 10:
                        count = v
                        break
        if not stars:
            for pat in [r'"ratingValue":"([\d.]+)"', r'(\d\.\d)\s*(?:stars|out of 5)']:
                m = re.search(pat, content, re.IGNORECASE)
                if m:
                    try:
                        v = float(m.group(1))
                        if 1.0 <= v <= 5.0:
                            stars = v
                            break
                    except ValueError:
                        pass
    except Exception as e:
        print(f"  ERROR {name}: {e}")
    return count, stars


def run():
    snap_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    run_time  = datetime.utcnow().isoformat()

    print(f"=== Sathya Review Scraper ===")
    print(f"Snap date : {snap_date}")
    print(f"Run time  : {run_time} UTC")
    print()

    data    = load_data()
    success = 0
    failed  = []

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

        for b in BRANCHES:
            bid  = str(b["id"])
            name = b["name"]
            print(f"  [{b['id']:02d}/36] {name:<25}", end=" ", flush=True)

            live, stars = scrape_place(page, b["place_id"], name)
            prev_total  = data["branches"].get(bid, {}).get("overall", 0)
            daily       = max(0, live - prev_total) if live else 0

            if live is not None:
                data["branches"][bid] = {
                    "id":          b["id"],
                    "name":        b["name"],
                    "agm":         b["agm"],
                    "overall":     live,
                    "star_rating": stars or data["branches"].get(bid, {}).get("star_rating", 0),
                }
                if snap_date not in data["daily"]:
                    data["daily"][snap_date] = {}
                data["daily"][snap_date][bid] = {
                    "daily_count": daily,
                    "total_snap":  live,
                    "star_rating": stars or 0,
                }
                year_month = snap_date[:7]
                monthly = sum(
                    data["daily"].get(d, {}).get(bid, {}).get("daily_count", 0)
                    for d in data["daily"] if d.startswith(year_month)
                )
                data["branches"][bid]["monthly"] = monthly
                stars_str = f"{stars}★" if stars else "—"
                print(f"→ {live:,} total  +{daily} new  {stars_str}  ✓")
                success += 1
            else:
                failed.append(name)
                print("→ FAILED ✗")

            time.sleep(1.5)

        browser.close()

    data.setdefault("logs", []).insert(0, {
        "ran_at":       run_time,
        "snap_date":    snap_date,
        "success":      success,
        "failed":       len(failed),
        "failed_names": failed,
    })
    data["logs"]         = data["logs"][:50]
    data["last_updated"] = run_time

    save_data(data)
    print(f"\nDone: {success}/36 saved to data/reviews.json")


if __name__ == "__main__":
    run()
