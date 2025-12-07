@echo off
title Poetiq Launcher
color 0F

echo ===================================================
echo 🚀 POETIQ SYSTEM LAUNCHER
echo ===================================================
echo.
echo Launching all components in separate windows:
echo 1. LLM Server (llama.cpp)
echo 2. ChromaDB (Vector Database)
echo 3. Dashboard (Web UI)
echo.

:: Launch LLM Server
start "LLM Server" cmd /k "scripts\start_llm.bat"

:: Launch ChromaDB
echo Waiting 2s...
timeout /t 2 /nobreak >nul
start "ChromaDB" cmd /k "scripts\start_chroma.bat"

:: Launch Dashboard
echo Waiting 5s for DB...
timeout /t 5 /nobreak >nul
start "Dashboard" cmd /k "scripts\start_dashboard.bat"

echo.
echo ✅ All systems launched!
echo.
echo You can close this window, or press any key to exit.
pause
exit
