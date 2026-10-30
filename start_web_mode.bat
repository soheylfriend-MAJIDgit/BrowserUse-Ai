@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Browser Use AI Studio - Web Browser Mode

if not exist ".venv\Scripts\python.exe" (
    echo First-time setup has not run yet. Launching start.bat to install packages...
    call start.bat
    exit /b 0
)

echo Opening Browser Use AI Studio in your default Web Browser...
".venv\Scripts\python.exe" app.py --web
pause
endlocal
