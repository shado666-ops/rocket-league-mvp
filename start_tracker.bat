@echo off
set BALLCHASING_API_KEY=mf1fAbRos02BRD33nTPok6PwZjz3N6gB3jPKlaXD
color 0A
title Rocket League MVP Tracker
cd /d "%~dp0"

echo.
echo ==========================================
echo        ROCKET LEAGUE MVP TRACKER
echo ==========================================
echo.
echo Lancement du launcher...
echo.

".\.venv\Scripts\python.exe" ".\launcher.py"

echo.
echo ==========================================
echo Tracker arrete.
echo ==========================================
pause