# PaccaPro AI Sales Analysis System (PASAS)
## Deployment Guide for Company Setup

---

## Quick Start (Single Click)

1. Double-click **`START.bat`** to run the server
2. Open browser: **http://127.0.0.1:8000**
3. Login: **kumar** / **1973**

---

## First Time Setup on a New Computer

### Step 1: Install Python 3.11+
- Download from: https://www.python.org/downloads/
- **IMPORTANT**: Check ✅ "Add Python to PATH" during installation

### Step 2: Install Ollama (Optional - for AI Analysis)
- Download from: https://ollama.com
- After installing, open Command Prompt and run:
```
ollama pull gemma3:4b
```

### Step 3: Run Setup
- Double-click **`SETUP.bat`** — this installs all Python dependencies

### Step 4: Start the Server
- Double-click **`START.bat`**
- Open **http://127.0.0.1:8000** in your browser

---

## Project Folder Structure

```
pacca_ai_dashboard/
├── START.bat              ← Double-click to run
├── SETUP.bat              ← First-time setup
├── requirements.txt       ← Python dependencies
├── .env                   ← Configuration (API keys, credentials)
│
├── backend/               ← Python FastAPI server
│   ├── main.py            ← Application entry point
│   ├── models.py          ← Database models
│   ├── database.py        ← SQLite connection
│   ├── routes/            ← API endpoints
│   └── services/          ← Business logic (speech, analysis, sync)
│
├── frontend/              ← HTML/CSS/JS dashboard
│   ├── index.html         ← Main page
│   ├── css/               ← Stylesheets
│   └── js/                ← JavaScript (app.js)
│
├── config/                ← Configuration files
│   └── config.json        ← System settings
│
├── database/              ← SQLite database (auto-created)
│   └── database.db
│
├── uploads/               ← Voice recordings storage
│   ├── voice/             ← Uploaded audio files
│   └── processed/         ← Processed files
│
├── ffmpeg/                ← FFmpeg portable (for MP3 conversion)
│   └── ffmpeg.exe
│
├── models/                ← AI models cache
└── logs/                  ← Application logs
```

---

## Configuration (.env file)

Edit `.env` to customize:

```env
# Server
PORT=8000
HOST=127.0.0.1

# Login Credentials
DEFAULT_USERNAME=kumar
DEFAULT_PASSWORD=1973

# ElevenLabs Speech-to-Text API
ELEVENLABS_API_KEY=sk_your_api_key_here
ELEVENLABS_STT_MODEL=scribe_v2

# Ollama AI (local)
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b
```

---

## Company Network Deployment

### Option A: Single Computer (Simplest)
- Install on one computer
- Run `START.bat`
- Access at `http://127.0.0.1:8000`

### Option B: Local Network (Multiple Users)
1. Change `HOST` in `.env`:
   ```
   HOST=0.0.0.0
   ```
2. Run `START.bat`
3. Find the computer's IP (run `ipconfig` in Command Prompt)
4. Other users access: `http://<computer-ip>:8000`
5. **Firewall**: Allow port 8000 in Windows Firewall

### Option C: Cloud Server (Remote Access)
1. Get a Windows VPS (AWS, Azure, DigitalOcean)
2. Copy the entire `pacca_ai_dashboard` folder to the server
3. Run `SETUP.bat` then `START.bat`
4. Configure domain/SSL with nginx reverse proxy

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 11 |
| Python | 3.11+ | 3.11+ |
| RAM | 4 GB | 8 GB+ |
| Disk | 2 GB | 10 GB+ |
| Ollama | Optional | gemma3:4b |
| Internet | Required for ElevenLabs STT | Required |

---

## Features

- 🎙️ **Voice Upload** — Upload WhatsApp/MP3/WAV recordings
- 🗣️ **Tamil Speech-to-Text** — ElevenLabs Scribe API (Tamil)
- 🤖 **AI Analysis** — 10-category business analysis via Ollama
- 📊 **Live Dashboard** — Real-time sales metrics
- 📋 **Reports** — PDF/Excel/CSV export
- 🖼️ **Poster Analysis** — OCR + AI analysis of marketing posters
- 🌐 **Bilingual** — English & Tamil interface
- 🌙 **Dark/Light Theme** — Toggle display mode
