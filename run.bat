@echo off
title Antigravity AI Gateway (FastAPI)
cd /d "%~dp0"
echo ===================================================
echo   Starting Antigravity FastAPI Gateway...
echo   Webhook: http://localhost:5678/webhook/antigravity-chat
echo   API Docs: http://localhost:5678/docs
echo ===================================================
py -m uvicorn main:app --host 0.0.0.0 --port 5678 --reload
pause
