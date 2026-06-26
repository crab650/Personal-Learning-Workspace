@echo off
setlocal
title Personal Learning Workspace Launcher

cd /d "%~dp0"

echo ===================================================
echo   Personal Learning ^& Workspace Launcher
echo ===================================================
echo.

echo [1/4] Checking dependencies...
python -c "import flask, flask_login, flask_sqlalchemy, markdown, jwt" 2>nul
if %errorlevel% neq 0 (
    echo [*] Dependencies are missing. Installing from requirements.txt...
    python -m pip install --user -r requirements.txt
    if %errorlevel% neq 0 (
        echo [!] Error: Failed to install dependencies.
        echo     Please run: python -m pip install --user -r requirements.txt
        pause
        exit /b 1
    )
) else (
    echo [*] All dependencies are already installed.
)

echo.
echo [2/4] Preparing database...
set FLASK_APP=run.py
python -m flask upgrade-db
if %errorlevel% neq 0 (
    echo [!] Error: Failed to upgrade database.
    pause
    exit /b 1
)

python -m flask seed
if %errorlevel% neq 0 (
    echo [!] Error: Failed to initialize default data.
    pause
    exit /b 1
)

echo.
echo [3/4] Opening browser at http://127.0.0.1:5050 ...
start "" "http://127.0.0.1:5050"

echo.
echo [4/4] Starting Flask Local Server...
echo       Login: admin / admin123
echo       You can close this window to stop the server.
echo ===================================================
echo.

python run.py

pause
