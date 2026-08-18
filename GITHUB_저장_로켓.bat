@echo off
setlocal

cd /d "C:\Users\Jini\Desktop\대량클로드_로켓배송_자동화"

echo ============================================
echo   Rocket project -^> GitHub push
echo ============================================
echo.

git add -A

echo.
echo ===== status =====
git status

echo.
echo ===== commit =====
git commit -m "Update rocket automation (last night work)" -m "Save recent local changes to GitHub backup"

echo.
echo ===== push =====
git push

echo.
echo ============================================
echo   DONE. Check messages above.
echo   - if you see 'rejected' or red errors, screenshot this
echo ============================================
pause
