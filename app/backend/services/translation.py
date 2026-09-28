import os
import json
import requests
from backend.utils import logger

class TranslationService:
    def __init__(self):
        # Load settings from config/config.json and .env if available
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.json"))
        self.ollama_url = "http://localhost:11434"
        self.ollama_model = "qwen2.5:14b"
        self.translation_model = "nllb-200"

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                    self.ollama_url = cfg.get("ollama_url", self.ollama_url)
                    self.ollama_model = cfg.get("ollama_model", self.ollama_model)
                    self.translation_model = cfg.get("translation_model", self.translation_model)
            except:
                pass

        # Fallback check for .env
        from dotenv import load_dotenv
        load_dotenv()
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", self.ollama_url)
        self.ollama_model = os.getenv("OLLAMA_MODEL", self.ollama_model)
        self.translation_model = os.getenv("TRANSLATION_MODEL", self.translation_model)

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
        """
        Translates text from source language (like Tamil) to English.
        Tries local NLLB-200. Falls back to local Ollama LLM if NLLB is not initialized,
        and finally to a basic dictionary lookup if offline.
        """
        if not text or text.strip() == "":
            return text

        # 1. Try NLLB-200 dynamic load
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            logger.info("Initializing local NLLB-200 translation model...")
            model_path = os.path.abspath(os.path.join("models", "translation"))
            if os.path.exists(model_path) and os.listdir(model_path):
                tokenizer = AutoTokenizer.from_pretrained(model_path)
                model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
                
                src_code = "tam_Taml" if source_lang == "ta" else "eng_Latn"
                tgt_code = "eng_Latn" if target_lang == "en" else "tam_Taml"
                
                inputs = tokenizer(text, return_tensors="pt")
                translated_tokens = model.generate(
                    **inputs, forced_bos_token_id=tokenizer.lang_code_to_id[tgt_code], max_length=128
                )
                res = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
                logger.info(f"NLLB Translated text: {res}")
                return res
        except Exception:
            pass

        # 2. Fallback to Local Ollama LLM translation (highly resource-efficient CPU option)
        try:
            logger.info(f"Translating text using local Ollama model '{self.ollama_model}'...")
            prompt = f"Translate the following text to English. Return only the translated English text, without explanation or commentary.\n\nText: {text}"
            response = requests.post(
                f"{self.ollama_url.rstrip('/')}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120.0
            )
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                logger.info(f"Ollama translated text: {result}")
                return result
        except Exception as e:
            logger.warning(f"Ollama translation fallback failed: {str(e)}")

        # 3. Simple static dictionary lookup fallback
        translations = {
            "namaste": "hello",
            "shukriya": "thank you",
            "vanakkam": "hello / greetings"
        }
        
        words = text.split()
        translated_words = []
        for word in words:
            clean_word = word.lower().strip(",.!?")
            if clean_word in translations:
                translated_words.append(translations[clean_word])
            else:
                translated_words.append(word)
                
        return " ".join(translated_words)
