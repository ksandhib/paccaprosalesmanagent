# paccaprosalesmanagent

## PaccaPro AI Sales Analysis System (PASAS)

AI-powered dashboard and sales analysis tool for PaccaPro.

### Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and set required environment variables.
3. Start the server:
   ```bash
   python backend/main.py
   ```
   or run `START.bat` on Windows.
4. Access the dashboard at `http://127.0.0.1:8000`.

### Features
- Speech-to-Text conversion via ElevenLabs & Whisper
- AI-driven sales call analysis with Ollama (Gemma3:4b)
- Full interactive web dashboard (HTML/JS/CSS)
- Multi-language support (English / Tamil)
