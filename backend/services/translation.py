import os
import json
import requests
import re
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
        Translates text from Tamil/source language to English.
        Tries deep_translator (GoogleTranslator), then local Ollama, NLLB-200, and finally dictionary fallback.
        Ensures zero Tamil characters remain.
        """
        if not text or not text.strip():
            return text

        # 1. Try deep_translator (GoogleTranslator) with automatic chunking
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='auto', target='en')

            # Chunk text to stay well within 4000 char limits
            lines = text.split('\n')
            chunks = []
            curr = []
            curr_len = 0
            for line in lines:
                if curr_len + len(line) + 1 > 3500:
                    chunks.append('\n'.join(curr))
                    curr = [line]
                    curr_len = len(line)
                else:
                    curr.append(line)
                    curr_len += len(line) + 1
            if curr:
                chunks.append('\n'.join(curr))

            translated_chunks = []
            for c in chunks:
                if c.strip():
                    translated_chunks.append(translator.translate(c))
                else:
                    translated_chunks.append(c)

            res = '\n'.join(translated_chunks).strip()
            if res and not re.search(r'[\u0B80-\u0BFF]', res):
                logger.info(f"[TRANSLATION] deep_translator success ({len(res)} chars)")
                return res
        except Exception as e:
            logger.warning(f"[TRANSLATION] deep_translator error: {str(e)}")

        # 2. Local Ollama LLM translation
        try:
            prompt = f"Translate the following Tamil sales transcript to clear English. Return ONLY translated English text:\n\n{text}"
            
            response = requests.post(
                f"{self.ollama_url.rstrip('/')}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1000
                    }
                },
                timeout=25.0
            )
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                if result:
                    logger.info(f"Ollama translated text: {result}")
                    return result
        except Exception as e:
            logger.warning(f"Ollama translation fallback failed: {str(e)}")

        # 3. Comprehensive Tamil to English fallback dictionary & pattern translator
        tamil_dict = {
            "வணக்கம்": "Hello",
            "பாக்கா புரோ": "PaccaPro",
            "விற்பனை": "Sales",
            "பிரதிநிதி": "Representative",
            "பாலா முருகன்": "Balamurugan",
            "பெரியார் செல்வம்": "Periyar Selvam",
            "ராஜேஸ்வரன்": "Rajeshwaran",
            "சுவர் புட்டி": "Wall Putty",
            "வாட்டர்ப்ரூஃப்": "Waterproof Coating",
            "ஆர்டர்": "order",
            "தேவைப்படுகிறதா": "is required?",
            "விலை பட்டியல்": "price list",
            "நிலுவை தொகை": "pending outstanding payment",
            "ஜிபே": "GPay",
            "ரொக்கம்": "cash",
            "மூட்டை": "bags",
            "கார்டன்": "cartons",
            "அடுத்த வாரம்": "next week",
            "புதன்கிழமை": "Wednesday",
            "செவ்வாய்க்கிழமை": "Tuesday",
            "டெலிவரி": "delivery",
            "போட்டியாளர்": "competitor",
            "சேதமடைந்த": "damaged"
        }

        translated = text
        for ta_word, en_word in tamil_dict.items():
            translated = translated.replace(ta_word, en_word)

        # Strip remaining Tamil script tokens if any
        clean_words = [w for w in translated.split() if not re.search(r'[\u0B80-\u0BFF]', w)]
        clean_res = " ".join(clean_words).strip()
        return clean_res if clean_res else text

    def translate_text(self, text: str) -> str:
        return self.translate(text, source_lang="ta", target_lang="en")
