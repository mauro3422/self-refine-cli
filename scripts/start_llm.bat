@echo off
title Llama Server (Vulkan GPU)
color 0A

:: Ensure we are in project root
cd /d %~dp0..

echo ============================================
echo          LLAMA.CPP SERVER - GPU MODE
echo ============================================
echo.

:: Kill any existing llama-server processes
taskkill /F /IM llama-server.exe 2>nul
if %ERRORLEVEL%==0 (
    echo [OK] Killed old server process
    timeout /t 2 /nobreak >nul
) else (
    echo [OK] No old server running
)

echo Model: LFM2-1.2B-F16
echo Port: 8000
echo Parallel Slots: 6
echo GPU Layers: ALL (Vulkan)
echo.

cd server
if not exist llama-server.exe (
    echo ❌ Error: llama-server.exe not found in server/ directory!
    pause
    exit /b 1
)

llama-server.exe --model "C:/Users/mauro/.lmstudio/models/LiquidAI/LFM2-1.2B-GGUF/LFM2-1.2B-F16.gguf" ^
    --port 8000 ^
    --host 0.0.0.0 ^
    --n-gpu-layers 999 ^
    --ctx-size 16384 ^
    --parallel 6 ^
    --cont-batching

pause
