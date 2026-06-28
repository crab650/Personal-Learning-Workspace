@echo off
setlocal
title GitHub CLI Login

where gh >nul 2>&1
if errorlevel 1 (
    echo GitHub CLI ^(gh^) is not installed or is not in PATH.
    echo Download it from: https://cli.github.com/
    echo.
    pause
    exit /b 1
)

set "GH_USER="
for /f "delims=" %%U in ('gh api user --jq ".login" 2^>nul') do set "GH_USER=%%U"

if defined GH_USER (
    echo GitHub is already authenticated as %GH_USER%.
    gh auth setup-git
    echo.
    echo Login verification completed.
    pause
    exit /b 0
)

echo Removing any invalid saved login...
gh auth logout -h github.com -u crab650 >nul 2>&1

echo.
echo A GitHub page will open in your browser.
echo Copy the one-time code shown below, authorize GitHub CLI,
echo then return to this window.
echo.

gh auth login -h github.com -p https --web
if errorlevel 1 (
    echo.
    echo GitHub login failed or was cancelled.
    pause
    exit /b 1
)

gh auth setup-git
if errorlevel 1 (
    echo.
    echo Login succeeded, but Git credential setup failed.
    pause
    exit /b 1
)

echo.
echo Verifying GitHub API access...
gh api user --jq ".login"
if errorlevel 1 (
    echo.
    echo The saved token is not valid. Please run this file again.
    pause
    exit /b 1
)

echo.
echo GitHub login completed successfully.
pause
