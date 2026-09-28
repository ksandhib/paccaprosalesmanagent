@echo off
title PaccaPro AI - Restart
echo ======================================================================
echo           Restarting PaccaPro AI Sales Analysis System
echo ======================================================================
echo.

echo Step 1: Stopping all active backend server processes...
call stop.bat

echo.
echo Step 2: Restarting backend server and launching UI...
call start.bat

exit /b 0
