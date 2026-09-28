==========================================================================
PaccaPro AI Sales Analysis System (PASAS) - Documentation
==========================================================================

PaccaPro AI Sales Analysis System (PASAS) is a lightweight, offline-first,
AI-powered Sales Analysis Web Application designed to transcribe, translate, 
and analyze client meeting voice recordings completely locally.

--------------------------------------------------------------------------
1. PROJECT FOLDER STRUCTURE
--------------------------------------------------------------------------
PaccaPro-AI/
├── frontend/             # Single Page Application (HTML, CSS, JS)
│   ├── css/              # Custom stylesheets (style.css)
│   ├── js/               # Main interaction logic (app.js)
│   ├── lib/              # Bundled offline libraries (Bootstrap, DataTables, etc.)
│   └── index.html        # Main app template
├── backend/              # FastAPI Application Source Code
│   ├── routes/           # REST API endpoints (auth, dashboard, reports, upload, chat)
│   ├── services/         # Modular AI Pipeline Stubs (speech, analysis, embedding, etc.)
│   ├── main.py           # Entry point and database seeding
│   ├── models.py         # SQLAlchemy models (SQLite Tables)
│   ├── schemas.py        # Pydantic validation structures
│   └── utils.py          # Security, password hashing, and logging
├── database/             # Contains SQLite database.db (auto-created)
├── uploads/              # Storage path for file uploads
│   ├── voice/            # Raw recordings uploaded by users
│   └── processed/        # Audio recordings processed by AI services
├── models/               # Place your local Whisper models here (e.g., ggml models)
├── ollama/               # Location for local Ollama configuration or model files
├── python/               # Contains setup_assets.py download utility
├── ffmpeg/               # Place FFmpeg binaries here (ffmpeg.exe, ffprobe.exe)
├── logs/                 # Contains app.log file
├── config/               # System configurations (config.json)
├── start.bat             # Windows Startup Script
├── stop.bat              # Windows Stop/Shutdown Script
├── requirements.txt      # Python dependencies
├── .env                  # Environment secret settings
└── README.txt            # This documentation file

--------------------------------------------------------------------------
2. SYSTEM SETUP & RUNNING
--------------------------------------------------------------------------
To start the application:
1. Double-click the 'start.bat' script.
   The script will:
   - Check and verify your Python installation.
   - Install required packages in your system environment.
   - Download Bootstrap, jQuery, Chart.js, and DataTables libraries into
     'frontend/lib/' to prepare the interface for 100% offline use.
   - Launch the FastAPI server in a separate background window.
   - Open your default web browser to: http://localhost:8000
   
2. Log in with the default credentials:
   - Username: kumar
   - Password: 1973
   (No internet connection or registration is required).

To stop the application:
1. Double-click the 'stop.bat' script to kill the active Uvicorn backend process.

--------------------------------------------------------------------------
3. ADDING LOCAL AI MODELS (FOR PRODUCTION DEPLOYMENT)
--------------------------------------------------------------------------
The pipeline is designed with a clean, modular service layer. To transition 
from the built-in heuristic/template engine to live local AI processing:

A. Audio Transcription (Whisper)
   1. Install 'faster-whisper' via pip:
      pip install faster-whisper
   2. Download a Whisper model (e.g., 'base' or 'small') and copy it to the 
      'models/' folder.
   3. Update 'backend/services/speech.py' to load the local Whisper model:
      from faster_whisper import WhisperModel
      self.model = WhisperModel("base", device="cpu", download_root="models")

B. Local LLM / Chat / Structured Extraction (Ollama or llama.cpp)
   1. Install Ollama locally (https://ollama.com).
   2. Pull a local model, such as Llama3 or Mistral:
      ollama pull llama3:8b
   3. Ollama runs by default at http://localhost:11434 (configured in 'config.json').
   4. Update 'backend/services/analysis.py' or 'chat_service.py' to send 
      structured system prompts to your local Ollama instance using the 
      'requests' library to parse JSON outputs.

C. Audio Processing (FFmpeg)
   To handle multiple audio formats (m4a, ogg, wav) with Whisper:
   1. Download FFmpeg static builds for Windows.
   2. Extract and copy 'ffmpeg.exe' and 'ffprobe.exe' to the 'ffmpeg/' folder.
   3. Add the 'ffmpeg/' directory path to your system Environment Variables, or 
      configure your service wrapper to reference the binary in this folder.

--------------------------------------------------------------------------
4. TROUBLESHOOTING
--------------------------------------------------------------------------
- "Port 8000 already in use": Run 'stop.bat' or check if another web server is 
  running on port 8000.
- "Python is not recognized": Install Python (version 3.8 or higher is recommended) 
  and check the "Add Python to PATH" box during installation.
- Interface doesn't load styles: Ensure the 'start.bat' has successfully run 
  the 'python/setup_assets.py' script while connected to the internet during the 
  first startup to download libraries locally.
- Logs: Check 'logs/app.log' for detailed backend errors.
==========================================================================
