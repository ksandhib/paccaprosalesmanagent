@echo off
title PaccaPro AI - Software Update
echo ======================================================================
echo           Updating PaccaPro AI Sales Analysis System
echo ======================================================================
echo.

:: Check if git is initialized in directory
git --version >nul 2>&1
if %errorlevel% equ 0 (
    if exist ".git" (
        echo Git repository detected. Pulling software updates...
        git pull
    ) else (
        echo Code folder is not a Git repository clone. Skipping code pull.
    )
) else (
    echo Git command not found in path. Skipping repository pull.
)

echo.
echo Re-running package dependency installation...
call install.bat
