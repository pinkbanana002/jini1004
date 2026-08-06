@echo off
chcp 65001 > nul
title Sellochomes Login (one-time priming)

set "PROFILE=%~dp0chrome_profile_stage1"

echo ==================================================
echo  Sellochomes login for the automation profile
echo ==================================================
echo.
echo A Chrome window will open. Log in to Sellochomes
echo (Google / Kakao), confirm a product page opens,
echo then CLOSE that Chrome window.
echo Do NOT run START.bat until this Chrome is closed.
echo.

set "CHROME="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if not defined CHROME (
    echo [ERROR] chrome.exe not found in the usual locations.
    echo Please tell the assistant your Chrome install path.
    pause
    exit /b 1
)

echo Using Chrome: %CHROME%
echo Profile dir : %PROFILE%
echo.
"%CHROME%" --user-data-dir="%PROFILE%" "https://sellochomes.co.kr/sourcinglife/"

echo.
echo Chrome closed. Login session saved. You can now run START.bat.
pause
