@echo off
title PaccaPro AI Sales Analysis System (PASAS) - Stop
echo ======================================================================
echo           Stopping PaccaPro AI Sales Analysis System (PASAS)
echo ======================================================================
echo.

echo Searching for running backend server processes on port 8000...
set "pid_found="

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    set "pid_found=%%a"
    echo Found process ID: %%a. Terminating...
    taskkill /F /PID %%a >nul 2>&1
    if %errorlevel% equ 0 (
        echo Process terminated successfully.
    ) else (
        echo Failed to terminate process. It may require Administrator privileges.
    )
)

if not defined pid_found (
    echo No active PASAS server detected on port 8000.
)

echo.
echo ======================================================================
echo System shutdown complete.
echo ======================================================================
echo.
pause
