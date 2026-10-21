@echo off
echo ====================================================
echo Stopping Antigravity Gateway Docker container...
echo ====================================================
docker compose down
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Antigravity Gateway container stopped.
    echo.
) else (
    echo.
    echo [ERROR] Failed to stop container.
    echo.
)
pause
