#!/bin/bash
echo "Starting Sathya Live Scraper..."
pip install playwright 2>/dev/null
playwright install chromium 2>/dev/null
open sathya_jupyter.html 2>/dev/null || xdg-open sathya_jupyter.html 2>/dev/null &
python3 live_scraper.py
