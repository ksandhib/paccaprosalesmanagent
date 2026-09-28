import os
import json
import requests
from fastapi import APIRouter, Depends
from backend.utils import get_current_user, logger

router = APIRouter(tags=["models"])

# Config paths
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.json"))
MODELS_DIR = "models"
OLLAMA_URL = "http://127.0.0.1:11434"

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
            MODELS_DIR = cfg.get("models_path", MODELS_DIR)
            OLLAMA_URL = cfg.get("ollama_url", OLLAMA_URL)
    except:
        pass

SUPPORTED_ARCHITECTURES = ["qwen", "llama", "gemma", "deepseek", "mistral"]

@router.get("/ai-models")
def get_available_models(current_user: str = Depends(get_current_user)):
    """
    Scans the models/ directory and queries the local Ollama service to detect available models.
    """
    logger.info("Scanning for available AI models...")
    detected_models = []
    
    # 1. Scan the local models/ directory
    os.makedirs(MODELS_DIR, exist_ok=True)
    try:
        for file in os.listdir(MODELS_DIR):
            file_lower = file.lower()
            # Look for model files (gguf, bin, etc.)
            if any(file_lower.endswith(ext) for ext in [".gguf", ".bin", ".pt", ".onnx"]):
                for arch in SUPPORTED_ARCHITECTURES:
                    if arch in file_lower:
                        detected_models.append({
                            "name": file,
                            "type": "Local File (.gguf)",
                            "family": arch.capitalize(),
                            "path": os.path.abspath(os.path.join(MODELS_DIR, file))
                        })
                        break
    except Exception as e:
        logger.error(f"Error scanning local models/ directory: {str(e)}")

    # 2. Query the local Ollama API tags endpoint (if running)
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if response.status_code == 200:
            ollama_data = response.json()
            models_list = ollama_data.get("models", [])
            for m in models_list:
                m_name = m.get("name", "")
                m_name_lower = m_name.lower()
                
                # Check model family
                family = "Unknown"
                for arch in SUPPORTED_ARCHITECTURES:
                    if arch in m_name_lower:
                        family = arch.capitalize()
                        break
                
                detected_models.append({
                    "name": m_name,
                    "type": "Ollama Service",
                    "family": family,
                    "details": m.get("details", {})
                })
        else:
            logger.warning(f"Ollama server returned code {response.status_code}")
    except requests.exceptions.RequestException:
        # Silently catch Ollama service offline exception (offline portable fallback)
        logger.info("Ollama local service is offline or not installed.")

    # 3. Select first model or configure feedback
    if not detected_models:
        return {
            "status": "empty",
            "message": "No local AI model found. Please place a supported model inside the models folder.",
            "models": []
        }
    
    # Select first model as default
    default_selected = detected_models[0]["name"]
    return {
        "status": "success",
        "models": detected_models,
        "selected": default_selected
    }

@router.get("/ai-health")
def get_ai_health():
    """
    Checks the status of the local AI components: Ollama, Qwen, Whisper, Translation, and Embeddings.
    """
    ollama_status = "OFFLINE"
    qwen_status = "MISSING"
    whisper_status = "MISSING"
    translation_status = "MISSING"
    embeddings_status = "MISSING"
    
    # 1. Check Ollama & LLM / Embeddings
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if response.status_code == 200:
            ollama_status = "ONLINE"
            models_list = response.json().get("models", [])
            model_names = [m.get("name", "").lower() for m in models_list]
            
            # Check Qwen model presence
            for m in model_names:
                if "qwen" in m or "llama" in m:
                    qwen_status = "AVAILABLE"
                if "nomic" in m or "embed" in m:
                    embeddings_status = "AVAILABLE"
    except Exception:
        pass
        
    # 2. Check Whisper library presence
    try:
        import faster_whisper
        whisper_status = "AVAILABLE"
    except ImportError:
        whisper_dir = os.path.abspath("models/whisper")
        if os.path.exists(whisper_dir) and os.listdir(whisper_dir):
            whisper_status = "AVAILABLE"
            
    # 3. Check Translation library presence
    try:
        import transformers
        translation_status = "AVAILABLE"
    except ImportError:
        trans_dir = os.path.abspath("models/translation")
        if os.path.exists(trans_dir) and os.listdir(trans_dir):
            translation_status = "AVAILABLE"
        else:
            if ollama_status == "ONLINE" and qwen_status == "AVAILABLE":
                translation_status = "AVAILABLE"

    return {
        "ollama": ollama_status,
        "qwen": qwen_status,
        "whisper": whisper_status,
        "translation": translation_status,
        "embeddings": embeddings_status
    }

