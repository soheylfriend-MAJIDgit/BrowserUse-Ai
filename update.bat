@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Browser Use AI Studio - GitHub Updater

echo ================================================================
echo         Browser Use AI Studio - Update from GitHub
echo ================================================================
echo.

git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed in PATH. Please download the latest ZIP from GitHub.
    pause
    exit /b 1
)

echo Pulling latest updates from GitHub...
git pull
if errorlevel 1 (
    echo.
    echo [WARN] Could not auto-pull. Make sure you have no conflicting local edits.
    pause
    exit /b 1
)

echo.
echo [OK] Successfully updated! Launching Browser Use AI Studio...
call start.bat
endlocal
