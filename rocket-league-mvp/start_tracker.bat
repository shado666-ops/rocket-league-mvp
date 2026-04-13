@echo off
set "PYTHONPATH=%PYTHONPATH%;%cd%"
call .venv\Scripts\activate.bat
python menu_launcher.py
pause