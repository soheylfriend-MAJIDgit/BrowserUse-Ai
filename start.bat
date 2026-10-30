@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Browser Use AI Studio - Launcher

echo ================================================================
echo          Browser Use AI Studio  (GUI Desktop Launcher)
echo ================================================================
echo.

:: 1. Find Python 3.11+ on Windows
set "PY_CMD="

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :found_python
)

for %%V in (3.13 3.12 3.11 3) do (
    py -%%V -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -%%V"
        goto :found_python
    )
)

echo [ERROR] Python 3.11 or newer was not found on this computer!
echo.
echo Rahnama (Guide):
echo   1. Download Python 3.12 from: https://www.python.org/downloads/
echo   2. IMPORTANT: During installation, check the box "Add Python.exe to PATH"!
echo   3. After installing Python, double-click start.bat again.
echo.
choice /C YN /M "Open python.org download page in your browser now?"
if %errorlevel% equ 1 start https://www.python.org/downloads/
pause
exit /b 1

:found_python
for /f "tokens=*" %%i in ('%PY_CMD% --version 2^>^&1') do set "PY_VER=%%i"
echo [OK] Found %PY_VER%

:: 2. Create Virtual Environment (.venv) if not exists
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [1/2] Creating isolated Python environment ^(.venv^)... Please wait...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
)

:: 3. Install dependencies on first run
if not exist ".venv\.deps_installed_v1" (
    echo.
    echo [2/2] First-time setup: Installing Browser Use + PyWebView GUI packages...
    echo       ^(This takes ~1-2 minutes only on the first run. Please wait...^)
    echo.
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Package installation failed! Check your internet / VPN connection
        echo         and run start.bat ^(or repair_install.bat^) again.
        pause
        exit /b 1
    )
    echo ok > ".venv\.deps_installed_v1"
    echo.
    echo [OK] Setup completed successfully!
)

:: 4. If user dragged & dropped a custom .py script onto start.bat, run it directly!
if not "%~1"=="" (
    echo.
    echo [RUN] Executing custom Python file: "%~1"
    echo ----------------------------------------------------------------
    ".venv\Scripts\python.exe" "%~1"
    echo ----------------------------------------------------------------
    pause
    exit /b 0
)

:: 5. Launch PyWebView Desktop GUI Application
echo.
echo [START] Opening Browser Use AI Studio graphical window...
echo         ^(Keep this console minimized while using the app^)
echo.
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
    echo.
    echo [WARN] Desktop window exited with an error. Trying Web Browser mode...
    ".venv\Scripts\python.exe" app.py --web
    pause
)
endlocal
