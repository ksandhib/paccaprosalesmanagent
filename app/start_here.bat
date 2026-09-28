@echo off
title PaccaPro AI - D:\pacca_ai_dashboard
echo Setting Ollama model path...
set OLLAMA_MODELS=D:\pacca_ai_dashboard\ai_models
echo Starting PaccaPro AI server...
cd /d "D:\pacca_ai_dashboard\app"
"%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info
pause
