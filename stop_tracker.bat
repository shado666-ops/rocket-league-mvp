@echo off
color 0C
title Arret Rocket League MVP Tracker
cd /d "%~dp0"

echo.
echo ==========================================
echo     ARRET ROCKET LEAGUE MVP TRACKER
echo ==========================================
echo.

".\.venv\Scripts\python.exe" ".\stop_tracker.py"

echo.
pause