@echo off
REM Get a new ZoomInfo access token and update .env (no Developer Portal).
REM Requires ZOOMINFO_CLIENT_ID, ZOOMINFO_CLIENT_SECRET, ZOOMINFO_REFRESH_TOKEN in .env.
REM First time? Run: python oauth_capture_refresh_token.py  (see GET_REFRESH_TOKEN.md)
cd /d "%~dp0"
python get_zoominfo_token.py
if errorlevel 1 exit /b 1
echo.
echo You can now run: python zoominfo_enrich_company.py -n "Apex Aircraft Sales"
