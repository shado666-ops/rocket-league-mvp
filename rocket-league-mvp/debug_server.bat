@echo off
set "PYTHONPATH=%PYTHONPATH%;%cd%"
call .venv\Scripts\activate.bat
python main.py
pause
