@echo off
cd /d "%~dp0"

if not exist "webapp\modules" (
  echo ERROR: webapp\modules not found in this folder.
  echo.
  echo Move CLEAN_CACHE.bat into the ROCKET project folder
  echo the same folder that has START.bat  then run again.
  echo.
  pause
  exit /b
)

echo Killing python...
taskkill /f /im python.exe 2>nul

echo Deleting cache...
rmdir /s /q "webapp\modules\__pycache__" 2>nul
rmdir /s /q "webapp\__pycache__" 2>nul

echo.
echo Done. Cache cleared.
echo Now run START.bat and do step 1 with a NEW product.
echo.
pause
