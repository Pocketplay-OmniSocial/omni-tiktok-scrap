@echo off
setlocal
cd /d "%~dp0"

echo Opening Omni TikTok Scraper at http://127.0.0.1:7860
echo Press Ctrl+C in this window to stop the server and running job.
start "" "http://127.0.0.1:7860"
set "PYTHONPATH=%CD%\src"
python -m omni_tiktok_scraper.web --host 127.0.0.1 --port 7860

echo Server stopped.
pause
