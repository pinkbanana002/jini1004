@echo off
chcp 65001 > nul
title Coupang Rocket Delivery Automation

cd /d "%~dp0webapp"

echo ==================================================
echo    Coupang Rocket Delivery Automation - Starting
echo ==================================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Please install from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Kill any stale python process occupying port 8000
echo Checking for stale server on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo   Found existing process PID %%a - terminating...
    taskkill /f /pid %%a > nul 2>&1
)

echo Checking/installing dependencies...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Library install failed. Check internet connection.
    pause
    exit /b 1
)
echo.

start "" cmd /c "timeout /t 3 > nul && start http://localhost:8000"

python server.py

pause
