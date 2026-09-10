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
git commit -m "Update rocket automation (0829 work)" -m "stage1: detail filter off + cny price extract + color KO->EN; main_image_studio: text removal + timeout + parallel; app.js: popup simplified + auto stage2; 07_cell_9: type/model M1/yellow fill; detail_image_filter: dedup + ad remove"

echo.
echo ===== push =====
git push

echo.
echo ============================================
echo   DONE. Check messages above.
echo   - if you see 'rejected' or red errors, screenshot this
echo ============================================
pause
