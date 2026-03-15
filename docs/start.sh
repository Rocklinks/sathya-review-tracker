#!/bin/bash
echo "Starting Sathya Live Tracker..."
pip install playwright 2>/dev/null
playwright install chromium 2>/dev/null
python3 tracker.py
