@echo off
echo Starting Self-Refine CLI in Docker...
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker is not running! Please start Docker Desktop and try again.
    pause
    exit /b
)

REM Build and start
docker-compose up --build -d

echo.
echo Worker started in background.
echo Use 'docker-compose logs -f' to see logs.
echo.
pause
