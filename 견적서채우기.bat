@echo off
cd /d "%~dp0"
set PY=python
if exist ".venv312\Scripts\python.exe" set PY=.venv312\Scripts\python.exe

if "%~1"=="" (
  echo ============================================
  echo   견적서 xlsx 파일을 이 bat 아이콘 위로
  echo   끌어다 놓으면 빈칸이 자동으로 채워집니다.
  echo ============================================
  pause
  exit /b
)

echo 채우는 중: %~1
%PY% "%~dp0견적서_채우기보완.py" "%~1"
echo.
pause
