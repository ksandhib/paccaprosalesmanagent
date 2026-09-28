@echo off
title PaccaPro AI Sales Analysis System
color 0A

echo ===============================================================
echo    PaccaPro AI Sales Analysis System (PASAS)
echo    Starting Server...
echo ===============================================================
echo.

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Navigate to project directory
cd /d "%~dp0"

REM Install dependencies if needed
if not exist "venv" (
    echo [SETUP] First-time setup - Installing dependencies...
    pip install -r requirements.txt --quiet
    echo [SETUP] Dependencies installed.
    echo.
)

REM Create required directories
if not exist "database" mkdir database
if not exist "uploads" mkdir uploads
if not exist "uploads\voice" mkdir uploads\voice
if not exist "uploads\processed" mkdir uploads\processed
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp
if not exist "models" mkdir models
if not exist "config" mkdir config
if not exist "exports" mkdir exports
if not exist "backups" mkdir backups

echo [OK] Project directories verified.

REM Check Ollama (optional)
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama detected - AI Analysis will use local LLM.
) else (
    echo [INFO] Ollama not found - AI Analysis will use fallback text extraction.
    echo        Install Ollama from https://ollama.com for full AI analysis.
)

echo.
echo ===============================================================
echo    Server starting on: http://127.0.0.1:8000
echo    Open your browser and go to: http://127.0.0.1:8000
echo.
echo    Login: kumar / 1973
echo.
echo    Press Ctrl+C to stop the server.
echo ===============================================================
echo.

REM Start the server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

pause
