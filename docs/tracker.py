#!/usr/bin/env python3
"""
tracker.py — Sathya Agencies Live Review Tracker
=================================================
ONE command to run everything:

    pip install playwright
    playwright install chromium
    python tracker.py

Browser opens automatically at http://localhost:5000
Click ▶ on any AGM cell to scrape live Google Maps reviews.
"""

import re, time, json, threading, webbrowser, sys, os, queue
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

# ─────────────────────────────────────────────────────────────
# BRANCH DATA
# ─────────────────────────────────────────────────────────────
BRANCHES = [
    {"id":18,"name":"Kovilpatti",       "place_id":"ChIJHY0o-26yBjsRt7wbXB1pDUE","agm":"Seenivasan"},
    {"id":19,"name":"Ramnad",           "place_id":"ChIJNVVVVaGiATsRnunSgOTvbE8","agm":"Seenivasan"},
    {"id":20,"name":"Paramakudi",       "place_id":"ChIJ-dgjBzQHATsRf27FWAJgmsA","agm":"Seenivasan"},
    {"id":21,"name":"Sayalkudi-1",      "place_id":"ChIJRTqudn9lATsR2fYyMmxlOrw","agm":"Seenivasan"},
    {"id":22,"name":"Villathikullam",   "place_id":"ChIJi_wAkwVbATsRtFl3_V5rGrY","agm":"Seenivasan"},
    {"id":23,"name":"Sattur-2",         "place_id":"ChIJNVVVVcHKBjsR7xMX97RFn8Q","agm":"Seenivasan"},
    {"id":24,"name":"Sankarankovil-1",  "place_id":"ChIJE1mKnhSXBjsRKMQ-9JKQf_c","agm":"Seenivasan"},
    {"id":25,"name":"Kayathar-1",       "place_id":"ChIJx5ebtUgRBDsRMquPZNUJVpw","agm":"Seenivasan"},
    {"id":11,"name":"Nagercoil",        "place_id":"ChIJe1LZBiTxBDsRJFLjlbgZoIs","agm":"Jeeva"},
    {"id":12,"name":"Marthandam",       "place_id":"ChIJcWptCRdVBDsRlJh2q0-rnfY","agm":"Jeeva"},
    {"id":13,"name":"Thuckalay-1",      "place_id":"ChIJc9QgEub4BDsRoyDR4Wd6tYA","agm":"Jeeva"},
    {"id":14,"name":"Colachel-1",       "place_id":"ChIJgRkBLw39BDsR58D0lwNo5Ts","agm":"Jeeva"},
    {"id":15,"name":"Kulasekharam-1",   "place_id":"ChIJw0Ep-kNXBDsRe5ad32jAeAk","agm":"Jeeva"},
    {"id":16,"name":"Monday Market",    "place_id":"ChIJTceRGAD5BDsR65i3YNTcYHk","agm":"Jeeva"},
    {"id":17,"name":"Karungal-1",       "place_id":"ChIJfTP5ASr_BDsRgsBaeQltkw4","agm":"Jeeva"},
    {"id":26,"name":"Thenkasi",         "place_id":"ChIJuaqqquEpBDsRVITw0MMYklc","agm":"Muthuselvam"},
    {"id":27,"name":"Thenkasi-2",       "place_id":"ChIJiwqLye6DBjsRo9v1mWXaycI","agm":"Muthuselvam"},
    {"id":28,"name":"Surandai-1",       "place_id":"ChIJPb1_eEOdBjsRjL9IVCVJhi8","agm":"Muthuselvam"},
    {"id":29,"name":"Puliyankudi-1",    "place_id":"ChIJjZqoc46RBjsRQTGHnNC8xxA","agm":"Muthuselvam"},
    {"id":30,"name":"Sengottai-1",      "place_id":"ChIJw3zzKiaBBjsR9KDyGpn1nXU","agm":"Muthuselvam"},
    {"id":31,"name":"Rajapalayam",      "place_id":"ChIJW2ot-NDpBjsRMTfMF2IV-xE","agm":"Muthuselvam"},
    {"id":7, "name":"Tirunelveli-1",    "place_id":"ChIJ2RU2NvQRBDsRq-Fw7IVwx7k","agm":"John"},
    {"id":8, "name":"Valliyur-1",       "place_id":"ChIJcVNk6TtnBDsRBoP4zpExt5k","agm":"John"},
    {"id":9, "name":"Ambasamudram-1",   "place_id":"ChIJ9SGeIi85BDsRZk4QdyW9BSY","agm":"John"},
    {"id":10,"name":"Anjugramam-1",     "place_id":"ChIJ4yeJebLtBDsRDceoxujdGyc","agm":"John"},
    {"id":1, "name":"Tuticorin-1",      "place_id":"ChIJ5zJNoJfvAzsR-bJE_3bbNYw","agm":"Siva"},
    {"id":2, "name":"Tuticorin-2",      "place_id":"ChIJH6gY4-PvAzsRJ50skTlx3cs","agm":"Siva"},
    {"id":3, "name":"Thiruchendur-1",   "place_id":"ChIJeXA4vJKRAzsRBovAtv6lMuQ","agm":"Siva"},
    {"id":4, "name":"Thisayanvilai-1",  "place_id":"ChIJVWkvdfh_BDsRdvtimKCLS5Y","agm":"Siva"},
    {"id":5, "name":"Eral-2",           "place_id":"ChIJbwAA0KGMAzsRkQilW5PceeA","agm":"Siva"},
    {"id":6, "name":"Udankudi",         "place_id":"ChIJPQAAACyEAzsRgjznQ1GLom0","agm":"Siva"},
    {"id":32,"name":"Virudhunagar",     "place_id":"ChIJN3jzNJgsATsRCU3nrB5ntKE","agm":"Venkatesh"},
    {"id":33,"name":"Virudhunagar-2",   "place_id":"ChIJPezaX7wtATsR9sHhFOG6A1c","agm":"Venkatesh"},
    {"id":34,"name":"Aruppukottai",     "place_id":"ChIJy6qqqgYwATsRbcp-hXnoruM","agm":"Venkatesh"},
    {"id":35,"name":"Aruppukottai-2",   "place_id":"ChIJY04wY58xATsRuoJSichVQQE","agm":"Venkatesh"},
    {"id":36,"name":"Sivakasi",         "place_id":"ChIJI2JvEePOBjsREh8b-x4WF4U","agm":"Venkatesh"},
]

VALID_AGMS = {b["agm"] for b in BRANCHES}

# ─────────────────────────────────────────────────────────────
# PLAYWRIGHT SCRAPER  (runs in its own background thread)
# ─────────────────────────────────────────────────────────────

def _scrape_place(page, place_id, wait_ms=3500):
    """Return (review_count, stars) for one place_id. May return (None, None)."""
    url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    page.goto(url, wait_until="domcontentloaded", timeout=35000)
    page.wait_for_timeout(wait_ms)

    count = None
    stars = None

    # --- review count via aria-label ---
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

    # --- star rating via aria-label ---
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

    # --- fallback: parse page source ---
    try:
        src = page.content()
        if not count:
            for pat in [r'([\d,]+)\s*reviews?',
                        r'"reviewCount"["\s:]+(\d+)',
                        r'(\d[\d,]{2,})\s*Google review']:
                m = re.search(pat, src, re.IGNORECASE)
                if m:
                    v = int(m.group(1).replace(",", ""))
                    if v > 5:
                        count = v
                        break
        if not stars:
            for pat in [r'"ratingValue"\s*:\s*"?([\d.]+)',
                        r'(\d[\.,]\d)\s*(?:stars|out of 5)',
                        r'"rating"\s*:\s*"?([\d.]+)']:
                m = re.search(pat, src, re.IGNORECASE)
                if m:
                    try:
                        v = float(m.group(1).replace(",", "."))
                        if 1.0 <= v <= 5.0:
                            stars = round(v, 1)
                            break
                    except ValueError:
                        pass
    except Exception:
        pass

    return count, stars


def scrape_agm_worker(agm_name, q):
    """
    Worker function — runs in a daemon thread.
    Puts JSON strings into q; puts None when done.
    """
    branches = [b for b in BRANCHES if b["agm"] == agm_name]

    def ev(etype, **kw):
        kw["event"] = etype
        q.put(json.dumps(kw))

    ev("log", text="=" * 54, type="muted")
    ev("log", text="  SATHYA AGENCIES — Live Review Tracker", type="bold")
    ev("log", text=f"  AGM: {agm_name}  ({len(branches)} branches)", type="muted")
    ev("log", text="=" * 54, type="muted")
    ev("log", text="", type="normal")
    ev("log", text="🌐 Starting Chromium browser...", type="accent")

    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                    "--window-size=1280,800",
                ]
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-IN",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Warm-up: one load of Google Maps so the session is initialised
            try:
                page.goto("https://www.google.com/maps",
                          wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(2000)
                ev("log", text="✓ Browser ready\n", type="success")
            except Exception as e:
                ev("log", text=f"⚠ Warm-up skipped ({e})\n", type="muted")

            for i, b in enumerate(branches):
                name = b["name"]
                pad  = str(i + 1).zfill(2)
                ev("log",
                   text=f"  [{pad}/{len(branches)}] {name:<22} → fetching...",
                   type="normal")
                ev("progress", current=i, total=len(branches), branch=name)

                count, stars = None, None
                ok = False

                for attempt in range(1, 4):
                    try:
                        if attempt > 1:
                            ev("log",
                               text=f"    ↺ Retry {attempt}/3 for {name}...",
                               type="muted")
                            time.sleep(3)
                            try:
                                page.goto("about:blank", timeout=5000)
                            except Exception:
                                pass
                            time.sleep(1)

                        wait = 3500 + (attempt - 1) * 2000
                        count, stars = _scrape_place(page, b["place_id"], wait_ms=wait)

                        if count is not None:
                            ok = True
                            break

                        ev("log",
                           text=f"    ⚠ Attempt {attempt}: no data found",
                           type="muted")

                    except Exception as exc:
                        ev("log",
                           text=f"    ⚠ Attempt {attempt} error: {str(exc)[:80]}",
                           type="muted")

                if ok:
                    star_str = f"{stars}★" if stars else "—"
                    ev("log",
                       text=f"  [{pad}/{len(branches)}] {name:<22} → {count:,} reviews  {star_str}  ✓",
                       type="success")
                    results.append({
                        "name":    name,
                        "agm":     agm_name,
                        "reviews": count,
                        "stars":   stars or 0,
                        "status":  "ok",
                    })
                else:
                    ev("log",
                       text=f"  [{pad}/{len(branches)}] {name:<22} → FAILED ✗",
                       type="error")
                    results.append({
                        "name":    name,
                        "agm":     agm_name,
                        "reviews": 0,
                        "stars":   0,
                        "status":  "failed",
                    })

                time.sleep(1.2)

            browser.close()

    except Exception as crash:
        ev("log", text=f"💥 Scraper crashed: {crash}", type="error")

    # Summary
    ok_n    = sum(1 for r in results if r["status"] == "ok")
    total_r = sum(r["reviews"] for r in results)
    failed  = [r["name"] for r in results if r["status"] == "failed"]

    ev("log", text="", type="normal")
    ev("log", text="─" * 54, type="muted")
    ev("log", text=f"  ✅ Fetched: {ok_n}/{len(branches)} branches", type="success")
    if failed:
        ev("log", text=f"  ❌ Failed: {', '.join(failed)}", type="error")
    ev("log", text="", type="normal")
    ev("log", text="  🎉 ALL DONE!", type="bold")
    ev("log", text=f"  Total live reviews: {total_r:,}", type="bold")
    ev("log", text="=" * 54, type="muted")

    # Send result payload then sentinel
    q.put(json.dumps({"event": "result", "rows": results}))
    q.put(None)


# ─────────────────────────────────────────────────────────────
# HTML  (the entire browser UI, served at /)
# ─────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sathya Agencies — Live Tracker</title>
  <link rel="icon" type="image/webp" href="https://www.sathya.store/favicon.webp">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Plus Jakarta Sans',system-ui,sans-serif;background:#f9fafb;min-height:100vh;color:#1e293b}
    .topbar{background:#fff;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;height:52px;position:sticky;top:0;z-index:200;box-shadow:0 1px 0 #e5e7eb,0 2px 8px rgba(0,0,0,.04)}
    .topbar-logo{width:200px;flex-shrink:0;display:flex;align-items:center;gap:10px;padding:0 14px;border-right:1px solid #e5e7eb;height:100%}
    .topbar-logo img{height:30px;object-fit:contain}
    .topbar-logo-text{font-size:12px;font-weight:700;color:#1e293b;line-height:1.2}
    .topbar-controls{display:flex;align-items:center;gap:10px;padding:0 14px;flex:1;min-width:0}
    .topbar-right{display:flex;align-items:center;gap:8px;padding-right:14px;flex-shrink:0}
    .kernel-pill{font-size:11px;color:#94a3b8;font-family:'DM Mono',monospace;display:flex;align-items:center;gap:6px;white-space:nowrap}
    .kernel-dot{width:8px;height:8px;border-radius:50%}
    .hamburger{display:none;width:36px;height:36px;border:1px solid #e5e7eb;border-radius:8px;background:#f8fafc;cursor:pointer;flex-direction:column;align-items:center;justify-content:center;gap:4px;flex-shrink:0;margin-left:8px}
    .hamburger span{display:block;width:16px;height:2px;background:#475569;border-radius:2px}
    .divider-v{width:1px;height:20px;background:#e5e7eb;flex-shrink:0}
    .sp{display:flex;align-items:stretch;border-radius:6px;overflow:hidden;height:30px;flex-shrink:0}
    .sp-main{display:flex;align-items:center;gap:5px;padding:0 12px;font-size:12px;font-weight:600;font-family:inherit;border:none;cursor:pointer;white-space:nowrap;height:100%}
    .sp-sep{width:1px;flex-shrink:0;align-self:stretch;opacity:.4}
    .sp-pdf{display:flex;align-items:center;justify-content:center;padding:0 10px;font-size:11px;font-weight:700;font-family:inherit;border:none;cursor:pointer;letter-spacing:.4px;height:100%}
    .sp-main:disabled,.sp-pdf:disabled{cursor:not-allowed;opacity:.5}
    .sp-green .sp-main{background:#16a34a;color:#fff}.sp-green .sp-main:hover:not(:disabled){background:#15803d}
    .sp-green .sp-sep{background:rgba(255,255,255,.5)}.sp-green .sp-pdf{background:#15803d;color:#fff}
    .sp-green .sp-pdf:hover:not(:disabled){background:#166534}
    .sp-blue .sp-main{background:#1d4ed8;color:#fff}.sp-blue .sp-main:hover:not(:disabled){background:#1e40af}
    .sp-blue .sp-sep{background:rgba(255,255,255,.4)}.sp-blue .sp-pdf{background:#e11d48;color:#fff}
    .sp-blue .sp-pdf:hover:not(:disabled){background:#be123c}
    .sp-gray .sp-main,.sp-gray .sp-pdf{background:#f1f5f9;color:#9ca3af;cursor:not-allowed;border:1px solid #e5e7eb}
    .sp-gray .sp-sep{background:#e5e7eb}
    .run-all-btn{display:flex;align-items:center;gap:6px;padding:0 13px;height:30px;border:none;border-radius:6px;font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;white-space:nowrap;flex-shrink:0;background:#0f172a;color:#fff}
    .run-all-btn:hover:not(:disabled){background:#1e293b}
    .run-all-btn:disabled{background:#e5e7eb;color:#9ca3af;cursor:not-allowed}
    .layout{display:flex;min-height:calc(100vh - 52px)}
    .sidebar{width:200px;flex-shrink:0;background:#fff;border-right:1px solid #e5e7eb;padding:16px 10px;display:flex;flex-direction:column;gap:2px;overflow-y:auto;transition:transform .25s ease}
    .sb-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:150}
    .s-lbl{font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.8px;padding:0 8px;margin:4px 0 5px;font-weight:600}
    .s-link{display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:9px;cursor:pointer;font-size:13px;color:#475569;font-weight:500;text-decoration:none;transition:all .12s}
    .s-link:hover{background:#f1f5f9;color:#1e293b}
    .s-icon{width:28px;height:28px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:14px;background:#f1f5f9;flex-shrink:0;border:1px solid #e5e7eb}
    .s-arrow{margin-left:auto;font-size:9px;color:#94a3b8}
    .s-divider{height:1px;background:#f1f5f9;margin:8px 2px}
    .s-agm{display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:8px;font-size:12px;color:#475569;font-weight:500;cursor:pointer;transition:background .12s}
    .s-agm:hover{background:#f1f5f9}
    .s-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
    .main{flex:1;padding:20px 20px 60px;overflow-x:hidden;min-width:0}
    .cell-wrap{display:flex;gap:0;margin-bottom:4px}
    .cell-gutter{width:44px;flex-shrink:0;display:flex;flex-direction:column;align-items:center;padding-top:10px;gap:4px}
    .cell-body{flex:1;min-width:0}
    .run-btn{width:26px;height:26px;border-radius:50%;background:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s;padding:0}
    .run-btn:disabled{cursor:not-allowed;opacity:.5}
    .exec-num{font-family:'DM Mono',monospace;font-size:10px;color:#94a3b8}
    .collapse-btn{width:22px;height:22px;border:1px solid #e2e8f0;border-radius:4px;background:#f8fafc;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#94a3b8;padding:0;font-size:10px}
    .collapse-btn:hover{background:#e5e7eb;color:#374151}
    .cell-hdr{padding:10px 14px;display:flex;align-items:center;justify-content:space-between;gap:10px;background:#f8fafc;border:1px solid #d1d5db;border-radius:4px 4px 0 0;border-bottom:none;transition:background .2s}
    .cell-hdr.closed{border-radius:4px;border-bottom:1px solid #d1d5db}
    .cell-hdr.running{background:#fffbeb}
    .cell-output{border:1px solid #d1d5db;border-top:1px dashed #e5e7eb;border-radius:0 0 4px 4px;background:#fff;padding:10px 14px;max-height:340px;overflow-y:auto}
    .cell-idle{border:1px solid #e5e7eb;border-top:1px dashed #e5e7eb;border-radius:0 0 4px 4px;background:#fff;padding:8px 14px;color:#cbd5e1;font-family:'DM Mono',monospace;font-size:11px}
    .cell-tbl{border:1px solid #d1d5db;border-top:1px dashed #e5e7eb;border-radius:0 0 4px 4px;background:#fff;overflow-x:auto}
    .dt{width:100%;border-collapse:collapse;font-size:12.5px}
    .dt thead th{background:#f8fafc;color:#94a3b8;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:9px 14px;text-align:left;border-bottom:1px solid #e5e7eb;white-space:nowrap}
    .dt thead th.num{text-align:right}
    .dt tbody tr{border-bottom:1px solid #f1f5f9}
    .dt tbody tr:last-child{border-bottom:none}
    .dt tbody tr:hover{background:rgba(79,70,229,.03)}
    .dt tbody td{padding:10px 14px;white-space:nowrap}
    .dt tbody td.num{text-align:right}
    .dt tbody td.branch{font-weight:600;color:#0f172a}
    .dt tfoot td{padding:9px 14px;font-weight:700;background:#f8fafc;border-top:2px solid #e5e7eb;font-size:12.5px}
    .dt tfoot td.num{text-align:right}
    .badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;font-family:'DM Mono',monospace}
    .b-tot{background:rgba(79,70,229,.1);color:#4f46e5}
    .b-nil{background:#f1f5f9;color:#94a3b8;border:1px solid #e5e7eb}
    .stars{color:#f59e0b;letter-spacing:-1px}
    .live-tag{font-size:8px;background:rgba(5,150,105,.1);color:#059669;border:1px solid rgba(5,150,105,.25);border-radius:4px;padding:1px 5px;font-weight:700;margin-left:5px;vertical-align:middle}
    .fail-tag{font-size:8px;background:rgba(225,29,72,.08);color:#e11d48;border:1px solid rgba(225,29,72,.2);border-radius:4px;padding:1px 5px;font-weight:700;margin-left:5px;vertical-align:middle}
    .output-line{font-family:'DM Mono','Courier New',monospace;font-size:12px;line-height:1.75;white-space:pre-wrap;word-break:break-all}
    .cell-dl-row{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding-top:6px}
    .banner{padding:10px 14px;border-radius:8px;font-size:12px;font-weight:500;margin-bottom:14px}
    .banner-ok{background:rgba(5,150,105,.08);border:1px solid rgba(5,150,105,.2);color:#065f46}
    .title-cell{flex:1;padding:10px 14px;background:#fff;border:1px solid #e5e7eb;border-left:4px solid #3b82f6;border-radius:4px;margin-bottom:2px}
    ::-webkit-scrollbar{width:5px;height:5px}
    ::-webkit-scrollbar-track{background:#f1f5f9}
    ::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:3px}
    @keyframes spin{to{transform:rotate(360deg)}}
    @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
    .spin{animation:spin .9s linear infinite}
    .blink{animation:blink 1s step-end infinite}
    @media(max-width:768px){
      .topbar-logo{width:auto;border-right:none;padding-right:0}.topbar-logo-text{display:none}
      .hamburger{display:flex}
      .sidebar{position:fixed;top:52px;left:0;bottom:0;z-index:160;transform:translateX(-100%);width:220px;box-shadow:4px 0 20px rgba(0,0,0,.15)}
      .sidebar.open{transform:translateX(0)}.sb-overlay.show{display:block}
      .topbar-right{display:none}.main{padding:12px 10px 60px}
      .cell-gutter{width:32px}.dl-lbl{display:none}.divider-v{display:none}
    }
  </style>
</head>
<body>
<div class="sb-overlay" id="sb-ov" onclick="closeSidebar()"></div>
<div class="topbar">
  <div class="topbar-logo">
    <img src="https://www.sathya.store/new_frontend/assets/img/sathya.webp" alt="Sathya" onerror="this.style.display='none'">
    <span class="topbar-logo-text">Live<br>Tracker</span>
  </div>
  <button class="hamburger" onclick="toggleSidebar()"><span></span><span></span><span></span></button>
  <div class="topbar-controls">
    <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:12px;font-weight:600;color:#374151;user-select:none;flex-shrink:0">
      <input type="checkbox" id="chk-all" style="width:14px;height:14px;accent-color:#1d4ed8;cursor:pointer">
      <span class="dl-lbl">Select All</span>
    </label>
    <div class="divider-v"></div>
    <button class="run-all-btn" id="btn-run-all" onclick="runAll()">
      <svg width="11" height="11" viewBox="0 0 10 11" fill="currentColor"><path d="M1 1 L9 5.5 L1 10 Z"/></svg>
      <span class="dl-lbl" id="lbl-run-all">Run All (6)</span>
    </button>
    <div class="divider-v"></div>
    <div class="sp sp-gray" id="dl-all-wrap">
      <button class="sp-main" id="btn-dl-xls" onclick="downloadAllExcel()" disabled>
        <svg width="11" height="11" viewBox="0 0 13 13" fill="none"><path d="M6.5 1v7M4 6l2.5 2.5L9 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 10h9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
        <span id="lbl-dl-all" class="dl-lbl">Download All</span>
      </button>
      <div class="sp-sep" style="height:30px"></div>
      <button class="sp-pdf" id="btn-dl-pdf" onclick="downloadAllPdf()" disabled>PDF</button>
    </div>
  </div>
  <div class="topbar-right">
    <div class="kernel-pill">
      <span class="kernel-dot" style="background:#22c55e"></span>
      Python 3 · Playwright
    </div>
  </div>
</div>

<div class="layout">
  <div class="sidebar" id="main-sb">
    <div class="s-lbl">Navigation</div>
    <a href="/home" class="s-link"><span class="s-icon">🏠</span>Home<span class="s-arrow">↗</span></a>
    <a href="/weather" class="s-link"><span class="s-icon">⛅</span>Weather<span class="s-arrow">↗</span></a>
    <div class="s-divider"></div>
    <div class="s-lbl">AGM Scripts</div>
    <div id="sb-agms"></div>
  </div>
  <div class="main" id="main-area"></div>
</div>

<script>
var C={Seenivasan:"#d97706",Jeeva:"#059669",Muthuselvam:"#7c3aed",John:"#2563eb",Siva:"#dc2626",Venkatesh:"#db2777"};
var S=[
  {id:"seenivasan", label:"kovilpatti.py",  agm:"Seenivasan"},
  {id:"jeeva",      label:"nagercoil.py",   agm:"Jeeva"},
  {id:"muthuselvam",label:"tenkasi.py",     agm:"Muthuselvam"},
  {id:"john",       label:"tirunelveli.py", agm:"John"},
  {id:"siva",       label:"tuticorin.py",   agm:"Siva"},
  {id:"venkatesh",  label:"virudungar.py",  agm:"Venkatesh"},
];
var st={},ln={},dt={},en={},cl={};
var ec=0,busy=false,sse={};

function init(){
  document.getElementById("sb-agms").innerHTML=S.map(function(s){
    return'<div class="s-agm" onclick="scrollTo_(\''+s.id+'\')"><span class="s-dot" style="background:'+C[s.agm]+'"></span>'
      +'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+s.label+'</span></div>';
  }).join("");
  var h='<div class="banner banner-ok">✅ Server running — Playwright ready. Click ▶ to scrape live Google Maps reviews.</div>'
    +'<div class="cell-wrap" style="margin-bottom:10px"><div style="width:44px;flex-shrink:0"></div>'
    +'<div class="title-cell"><div style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:3px">🏪 Google Review Tracker</div>'
    +'<div style="font-size:11.5px;color:#64748b;font-family:\'DM Mono\',monospace">Real-time Playwright · Chromium headless · All 36 Tamil Nadu branches</div>'
    +'</div></div><div style="height:8px"></div>';
  S.forEach(function(s){h+=cell(s);});
  document.getElementById("main-area").innerHTML=h;
  document.getElementById("chk-all").addEventListener("change",function(){
    S.forEach(function(s){var e=document.getElementById("c-"+s.id);if(e)e.checked=this.checked;},this);
    tb();
  });
  tb();
}

function cell(s){
  var col=C[s.agm]||"#6366f1";
  var status=st[s.id]||"idle",isR=status==="running",isDone=status==="done";
  var isCol=cl[s.id]||false;
  var execN=en[s.id]?"["+en[s.id]+"]":"[ ]";
  var lines=ln[s.id]||[], rows=dt[s.id]||[];
  var hc="cell-hdr"+(isR?" running":"")+(isCol||status==="idle"?" closed":"");
  var sb=isDone?'<span style="font-size:10px;color:#15803d;font-family:monospace;font-weight:600">● done</span>'
          :isR?'<span style="font-size:10px;color:'+col+';font-family:monospace;font-weight:600">● running</span>'
          :'<span style="font-size:10px;color:#94a3b8;font-family:monospace;font-weight:600">○ idle</span>';
  var h='<div class="cell-wrap" id="cell-'+s.id+'">'
    +'<div class="cell-gutter"><button class="run-btn" id="rb-'+s.id+'" onclick="runCell(\''+s.id+'\')"'+(isR?' disabled':'')
    +' style="border:1.5px solid '+(isR?"#e2e8f0":col+"66")+';color:'+(isR?"#94a3b8":col)+'">'
    +(isR?'<svg width="12" height="12" viewBox="0 0 13 13" fill="none" class="spin"><circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5" stroke-dasharray="18" stroke-dashoffset="6"/></svg>'
        :'<svg width="9" height="10" viewBox="0 0 10 11" fill="'+col+'"><path d="M1 1 L9 5.5 L1 10 Z"/></svg>')
    +'</button><span class="exec-num">'+execN+'</span></div>'
    +'<div class="cell-body">'
    +'<div class="'+hc+'"'+(isR?' style="border-color:'+col+'"':'')+'>'
    +'<div style="display:flex;align-items:center;gap:8px;min-width:0;flex:1;overflow:hidden">'
    +'<input type="checkbox" id="c-'+s.id+'" checked onchange="tb()" style="width:13px;height:13px;accent-color:'+col+';cursor:pointer;flex-shrink:0">'
    +'<span style="font-family:\'DM Mono\',monospace;font-size:12px;color:#1e3a5f;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
    +'<span style="color:#7c3aed">import</span> <span style="color:#0369a1">playwright</span>'
    +'  # <span style="color:#64748b">'+s.label+'</span></span>'
    +'<span style="font-size:10px;background:'+col+'18;color:'+col+';border:1px solid '+col+'35;border-radius:4px;padding:1px 7px;font-family:monospace;font-weight:600;flex-shrink:0">'+s.agm+'</span>'
    +'</div><div style="display:flex;align-items:center;gap:7px;flex-shrink:0">'+sb;
  if(isDone)h+='<button class="collapse-btn" onclick="toggleC(\''+s.id+'\')">'+(isCol?"▼":"▲")+'</button>';
  h+='</div></div>';
  if(status==="idle")h+='<div class="cell-idle"># click ▶ to scrape live Google Maps reviews</div>';
  else if(isR){
    h+='<div class="cell-output" id="out-'+s.id+'">';
    lines.forEach(function(l){h+=rl(l);});
    h+='<span class="blink" style="display:inline-block;width:7px;height:13px;background:#1e293b;margin-left:2px;vertical-align:middle"></span>';
    h+='</div>';
  }else if(isDone&&!isCol)h+=tbl(rows);
  if(isDone){
    h+='<div class="cell-dl-row"><div class="sp sp-green">'
      +'<button class="sp-main" onclick="dlXls(\''+s.id+'\')">'
      +'<svg width="11" height="11" viewBox="0 0 13 13" fill="none"><path d="M6.5 1v7M4 6l2.5 2.5L9 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 10h9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
      +' Excel</button><div class="sp-sep" style="height:30px"></div>'
      +'<button class="sp-pdf" onclick="dlPdfCell(\''+s.id+'\')">PDF</button>'
      +'</div></div>';
  }
  h+='</div></div>';
  return h;
}

function tbl(rows){
  if(!rows||!rows.length)return'<div class="cell-idle" style="border-top:1px dashed #e5e7eb;border-radius:0 0 4px 4px">No data.</div>';
  var tot=rows.reduce(function(a,r){return a+(r.reviews||0);},0);
  var ok=rows.filter(function(r){return r.status==="ok";}).length;
  var trs=rows.map(function(r,i){
    var isOk=r.status==="ok";
    var bg=i%2===0?"#fff":"#f8fafc";
    var rv=isOk?'<span class="badge b-tot">'+r.reviews.toLocaleString("en-IN")+'</span>':'<span class="badge b-nil">FAILED</span>';
    var sr=r.stars?'<span class="stars">'+"★".repeat(Math.floor(r.stars))+'</span> <span style="font-family:\'DM Mono\',monospace;font-size:11px;color:#64748b">'+r.stars+'</span>':"—";
    var tag=isOk?'<span class="live-tag">LIVE</span>':'<span class="fail-tag">FAILED</span>';
    return'<tr style="background:'+bg+'"><td class="branch">'+r.name+tag+'</td><td>'+sr+'</td><td class="num">'+rv+'</td></tr>';
  }).join("");
  return'<div class="cell-tbl"><table class="dt">'
    +'<thead><tr><th>Branch</th><th>Stars</th><th class="num">Live Reviews</th></tr></thead>'
    +'<tbody>'+trs+'</tbody>'
    +'<tfoot><tr><td style="font-weight:700;color:#0f172a">TOTAL <span style="font-size:10px;font-weight:500;color:#94a3b8">'+ok+'/'+rows.length+' live</span></td>'
    +'<td>—</td><td class="num"><span class="badge b-tot">'+tot.toLocaleString("en-IN")+'</span></td></tr></tfoot>'
    +'</table><div style="padding:6px 14px;font-size:10px;color:#64748b;background:#f8fafc;border-top:1px solid #e5e7eb">'
    +'🕐 Scraped live · '+new Date().toLocaleString("en-IN")+'</div></div>';
}

var LN={normal:"#1e293b",muted:"#94a3b8",bold:"#0f172a",success:"#15803d",error:"#b91c1c",accent:"#1d4ed8"};
function rl(l){
  return'<div class="output-line" style="color:'+(LN[l.type]||"#1e293b")+';font-weight:'+(l.type==="bold"?"700":"400")+'">'+esc(l.text||"\u00a0")+'</div>';
}
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

function re_(id){
  var s=S.find(function(x){return x.id===id;});
  if(!s)return;
  var el=document.getElementById("cell-"+id);
  if(!el)return;
  var t=document.createElement("div");
  t.innerHTML=cell(s);
  el.parentNode.replaceChild(t.firstChild,el);
}
function toggleC(id){cl[id]=!cl[id];re_(id);}
function scrollTo_(id){var e=document.getElementById("cell-"+id);if(e)e.scrollIntoView({behavior:"smooth",block:"start"});closeSidebar();}

/* SCRAPE */
function runCell(id){
  var s=S.find(function(x){return x.id===id;});if(!s)return;
  if(sse[id]){sse[id].close();delete sse[id];}
  st[id]="running";ln[id]=[];dt[id]=[];cl[id]=false;en[id]=++ec;
  re_(id);tb();

  var es=new EventSource("/scrape/"+encodeURIComponent(s.agm));
  sse[id]=es;

  es.onmessage=function(e){
    var msg;try{msg=JSON.parse(e.data);}catch(_){return;}
    if(msg.event==="log"){
      ln[id].push({text:msg.text,type:msg.type||"normal"});
      var out=document.getElementById("out-"+id);
      if(out){
        var d=document.createElement("div");
        d.className="output-line";
        d.style.color=LN[msg.type]||"#1e293b";
        if(msg.type==="bold")d.style.fontWeight="700";
        d.textContent=msg.text||"\u00a0";
        var bl=out.querySelector(".blink");
        if(bl)out.insertBefore(d,bl);else out.appendChild(d);
        out.scrollTop=out.scrollHeight;
      }
    }
    if(msg.event==="result"){dt[id]=msg.rows||[];}
    if(msg.event==="done"){
      es.close();delete sse[id];
      st[id]="done";re_(id);tb();
    }
  };
  es.onerror=function(){
    es.close();delete sse[id];
    ln[id].push({text:"⚠ Stream disconnected.",type:"error"});
    if(st[id]==="running"){st[id]="done";re_(id);tb();}
  };
}

/* RUN ALL */
async function runAll(){
  if(busy)return;busy=true;
  var btn=document.getElementById("btn-run-all");
  btn.disabled=true;
  btn.innerHTML='<svg width="12" height="12" viewBox="0 0 13 13" fill="none" class="spin"><circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5" stroke-dasharray="18" stroke-dashoffset="6"/></svg><span class="dl-lbl">Running…</span>';
  var ids=chk();
  for(var i=0;i<ids.length;i++){
    var id=ids[i];
    await new Promise(function(res){
      runCell(id);
      var poll=setInterval(function(){if(st[id]==="done"){clearInterval(poll);res();}},500);
    });
    if(i<ids.length-1)await new Promise(function(r){setTimeout(r,600);});
  }
  busy=false;btn.disabled=false;
  btn.innerHTML='<svg width="11" height="11" viewBox="0 0 10 11" fill="currentColor"><path d="M1 1 L9 5.5 L1 10 Z"/></svg><span class="dl-lbl" id="lbl-run-all">Run All ('+ids.length+')</span>';
  tb();
}

function chk(){return S.filter(function(s){var e=document.getElementById("c-"+s.id);return e&&e.checked;}).map(function(s){return s.id;});}
function tb(){
  var ids=chk(),allDone=ids.length>0&&ids.every(function(id){return st[id]==="done";});
  var ca=document.getElementById("chk-all");
  if(ca){ca.checked=ids.length===S.length;ca.indeterminate=ids.length>0&&ids.length<S.length;}
  var w=document.getElementById("dl-all-wrap"),bx=document.getElementById("btn-dl-xls"),bp=document.getElementById("btn-dl-pdf"),dl=document.getElementById("lbl-dl-all");
  if(w)w.className="sp "+(allDone?"sp-blue":"sp-gray");
  if(bx)bx.disabled=!allDone;if(bp)bp.disabled=!allDone;
  if(dl)dl.textContent="Download All"+(allDone?" ("+ids.length+")":"");
  var rb=document.getElementById("btn-run-all");if(rb&&!busy)rb.disabled=ids.length===0;
  var lrl=document.getElementById("lbl-run-all");if(lrl)lrl.textContent="Run All ("+ids.length+")";
}

/* EXCEL */
function mkSheet(rows){
  var h=["Branch","Live Reviews","Stars","Status"];
  var d=[h].concat(rows.map(function(r){return[r.name,r.reviews||0,r.stars||"—",r.status==="ok"?"✓":"FAILED"];}));
  var ws=XLSX.utils.aoa_to_sheet(d);
  ws["!cols"]=[{wch:24},{wch:14},{wch:8},{wch:10}];
  ws["!rows"]=d.map(function(_,i){return{hpt:i===0?22:18};});
  var tn={style:"thin",color:{rgb:"AAAAAA"}},b={top:tn,bottom:tn,left:tn,right:tn};
  for(var r=0;r<d.length;r++)for(var c=0;c<h.length;c++){
    var a=XLSX.utils.encode_cell({r:r,c:c});if(!ws[a])ws[a]={v:"",t:"s"};
    ws[a].s={border:b,alignment:{horizontal:"center",vertical:"center",wrapText:true},
      font:r===0?{bold:true,sz:11,color:{rgb:"FFFFFF"}}:{sz:11},
      fill:r===0?{fgColor:{rgb:"1E3A5F"},patternType:"solid"}:r%2===0?{fgColor:{rgb:"EEF2FA"},patternType:"solid"}:{fgColor:{rgb:"FFFFFF"},patternType:"solid"}};
  }
  return ws;
}
function dlXls(id){var s=S.find(function(x){return x.id===id;});var rows=dt[id];if(!s||!rows||!rows.length)return;
  var wb=XLSX.utils.book_new();XLSX.utils.book_append_sheet(wb,mkSheet(rows),s.label.replace(".py",""));
  XLSX.writeFile(wb,s.label.replace(".py","")+"_live_"+new Date().toISOString().slice(0,10)+".xlsx");}
function downloadAllExcel(){
  var ids=chk();var wb=XLSX.utils.book_new();
  S.forEach(function(s){if(!ids.includes(s.id)||!dt[s.id]||!dt[s.id].length)return;XLSX.utils.book_append_sheet(wb,mkSheet(dt[s.id]),s.label.replace(".py",""));});
  if(!wb.SheetNames.length)return;XLSX.writeFile(wb,"sathya_live_"+new Date().toISOString().slice(0,10)+".xlsx");}

/* PDF */
function pdfSec(s,rows){
  var col=C[s.agm]||"#4f46e5";
  var tot=rows.reduce(function(a,r){return a+(r.reviews||0);},0);
  var ok=rows.filter(function(r){return r.status==="ok";}).length;
  var trs=rows.map(function(r,i){
    var bg=i%2===0?"#fff":"#f8fafc";
    var rv=r.status==="ok"?r.reviews.toLocaleString("en-IN"):"FAILED";
    var rc=r.status==="ok"?"#1e293b":"#b91c1c";
    var st=r.stars?r.stars+"★":"—";
    return'<tr style="background:'+bg+'"><td style="text-align:left;font-weight:600;color:#0f172a;padding:6px 10px;border-bottom:1px solid #e5e7eb">'+r.name+'</td>'
      +'<td style="text-align:center;padding:6px 10px;border-bottom:1px solid #e5e7eb;color:#d97706">'+st+'</td>'
      +'<td style="text-align:center;padding:6px 10px;border-bottom:1px solid #e5e7eb;font-weight:600;color:'+rc+'">'+rv+'</td></tr>';
  }).join("");
  return'<div style="margin-bottom:22px;page-break-inside:avoid">'
    +'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:#f0f4f8;border-left:3px solid '+col+';margin-bottom:8px;border-radius:0 4px 4px 0">'
    +'<span style="font-size:11px;font-weight:700;color:#1e293b">'+s.label.replace(".py","").toUpperCase()+' &mdash; '+ok+'/'+rows.length+' live</span>'
    +'<span style="font-size:9px;font-weight:700;padding:2px 9px;border-radius:10px;background:'+col+'22;color:'+col+'">AGM: '+s.agm+'</span></div>'
    +'<table style="width:100%;border-collapse:collapse;font-size:10px"><thead><tr style="background:#1e3a5f">'
    +'<th style="color:#fff;font-size:9px;font-weight:700;padding:7px 10px;text-align:left;text-transform:uppercase;letter-spacing:.5px">Branch</th>'
    +'<th style="color:#fff;font-size:9px;font-weight:700;padding:7px 10px;text-align:center;text-transform:uppercase;letter-spacing:.5px">Stars</th>'
    +'<th style="color:#fff;font-size:9px;font-weight:700;padding:7px 10px;text-align:center;text-transform:uppercase;letter-spacing:.5px">Live Reviews</th>'
    +'</tr></thead><tbody>'+trs+'</tbody>'
    +'<tfoot><tr style="background:#f8fafc"><td colspan="2" style="padding:6px 10px;font-weight:700;color:#0f172a;font-size:10px">TOTAL</td>'
    +'<td style="text-align:center;padding:6px 10px;font-weight:700;color:#4f46e5;font-size:10px">'+tot.toLocaleString("en-IN")+'</td></tr></tfoot></table></div>';
}
function printPdf(secs,title){
  var now=new Date();
  var ds=now.toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}).toUpperCase();
  var ts=now.toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"});
  var html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+title+'</title>'
    +'<style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#1e293b;background:#fff}'
    +'.page{padding:16mm 15mm 12mm}.hdr{display:flex;align-items:center;justify-content:space-between;border-bottom:2.5px solid #1e3a5f;padding-bottom:10px;margin-bottom:18px}'
    +'.hdr-left{display:flex;align-items:center;gap:12px}.hdr-logo{height:36px;object-fit:contain}'
    +'.hdr-title{font-size:17px;font-weight:700;color:#1e3a5f}.hdr-sub{font-size:9px;color:#64748b;margin-top:3px;text-transform:uppercase;letter-spacing:.5px}'
    +'.hdr-right{text-align:right;font-size:9px;color:#64748b;line-height:2}.hdr-right strong{color:#1e293b}'
    +'.footer{margin-top:20px;border-top:1px solid #e5e7eb;padding-top:8px;display:flex;justify-content:space-between;font-size:8px;color:#94a3b8}'
    +'@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact;}@page{size:A4;margin:0;}.page{padding:13mm 14mm 10mm;}}'
    +'</style></head><body><div class="page">'
    +'<div class="hdr"><div class="hdr-left"><img class="hdr-logo" src="https://www.sathya.store/new_frontend/assets/img/sathya.webp" alt="Sathya">'
    +'<div><div class="hdr-title">Google Review Report &mdash; Live Data</div>'
    +'<div class="hdr-sub">Sathya Agencies &mdash; Scraped via Playwright Chromium</div></div></div>'
    +'<div class="hdr-right"><div>Date: <strong>'+ds+'</strong></div><div>Time: <strong>'+ts+'</strong></div></div></div>'
    +secs+'<div class="footer"><span>Sathya Agencies &mdash; Live Tracker</span><span>Generated: '+ds+' &nbsp; '+ts+'</span></div>'
    +'</div><script>var p=false;function go(){if(p)return;p=true;window.print();}'
    +'var i=document.querySelector(".hdr-logo");if(i){i.addEventListener("load",go);i.addEventListener("error",go);}setTimeout(go,1200);<\/script>'
    +'</body></html>';
  var blob=new Blob([html],{type:"text/html;charset=utf-8"});
  var url=URL.createObjectURL(blob);
  var win=window.open(url,"_blank");
  if(win){win.addEventListener("load",function(){setTimeout(function(){URL.revokeObjectURL(url);},3000);});}
  else{setTimeout(function(){URL.revokeObjectURL(url);},10000);alert("Allow pop-ups and try again.");}
}
function dlPdfCell(id){var s=S.find(function(x){return x.id===id;});var rows=dt[id];if(!s||!rows||!rows.length)return;printPdf(pdfSec(s,rows),s.label.replace(".py","")+" — Live Review Report");}
function downloadAllPdf(){
  var ids=chk();
  var secs=S.filter(function(s){return ids.includes(s.id)&&dt[s.id]&&dt[s.id].length;}).map(function(s){return pdfSec(s,dt[s.id]);}).join("");
  if(!secs)return;printPdf(secs,"Sathya Agencies — All Branch Live Review Report");}

function toggleSidebar(){document.getElementById("main-sb").classList.toggle("open");document.getElementById("sb-ov").classList.toggle("show");}
function closeSidebar(){document.getElementById("main-sb").classList.remove("open");document.getElementById("sb-ov").classList.remove("show");}

init();
</script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────
# THREADED HTTP SERVER
# A ThreadingHTTPServer handles each request in its own thread,
# so a long-running SSE stream never blocks other requests.
# ─────────────────────────────────────────────────────────────

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True   # worker threads die when main thread dies


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Suppress noisy GET logs; only print scrape events
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"

        # ── Main tracker UI ──────────────────────────────────────
        if path in ("/", "/tracker"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # ── Redirect /home and /weather to sibling HTML files ────
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if path == "/home":
            for f in ("index.html", "sathya_tracker.html"):
                if os.path.exists(os.path.join(base_dir, f)):
                    self._serve_file(os.path.join(base_dir, f))
                    return
            self._redirect("http://localhost:5000/")
            return

        if path == "/weather":
            fp = os.path.join(base_dir, "sathya-weather.html")
            if os.path.exists(fp):
                self._serve_file(fp)
                return
            self._text("sathya-weather.html not found in the same folder.")
            return

        # ── Serve any sibling HTML/JS/CSS file ───────────────────
        if len(path) > 1:
            fp = os.path.join(base_dir, path.lstrip("/"))
            if os.path.exists(fp) and os.path.isfile(fp):
                self._serve_file(fp)
                return

        # ── SSE scrape endpoint: /scrape/<AGM> ───────────────────
        if path.startswith("/scrape/"):
            agm = unquote(path[len("/scrape/"):])
            if agm not in VALID_AGMS:
                self.send_response(404)
                self.end_headers()
                return
            self._stream_scrape(agm)
            return

        # ── /status ──────────────────────────────────────────────
        if path == "/status":
            body = json.dumps({"ok": True, "playwright": PLAYWRIGHT_OK}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def _stream_scrape(self, agm_name):
        """Open SSE stream, run scraper in a daemon thread, flush every event."""
        q = queue.Queue()

        worker = threading.Thread(
            target=scrape_agm_worker,
            args=(agm_name, q),
            daemon=True,
        )
        worker.start()

        self.send_response(200)
        self.send_header("Content-Type",  "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_cors_headers()
        self.end_headers()

        print(f"  [scrape] AGM={agm_name} started")

        try:
            while True:
                try:
                    msg = q.get(timeout=120)   # 2-min max wait per event
                except queue.Empty:
                    # Send a keep-alive comment so the browser doesn't time out
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                    continue

                if msg is None:
                    # Sentinel — scraper finished
                    done = json.dumps({"event": "done"})
                    self.wfile.write(f"data: {done}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    break

                self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # browser closed the tab — that's fine

        print(f"  [scrape] AGM={agm_name} done")

    def _serve_file(self, filepath):
        ext  = os.path.splitext(filepath)[1].lower()
        mime = {"html": "text/html", "js": "application/javascript",
                "css": "text/css", "json": "application/json",
                "png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "text/plain")
        with open(filepath, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def _text(self, msg):
        body = msg.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not PLAYWRIGHT_OK:
        print("\n❌  Playwright is not installed.")
        print("    Run these two commands first:\n")
        print("    pip install playwright")
        print("    playwright install chromium\n")
        sys.exit(1)

    PORT = 5000
    url  = f"http://localhost:{PORT}"

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)

    print("=" * 58)
    print("  Sathya Agencies — Live Review Tracker")
    print("=" * 58)
    print(f"  ✅ Playwright ready")
    print(f"  🌐 Server: {url}")
    print(f"  Opening browser automatically...")
    print(f"  Press Ctrl+C to stop")
    print("=" * 58)

    # Open browser 1 second after server starts
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
