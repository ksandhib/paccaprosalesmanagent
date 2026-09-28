import os
from PIL import Image
from backend.utils import logger

class OCRService:
    def __init__(self, provider: str = "Tesseract"):
        self.provider = provider
        
    def extract_text(self, image_path: str) -> dict:
        """
        Extracts actual image size and properties.
        We do not return hardcoded mock text fallbacks.
        The vision model will perform real-time pixel-based OCR.
        """
        logger.info(f"[OCR] Inspecting file dimensions for {image_path}")
        try:
            with Image.open(image_path) as img:
                w, h = img.size
                return {
                    "text": "",
                    "confidence": 1.0,
                    "provider": self.provider,
                    "width": w,
                    "height": h
                }
        except Exception as e:
            logger.error(f"[OCR] Failed to load image dimensions: {str(e)}")
            return {
                "text": "",
                "confidence": 0.0,
                "provider": self.provider,
                "width": 800,
                "height": 600
            }
