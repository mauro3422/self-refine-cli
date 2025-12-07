@echo off
title Llama Server (Vulkan GPU)
color 0A

echo ============================================
echo          LLAMA.CPP SERVER - GPU MODE
echo ============================================
echo.

REM Kill any existing llama-server processes first
echo Checking for existing server processes...
taskkill /F /IM llama-server.exe 2>nul
if %ERRORLEVEL%==0 (
    echo [OK] Killed old server process
    timeout /t 2 /nobreak >nul
) else (
    echo [OK] No old server running
)
echo.

echo Model: LFM2-1.2B-F16
echo Port: 8000
echo Parallel Slots: 6
echo GPU Layers: ALL (Vulkan)
echo.
echo Starting server... 
echo.
echo ============================================
echo    SERVER RUNNING - KEEP THIS WINDOW OPEN
echo    Press Ctrl+C to stop
echo ============================================
echo.

cd server
llama-server.exe --model "C:/Users/mauro/.lmstudio/models/LiquidAI/LFM2-1.2B-GGUF/LFM2-1.2B-F16.gguf" ^
    --port 8000 ^
    --host 0.0.0.0 ^
    --n-gpu-layers 999 ^
    --ctx-size 16384 ^
    --parallel 6 ^
    --cont-batching

echo.
echo ============================================
echo SERVER STOPPED
echo ============================================
pause
