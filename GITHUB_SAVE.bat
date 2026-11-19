@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   Rocket project -^> GitHub backup
echo ============================================
echo.

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set TODAY=%%i

rem ---- keep secrets out of the repo ----
if not exist ".gitignore" (
    echo .env> .gitignore
    echo chrome_auto_profile/>> .gitignore
    echo chrome_profile/>> .gitignore
    echo __pycache__/>> .gitignore
)
findstr /x /c:".env" .gitignore >nul 2>&1
if errorlevel 1 echo .env>> .gitignore

rem ---- warn if .env is already tracked ----
git ls-files --error-unmatch webapp/.env >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [WARNING] webapp/.env is tracked by git.
    echo           Your API key may be uploaded to GitHub.
    echo.
)

git add -A

echo.
echo ===== status =====
git status --short

echo.
echo ===== commit =====
git commit -m "Backup %TODAY%"

echo.
echo ===== push =====
git push

echo.
echo ============================================
echo   DONE. Check messages above.
echo   - 'rejected' or red text = screenshot it
echo ============================================
pause
