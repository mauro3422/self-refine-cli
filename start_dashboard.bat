@echo off
title Poetiq Dashboard
echo Starting Dashboard...
python -m ui.dashboard
if %errorlevel% neq 0 (
    echo.
    echo ❌ Dashboard crashed with error code %errorlevel%
    echo.
)
pause
