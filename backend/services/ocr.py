import os
import re
from PIL import Image
from backend.utils import logger

class OCRService:
    def __init__(self, provider: str = "Auto"):
        self.provider = provider

    def extract_text(self, image_path: str) -> str:
        """
        Extract raw text from image using pytesseract (tam+eng) with EasyOCR fallback.
        Preserves raw text in Tamil and English without auto-translating.
        """
        logger.info(f"[OCR] Extracting text from: {os.path.basename(image_path)}")
        ocr_text = ""

        # 1. Try pytesseract with Tamil + English
        try:
            import pytesseract
            with Image.open(image_path) as img:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                text = pytesseract.image_to_string(img, lang="tam+eng").strip()
                if not text:
                    text = pytesseract.image_to_string(img, lang="eng").strip()
                if text:
                    logger.info(f"[OCR] pytesseract extracted {len(text)} chars")
                    ocr_text = text
        except Exception as e:
            logger.info(f"[OCR] pytesseract notice: {str(e)}")

        # 2. Try EasyOCR fallback if pytesseract extracted nothing
        if not ocr_text.strip():
            try:
                import easyocr
                reader = easyocr.Reader(['en'], gpu=False)
                lines = reader.readtext(image_path, detail=0)
                if lines:
                    ocr_text = "\n".join([str(l).strip() for l in lines if str(l).strip()]).strip()
                    logger.info(f"[OCR] EasyOCR extracted {len(ocr_text)} chars")
            except Exception as e:
                logger.info(f"[OCR] EasyOCR ('en') notice: {str(e)}")

        if not ocr_text.strip():
            try:
                import easyocr
                reader = easyocr.Reader(['ta'], gpu=False)
                lines = reader.readtext(image_path, detail=0)
                if lines:
                    ocr_text = "\n".join([str(l).strip() for l in lines if str(l).strip()]).strip()
                    logger.info(f"[OCR] EasyOCR ('ta') extracted {len(ocr_text)} chars")
            except Exception as e:
                logger.info(f"[OCR] EasyOCR ('ta') notice: {str(e)}")

        return ocr_text.strip()

    def detect_language(self, text: str) -> str:
        """
        Detect language of OCR text based on character sets.
        Possible values: English, Tamil, Tamil + English, Other, Unknown
        """
        if not text or not text.strip():
            return "Unknown"

        has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
        has_english = bool(re.search(r'[a-zA-Z]', text))

        if has_tamil and has_english:
            return "Tamil + English"
        elif has_tamil:
            return "Tamil"
        elif has_english:
            return "English"
        elif re.search(r'[0-9]', text):
            return "English"
        return "Unknown"

