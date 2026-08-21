@echo off
cd /d "%~dp0"
set "PY=python"
if exist "%~dp0webapp\.venv312\Scripts\python.exe" set "PY=%~dp0webapp\.venv312\Scripts\python.exe"
echo Using python: %PY%
echo Running banner filter...
"%PY%" "%~dp0banner_filter.py"
echo.
echo DONE.
pause
