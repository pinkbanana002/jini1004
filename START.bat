@echo off
chcp 65001 > nul
title Coupang Rocket Delivery Automation
cd /d "%~dp0webapp"

echo ==================================================
echo    Coupang Rocket Delivery Automation - Starting
echo ==================================================
echo.

py -3.12 --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12 not found. Install from:
    echo   https://www.python.org/downloads/release/python-3129/
    pause
    exit /b 1
)

if not exist ".venv312\Scripts\python.exe" (
    echo Creating Python 3.12 virtual environment...
    py -3.12 -m venv .venv312
)

set "VENV_PY=.venv312\Scripts\python.exe"

echo Cleaning up stale server on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /f /pid %%a > nul 2>&1

echo Installing dependencies (first run takes a few minutes)...
"%VENV_PY%" -m pip install -q --upgrade pip
"%VENV_PY%" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Library install failed. Check internet connection.
    pause
    exit /b 1
)
echo.
echo Starting server... open http://localhost:8000 in your browser.
echo.

start "" http://localhost:8000
"%VENV_PY%" server.py

pause
