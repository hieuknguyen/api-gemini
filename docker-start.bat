@echo off
echo ====================================================
echo Starting Antigravity Gateway in Docker...
echo ====================================================
docker compose up -d --build
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Antigravity Gateway and Frontend are running!
    echo Frontend Web UI: http://localhost:5173/
    echo Gateway Web UI:  http://localhost:5678/
    echo API Docs:        http://localhost:5678/docs
    echo API Base URL:    http://localhost:5678/v1
    echo.
) else (
    echo.
    echo [ERROR] Failed to start Docker container.
    echo Please make sure Docker Desktop is running.
    echo.
)
pause
