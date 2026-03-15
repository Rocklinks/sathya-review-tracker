@echo off
echo Starting Sathya Live Tracker...

REM Install dependencies if needed
pip install playwright >nul 2>&1
playwright install chromium >nul 2>&1

REM Start the Python server (opens browser automatically)
python tracker.py
pause
