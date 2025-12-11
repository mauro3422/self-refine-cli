@echo off
title Self-Refine CLI - Start All Services
color 0A

echo ============================================
echo      SELF-REFINE CLI - START ALL
echo ============================================
echo.

:: Navigate to project root
cd /d %~dp0

:: Check if llama-server exists
if not exist "server\llama-server.exe" (
    echo [ERROR] llama-server.exe not found in server\ directory!
    echo Please download llama.cpp compiled binaries and place llama-server.exe in server\
    pause
    exit /b 1
)

:: Check if model exists
if not exist "models\*.gguf" (
    echo [ERROR] No .gguf model found in models\ directory!
    echo Please download a model (e.g., Qwen2.5-Coder-7B-Instruct.Q4_K_M.gguf)
    pause
    exit /b 1
)

echo [1/2] Starting LLM Server (Vulkan GPU)...
start "LLM Server" cmd /k "scripts\start_llm.bat"
echo      Waiting 10s for server startup...
timeout /t 10 /nobreak >nul

echo [2/2] Checking LLM Server health...
curl -s http://localhost:8000/health >nul 2>&1
if %ERRORLEVEL%==0 (
    echo      [OK] LLM Server is running!
) else (
    echo      [WARNING] Cannot reach LLM Server. It may still be starting...
)

echo.
echo ============================================
echo      ALL SERVICES STARTED
echo ============================================
echo.
echo LLM Server:  http://localhost:8000
echo.
echo To run the autonomous loop:
echo   python autonomous_loop.py
echo.
echo To run the dashboard:
echo   python -m ui.dashboard
echo.
pause
