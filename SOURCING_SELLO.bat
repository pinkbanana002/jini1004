@echo off
chcp 65001 > nul
title Sourcing Life x 1688 Collector
cd /d "%~dp0webapp"

set "VENV_PY=.venv312\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [ERROR] Python venv not found.
    echo         Run START.bat once first, then try again.
    pause
    exit /b 1
)

echo ==================================================
echo    Sourcing Life x 1688 Collector
echo ==================================================
echo.
echo  Korean keywords are OK. Separate them with spaces.
echo  Result is saved as an Excel file in the project folder.
echo.

"%VENV_PY%" modules\sourcing_sello.py %*

echo.
pause
