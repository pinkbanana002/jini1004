@echo off
cd /d "%~dp0"
set "PY=python"
if exist "%~dp0webapp\.venv312\Scripts\python.exe" set "PY=%~dp0webapp\.venv312\Scripts\python.exe"
echo Running studio background (test)...
"%PY%" "%~dp0genstudio.py"
echo.
pause
