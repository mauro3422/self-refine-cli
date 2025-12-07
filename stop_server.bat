@echo off
echo ============================================
echo    KILLING ALL LLAMA-SERVER PROCESSES
echo ============================================
echo.

taskkill /F /IM llama-server.exe 2>nul
if %ERRORLEVEL%==0 (
    echo [OK] All llama-server processes killed
) else (
    echo [OK] No llama-server processes found
)

echo.
echo Done. You can now run start_server.bat
pause
