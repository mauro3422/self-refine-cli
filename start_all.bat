@echo off
setlocal
title Self-Refine CLI - Start Services
color 0A

echo ============================================
echo      SELF-REFINE CLI - START SERVERS
echo ============================================
echo.

:: Navigate to project root (where this script is located)
cd /d "%~dp0"
echo Current directory: %CD%
echo.

:: ========== VALIDATIONS ==========
echo Checking requirements...

:: Check if llama-server exists
if not exist "server\llama-server.exe" (
    echo [ERROR] llama-server.exe not found!
    echo Expected at: %CD%\server\llama-server.exe
    goto :error
)
echo [OK] Found llama-server.exe

:: Check if model exists
dir /b "models\*.gguf" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No .gguf model found!
    echo Expected in: %CD%\models\
    goto :error
)
echo [OK] Found model file

:: ========== START SERVICES ==========
echo.
echo Starting services...
echo.

echo [1/2] Starting LLM Server (Vulkan GPU)...
start "LLM Server" cmd /k "cd /d %CD% && scripts\start_llm.bat"
echo      Server window opened. Waiting 5s...
timeout /t 5 /nobreak >nul

echo [2/2] Starting ChromaDB Vector Server...
start "ChromaDB" cmd /k "cd /d %CD% && scripts\start_chroma.bat"
echo      ChromaDB window opened. Waiting 3s...
timeout /t 3 /nobreak >nul

echo.
echo [Optional] Starting Dashboard...
start "Dashboard" cmd /k "cd /d %CD% && python -m ui.dashboard"
echo      Dashboard opened at http://localhost:5000
timeout /t 2 /nobreak >nul

:: ========== DONE ==========
echo.
echo ============================================
echo          ALL SERVICES STARTED
echo ============================================
echo.
echo LLM Server:  http://localhost:8000 (may take 30s to load model)
echo ChromaDB:    http://localhost:8100
echo Dashboard:   http://localhost:5000
echo.
echo Press any key to close this window...
pause >nul
exit /b 0

:error
echo.
echo ============================================
echo          STARTUP FAILED
echo ============================================
pause
exit /b 1
