@echo off
title Poetiq Dashboard
color 0E

:: Ensure we are in project root
cd /d %~dp0..

echo ============================================
echo          POETIQ DASHBOARD
echo ============================================
echo.
echo URL: http://localhost:5000
echo.

echo Starting Flask...
python -m ui.dashboard

if %errorlevel% neq 0 (
    echo.
    echo ❌ Dashboard crashed with error code %errorlevel%
)
pause
