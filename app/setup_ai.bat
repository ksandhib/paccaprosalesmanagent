@echo off
title PaccaPro Local AI Environment Setup
echo ======================================================================
echo           PaccaPro Local AI Auto-Setup Script
echo ======================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_ai.ps1"

echo.
echo ======================================================================
echo Setup run finished. Press any key to exit.
echo ======================================================================
pause >nul
