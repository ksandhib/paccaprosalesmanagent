@echo off
title PaccaPro AI - Installation
echo ======================================================================
echo           Installing PaccaPro AI System Dependencies
echo ======================================================================
echo.

:: Resolve Python path
set "PYTHON_EXE=python"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
        set "PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
        echo Detected User Local Python installation.
    ) else (
        echo [ERROR] Python is not installed or not added to your system PATH.
        echo Please install Python 3.8+ first and try again.
        pause
        exit /b 1
    )
)

echo Using Python path: "%PYTHON_EXE%"
echo Installing/upgrading requirements...
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r requirements.txt --force-reinstall
if %errorlevel% equ 0 (
    echo.
    echo Dependency installation completed successfully!
) else (
    echo.
    echo [ERROR] Dependency installation failed. Please check internet connection.
)
pause
