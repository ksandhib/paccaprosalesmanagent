@echo off
title PaccaPro - First Time Setup
color 0E

echo ===============================================================
echo    PaccaPro AI - FIRST TIME SETUP
echo    This will install all required dependencies.
echo ===============================================================
echo.

cd /d "%~dp0"

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please install Python 3.11 or higher:
    echo   1. Go to https://www.python.org/downloads/
    echo   2. Download Python 3.11+
    echo   3. IMPORTANT: Check "Add Python to PATH" during installation
    echo   4. Run this setup again after installing Python
    echo.
    pause
    exit /b 1
)

echo [1/4] Python found:
python --version
echo.

echo [2/4] Installing Python dependencies...
pip install -r requirements.txt
echo.

echo [3/4] Creating project directories...
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
if not exist "ffmpeg" mkdir ffmpeg
echo    Directories created.
echo.

echo [4/4] Checking FFmpeg...
if exist "ffmpeg\ffmpeg.exe" (
    echo    FFmpeg found at ffmpeg\ffmpeg.exe
) else (
    echo    [WARNING] FFmpeg not found in ffmpeg\ folder.
    echo    MP3 audio conversion requires FFmpeg.
    echo    Download from: https://ffmpeg.org/download.html
    echo    Place ffmpeg.exe in the ffmpeg\ folder.
)
echo.

echo ===============================================================
echo    SETUP COMPLETE!
echo.
echo    To start the server, double-click: START.bat
echo    Then open: http://127.0.0.1:8000
echo    Login: kumar / 1973
echo.
echo    OPTIONAL: Install Ollama for AI Analysis
echo    Download from: https://ollama.com
echo    Then run: ollama pull gemma3:4b
echo ===============================================================
echo.
pause
