@echo off
title Self-Refine CLI - Start Services
color 0A

echo ============================================
echo      SELF-REFINE CLI - START SERVERS
echo ============================================
echo.

:: Navigate to project root
cd /d %~dp0

:: ========== VALIDATIONS ==========

:: Check if llama-server exists
if not exist "server\llama-server.exe" (
    echo [ERROR] llama-server.exe not found in server\ directory!
    echo Please download llama.cpp compiled binaries.
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

:: ========== START SERVICES ==========

echo [1/2] Starting LLM Server (Vulkan GPU)...
start "LLM Server" cmd /k "scripts\start_llm.bat"
echo      Waiting 5s...
timeout /t 5 /nobreak >nul

echo [2/2] Starting ChromaDB Vector Server...
start "ChromaDB" cmd /k "scripts\start_chroma.bat"
echo      Waiting 3s...
timeout /t 3 /nobreak >nul

:: ========== HEALTH CHECK ==========

echo.
echo Checking LLM Server health...
curl -s http://localhost:8000/health >nul 2>&1
if %ERRORLEVEL%==0 (
    echo [OK] LLM Server: http://localhost:8000
) else (
    echo [WARNING] LLM Server may still be starting...
)

echo.
echo ============================================
echo          SERVERS STARTED
echo ============================================
echo.
echo LLM Server:  http://localhost:8000
echo ChromaDB:    http://localhost:8100
echo.
echo ============================================
echo          NEXT STEPS
echo ============================================
echo.
echo For DOCKER (sandboxed - recommended):
echo   docker-compose up --build
echo.
echo For LOCAL (no sandbox):
echo   python autonomous_loop.py
echo.
echo For DASHBOARD:
echo   python -m ui.dashboard
echo.
pause
