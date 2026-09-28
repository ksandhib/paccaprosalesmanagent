# PaccaPro Local AI Setup & Config Guide

This guide describes how to configure the offline-first Local AI components of the PaccaPro Sales Analysis System.

## Architecture Pipeline
All components operate completely locally without external cloud dependencies:
```
Audio Sync -> ffmpeg normalization -> faster-whisper (STT) -> Translation (Ollama/NLLB) -> LLM (Ollama Qwen2.5 14B) -> DB
```

## System Requirements & Hardware Warnings
- **RAM**: Minimum 16 GB (20 GB or higher recommended).
- **GPU**: NVIDIA GPU with CUDA support is recommended for accelerated Whisper transcription and LLM inference.
- **CPU Fallback**: If no Nvidia GPU is detected, the pipeline automatically executes on the CPU. Note that CPU execution of `qwen2.5:14b` may be slow.

## Model Configuration
You can customize the model configurations by modifying `config/config.json` or by defining the following environment variables in `.env`:

```ini
# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b

# Whisper config
WHISPER_MODEL=large-v3

# Translation model config
TRANSLATION_MODEL=nllb-200
```

## Quick Start Setup
1. **Ollama**: Ensure Ollama Desktop is installed and running on your system.
2. **Execute Setup**: Double-click `setup_ai.bat` in the root folder.
   - The setup script will scan your hardware (RAM, CPU, GPU).
   - It will check if `qwen2.5:14b` and `nomic-embed-text` are installed in Ollama.
   - If missing, it will automatically pull the models locally.
   - It will execute diagnostic pipeline tests and generate a report under `logs/setup_report.txt`.

## Offline Fallbacks & Safety
If any AI model is missing, or if the Ollama service goes offline, the system is designed to gracefully fallback:
- **Transcription**: Fallbacks to high-fidelity template structures.
- **Translation**: Fallbacks to pass-through or manual keyword mappings.
- **LLM parsing**: Fallbacks to regex-based heuristic data extractors.
The system will **never crash** or block manual submissions during offline states.
