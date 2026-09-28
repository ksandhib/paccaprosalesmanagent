@echo off
title PaccaPro AI Sales Analysis System (PASAS) - Startup
echo ======================================================================
echo           PaccaPro AI Sales Analysis System (PASAS) Startup
echo ======================================================================
echo.

:: 1. Verify Python Installation
set "PYTHON_EXE=python"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
        set "PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
        echo Detected User Local Python installation.
    ) else (
        echo [ERROR] Python is not installed or not added to your system PATH.
        echo Please install Python 3.8+ and try again.
        pause
        exit /b 1
    )
)

:: 2. Create folders if they do not exist
echo Creating system directory structure...
if not exist "models" mkdir "models"
if not exist "ollama" mkdir "ollama"
if not exist "python" mkdir "python"
if not exist "ffmpeg" mkdir "ffmpeg"
if not exist "logs" mkdir "logs"
if not exist "database" mkdir "database"
if not exist "uploads" mkdir "uploads"
if not exist "uploads\voice" mkdir "uploads\voice"
if not exist "uploads\processed" mkdir "uploads\processed"
echo Directories verified.
echo.

:: 3. Install Python Dependencies
echo Installing python requirements from requirements.txt...
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies failed to install. Check your internet connection.
)
echo Python requirements verified.
echo.

:: 4. Download Frontend Static Libraries (Offline Integration)
echo Bundling offline frontend assets...
"%PYTHON_EXE%" python/setup_assets.py
if %errorlevel% neq 0 (
    echo [WARNING] Asset bundling failed. Application might run in online-only mode.
)
echo Frontend assets verified.
echo.

:: 5. Launch FastAPI Backend in a separate window
echo Starting FastAPI application server...
start "PASAS Backend Server" cmd /c ""%PYTHON_EXE%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info"

:: Wait 3 seconds for server to start before opening browser
timeout /t 3 /nobreak >nul

:: 6. Open Web Application in default browser
echo Opening PaccaPro AI web interface...
start http://127.0.0.1:8000

echo.
echo ======================================================================
echo PASAS is running. To stop the application, run stop.bat.
echo ======================================================================
echo.
pause
