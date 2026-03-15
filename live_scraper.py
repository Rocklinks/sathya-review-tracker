#!/usr/bin/env python3
"""
live_scraper.py
===============
Local server that sathya_jupyter.html talks to when you click ▶.
Has NOTHING to do with scraper.py or reviews.json.

Start it:
  Windows  : double-click start.bat
  Mac/Linux: ./start.sh

Then open sathya_jupyter.html in your browser and click ▶ on any cell.
It scrapes Google Maps live using Playwright and streams results back.
"""

import re, time, json, threading, sys, os, queue
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

PORT = int(os.environ.get("PORT", 5000))

# ── Branch data ───────────────────────────────────────────────────────────────
BRANCHES = [
    {"name":"Kovilpatti",      "place_id":"ChIJHY0o-26yBjsRt7wbXB1pDUE", "agm":"Seenivasan"},
    {"name":"Ramnad",          "place_id":"ChIJNVVVVaGiATsRnunSgOTvbE8", "agm":"Seenivasan"},
    {"name":"Paramakudi",      "place_id":"ChIJ-dgjBzQHATsRf27FWAJgmsA", "agm":"Seenivasan"},
    {"name":"Sayalkudi-1",     "place_id":"ChIJRTqudn9lATsR2fYyMmxlOrw", "agm":"Seenivasan"},
    {"name":"Villathikullam",  "place_id":"ChIJi_wAkwVbATsRtFl3_V5rGrY", "agm":"Seenivasan"},
    {"name":"Sattur-2",        "place_id":"ChIJNVVVVcHKBjsR7xMX97RFn8Q", "agm":"Seenivasan"},
    {"name":"Sankarankovil-1", "place_id":"ChIJE1mKnhSXBjsRKMQ-9JKQf_c","agm":"Seenivasan"},
    {"name":"Kayathar-1",      "place_id":"ChIJx5ebtUgRBDsRMquPZNUJVpw", "agm":"Seenivasan"},

    {"name":"Nagercoil",       "place_id":"ChIJe1LZBiTxBDsRJFLjlbgZoIs", "agm":"Jeeva"},
    {"name":"Marthandam",      "place_id":"ChIJcWptCRdVBDsRlJh2q0-rnfY", "agm":"Jeeva"},
    {"name":"Thuckalay-1",     "place_id":"ChIJc9QgEub4BDsRoyDR4Wd6tYA", "agm":"Jeeva"},
    {"name":"Colachel-1",      "place_id":"ChIJgRkBLw39BDsR58D0lwNo5Ts", "agm":"Jeeva"},
    {"name":"Kulasekharam-1",  "place_id":"ChIJw0Ep-kNXBDsRe5ad32jAeAk", "agm":"Jeeva"},
    {"name":"Monday Market",   "place_id":"ChIJTceRGAD5BDsR65i3YNTcYHk", "agm":"Jeeva"},
    {"name":"Karungal-1",      "place_id":"ChIJfTP5ASr_BDsRgsBaeQltkw4", "agm":"Jeeva"},

    {"name":"Thenkasi",        "place_id":"ChIJuaqqquEpBDsRVITw0MMYklc", "agm":"Muthuselvam"},
    {"name":"Thenkasi-2",      "place_id":"ChIJiwqLye6DBjsRo9v1mWXaycI", "agm":"Muthuselvam"},
    {"name":"Surandai-1",      "place_id":"ChIJPb1_eEOdBjsRjL9IVCVJhi8", "agm":"Muthuselvam"},
    {"name":"Puliyankudi-1",   "place_id":"ChIJjZqoc46RBjsRQTGHnNC8xxA", "agm":"Muthuselvam"},
    {"name":"Sengottai-1",     "place_id":"ChIJw3zzKiaBBjsR9KDyGpn1nXU", "agm":"Muthuselvam"},
    {"name":"Rajapalayam",     "place_id":"ChIJW2ot-NDpBjsRMTfMF2IV-xE", "agm":"Muthuselvam"},

    {"name":"Tirunelveli-1",   "place_id":"ChIJ2RU2NvQRBDsRq-Fw7IVwx7k", "agm":"John"},
    {"name":"Valliyur-1",      "place_id":"ChIJcVNk6TtnBDsRBoP4zpExt5k", "agm":"John"},
    {"name":"Ambasamudram-1",  "place_id":"ChIJ9SGeIi85BDsRZk4QdyW9BSY", "agm":"John"},
    {"name":"Anjugramam-1",    "place_id":"ChIJ4yeJebLtBDsRDceoxujdGyc", "agm":"John"},

    {"name":"Tuticorin-1",     "place_id":"ChIJ5zJNoJfvAzsR-bJE_3bbNYw", "agm":"Siva"},
    {"name":"Tuticorin-2",     "place_id":"ChIJH6gY4-PvAzsRJ50skTlx3cs", "agm":"Siva"},
    {"name":"Thiruchendur-1",  "place_id":"ChIJeXA4vJKRAzsRBovAtv6lMuQ", "agm":"Siva"},
    {"name":"Thisayanvilai-1", "place_id":"ChIJVWkvdfh_BDsRdvtimKCLS5Y", "agm":"Siva"},
    {"name":"Eral-2",          "place_id":"ChIJbwAA0KGMAzsRkQilW5PceeA",  "agm":"Siva"},
    {"name":"Udankudi",        "place_id":"ChIJPQAAACyEAzsRgjznQ1GLom0",  "agm":"Siva"},

    {"name":"Virudhunagar",    "place_id":"ChIJN3jzNJgsATsRCU3nrB5ntKE", "agm":"Venkatesh"},
    {"name":"Virudhunagar-2",  "place_id":"ChIJPezaX7wtATsR9sHhFOG6A1c", "agm":"Venkatesh"},
    {"name":"Aruppukottai",    "place_id":"ChIJy6qqqgYwATsRbcp-hXnoruM",  "agm":"Venkatesh"},
    {"name":"Aruppukottai-2",  "place_id":"ChIJY04wY58xATsRuoJSichVQQE", "agm":"Venkatesh"},
    {"name":"Sivakasi",        "place_id":"ChIJI2JvEePOBjsREh8b-x4WF4U", "agm":"Venkatesh"},
]

VALID_AGMS = {b["agm"] for b in BRANCHES}


# ── Playwright scraper ────────────────────────────────────────────────────────

def _scrape_one(page, place_id, wait_ms=4000):
    """Scrape one place. Returns (count, stars) — either may be None."""
    page.goto(
        f"https://www.google.com/maps/place/?q=place_id:{place_id}",
        wait_until="domcontentloaded", timeout=35000
    )
    page.wait_for_timeout(wait_ms)

    count, stars = None, None

    for sel in ['[aria-label*="reviews"]', '[aria-label*="Reviews"]',
                'button[jsaction*="review"]']:
        try:
            for el in page.locator(sel).all():
                lbl = el.get_attribute("aria-label") or ""
                m = re.search(r"([\d,]+)", lbl)
                if m:
                    v = int(m.group(1).replace(",", ""))
                    if v > 0:
                        count = v
                        break
        except Exception:
            pass
        if count:
            break

    for sel in ['[aria-label*="stars"]', 'span[aria-label*="stars"]',
                '[aria-label*="star rating"]']:
        try:
            for el in page.locator(sel).all():
                lbl = el.get_attribute("aria-label") or ""
                m = re.search(r"(\d[\.,]\d)", lbl)
                if m:
                    stars = float(m.group(1).replace(",", "."))
                    break
        except Exception:
            pass
        if stars:
            break

    # fallback from page source
    if not count or not stars:
        try:
            src = page.content()
            if not count:
                for pat in [r'([\d,]+)\s*reviews?',
                            r'"reviewCount"["\s:]+(\d+)']:
                    m = re.search(pat, src, re.IGNORECASE)
                    if m:
                        v = int(m.group(1).replace(",", ""))
                        if v > 5:
                            count = v
                            break
            if not stars:
                for pat in [r'"ratingValue"\s*:\s*"?([\d.]+)',
                            r'(\d\.\d)\s*(?:stars|out of 5)']:
                    m = re.search(pat, src, re.IGNORECASE)
                    if m:
                        try:
                            v = float(m.group(1))
                            if 1.0 <= v <= 5.0:
                                stars = round(v, 1)
                                break
                        except ValueError:
                            pass
        except Exception:
            pass

    return count, stars


def scrape_agm(agm_name, q):
    """
    Scrape all branches for one AGM.
    Puts JSON event strings into q.
    Puts None when finished (sentinel).
    """
    branches = [b for b in BRANCHES if b["agm"] == agm_name]

    def ev(etype, **kw):
        kw["event"] = etype
        q.put(json.dumps(kw))

    ev("log", text="=" * 54, type="muted")
    ev("log", text="  SATHYA AGENCIES — Live Scraper", type="bold")
    ev("log", text=f"  AGM    : {agm_name}", type="muted")
    ev("log", text=f"  Branches: {len(branches)}", type="muted")
    ev("log", text="=" * 54, type="muted")
    ev("log", text="", type="normal")
    ev("log", text="  🌐 Launching Chromium...", type="accent")

    results = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled",
                      "--disable-gpu"]
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-IN",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()

            # warm-up
            try:
                page.goto("https://www.google.com/maps",
                          wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(2000)
                ev("log", text="  ✓ Browser ready\n", type="success")
            except Exception:
                ev("log", text="  ⚠ Warm-up skipped\n", type="muted")

            for i, b in enumerate(branches):
                name = b["name"]
                pad  = str(i + 1).zfill(2)
                ev("log",
                   text=f"  [{pad}/{len(branches)}] {name:<22} → fetching...",
                   type="normal")

                count, stars = None, None
                ok = False

                for attempt in range(1, 4):
                    try:
                        if attempt > 1:
                            ev("log",
                               text=f"    ↺ Retry {attempt}/3...",
                               type="muted")
                            time.sleep(3)
                            try:
                                page.goto("about:blank", timeout=5000)
                            except Exception:
                                pass
                            time.sleep(1)

                        wait = 4000 + (attempt - 1) * 2000
                        count, stars = _scrape_one(page, b["place_id"], wait_ms=wait)

                        if count:
                            ok = True
                            break

                        ev("log",
                           text=f"    ⚠ Attempt {attempt}: no data",
                           type="muted")
                    except Exception as e:
                        ev("log",
                           text=f"    ⚠ Attempt {attempt}: {str(e)[:60]}",
                           type="muted")

                if ok:
                    star_str = f"{stars}⭐" if stars else "—"
                    ev("log",
                       text=f"  [{pad}/{len(branches)}] {name:<22} → {count:,} reviews  {star_str}  ✓",
                       type="success")
                    results.append({
                        "name": name, "agm": agm_name,
                        "reviews": count, "stars": stars or 0, "status": "ok"
                    })
                else:
                    ev("log",
                       text=f"  [{pad}/{len(branches)}] {name:<22} → FAILED ✗",
                       type="error")
                    results.append({
                        "name": name, "agm": agm_name,
                        "reviews": 0, "stars": 0, "status": "failed"
                    })

                time.sleep(1.2)

            browser.close()

    except Exception as e:
        ev("log", text=f"  💥 Crashed: {e}", type="error")

    ok_n   = sum(1 for r in results if r["status"] == "ok")
    total  = sum(r["reviews"] for r in results)
    failed = [r["name"] for r in results if r["status"] == "failed"]

    ev("log", text="", type="normal")
    ev("log", text="─" * 54, type="muted")
    ev("log", text=f"  ✅ Done: {ok_n}/{len(branches)} branches", type="success")
    if failed:
        ev("log", text=f"  ❌ Failed: {', '.join(failed)}", type="error")
    ev("log", text="", type="normal")
    ev("log", text="  🎉 ALL DONE!", type="bold")
    ev("log", text=f"  Total reviews: {total:,}", type="bold")
    ev("log", text="=" * 54, type="muted")

    q.put(json.dumps({"event": "result", "rows": results}))
    q.put(None)  # sentinel — stream ends


# ── Threaded HTTP server ──────────────────────────────────────────────────────
# ThreadingMixIn = every request gets its own thread
# so SSE stream from Playwright never blocks the server

class ThreadingServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress default access log noise

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        # / — Railway health check, keeps service awake
        if path == "/":
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "2")
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return

        # /status — called by sathya_jupyter.html
        if path == "/status":
            body = json.dumps({"ok": True, "playwright": PLAYWRIGHT_OK}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return

        # /scrape/<AGM> — SSE stream
        if path.startswith("/scrape/"):
            agm = unquote(path[len("/scrape/"):])
            if agm not in VALID_AGMS:
                self.send_response(404)
                self.end_headers()
                return
            self._stream(agm)
            return

        self.send_response(404)
        self.end_headers()

    def _stream(self, agm_name):
        q = queue.Queue()
        t = threading.Thread(target=scrape_agm, args=(agm_name, q), daemon=True)
        t.start()

        self.send_response(200)
        self.send_header("Content-Type",     "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control",    "no-cache")
        self.send_header("X-Accel-Buffering","no")
        self._cors()
        self.end_headers()

        print(f"  [scrape] {agm_name} started")
        try:
            while True:
                try:
                    msg = q.get(timeout=180)
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                    continue

                if msg is None:
                    self.wfile.write(
                        f'data: {json.dumps({"event":"done"})}\n\n'.encode()
                    )
                    self.wfile.flush()
                    break

                self.wfile.write(f"data: {msg}\n\n".encode())
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

        print(f"  [scrape] {agm_name} done")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not PLAYWRIGHT_OK:
        print("\n❌  Playwright not installed.")
        print("    pip install playwright")
        print("    playwright install chromium\n")
        sys.exit(1)

    server = ThreadingServer(("0.0.0.0", PORT), Handler)

    print("=" * 50)
    print("  Sathya Live Scraper — ready")
    print(f"  Listening on http://localhost:{PORT}")
    print("  Open sathya_jupyter.html and click ▶")
    print("  Ctrl+C to stop")
    print("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
