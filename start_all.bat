@echo off
title Poetiq System - ChromaDB + Dashboard
echo ===================================================
echo 🚀 POETIQ SYSTEM LAUNCHER
echo ===================================================
echo.
echo This starts ChromaDB and Dashboard together.
echo LLM Server (llama.cpp) should be started separately.
echo.
echo ===================================================

:: Create data directory if needed
mkdir outputs\vector_memory_server 2>nul

echo [1/2] Starting ChromaDB Vector Server (Port 8100)...
start "ChromaDB Server" cmd /k "chroma run --path outputs/vector_memory_server --port 8100"

echo [2/2] Waiting for ChromaDB to initialize (8s)...
timeout /t 8 /nobreak >nul

echo.
echo ✅ ChromaDB should be ready
echo.
echo Starting Memory Dashboard on http://localhost:5000...
echo.

:: Start dashboard in this window so you can see logs
python -m ui.dashboard

if %errorlevel% neq 0 (
    echo.
    echo ❌ Dashboard crashed with error code %errorlevel%
    echo Make sure ChromaDB is running (check the other window)
)

pause
