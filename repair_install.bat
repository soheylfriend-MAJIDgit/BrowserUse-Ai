@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Browser Use AI Studio - Repair & Update

echo ================================================================
echo       Browser Use AI Studio - Repair & Update Packages
echo ================================================================
echo.

if exist ".venv\.deps_installed_v1" del /f /q ".venv\.deps_installed_v1"

set "PY_CMD=python"
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 set "PY_CMD=py -3"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY_CMD% -m venv .venv
)

echo Updating pip and reinstalling required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to update packages. Check your internet / VPN connection.
    pause
    exit /b 1
)

echo ok > ".venv\.deps_installed_v1"
echo.
echo [OK] All Python packages are installed and up to date!
echo.
choice /C YN /M "Do you also want to download standalone Playwright Chromium browser (only needed if Chrome/Edge is not installed)?"
if %errorlevel% equ 1 (
    ".venv\Scripts\python.exe" -m pip install playwright
    ".venv\Scripts\python.exe" -m playwright install chromium
)

echo.
echo Done! You can now run start.bat to open the application.
pause
endlocal
