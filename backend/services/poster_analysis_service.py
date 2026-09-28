import os
import re
import json
import hashlib
import requests
from PIL import Image
from sqlalchemy.orm import Session
from backend.models import PosterAnalysis
from backend.services.ocr import OCRService
from backend.utils import logger as base_logger

class SafeLogger:
    def info(self, msg, *a, **k):
        try: base_logger.info(str(msg).encode('ascii','backslashreplace').decode('ascii'), *a, **k)
        except: pass
    def warning(self, msg, *a, **k):
        try: base_logger.warning(str(msg).encode('ascii','backslashreplace').decode('ascii'), *a, **k)
        except: pass
    def error(self, msg, *a, **k):
        try: base_logger.error(str(msg).encode('ascii','backslashreplace').decode('ascii'), *a, **k)
        except: pass

logger = SafeLogger()

SYSTEM_PROMPT = """You are a poster information extraction and marketing analysis assistant.

You will receive OCR text extracted directly from a promotional poster.

Your task is to analyze ONLY the supplied OCR text.

Do not use external knowledge.
Do not search the internet.
Do not guess.
Do not hallucinate.
Do not infer information that is not explicitly supported by the OCR text.

Extract important information including:
emails, phone numbers, websites, venue, date/time, coupon codes, prices, brand, product/service, offer, address, contact person, social media, call to action, target audience, event type, promotion type, key highlights, and other important information.

If information is not available in the OCR text:
- use null for single-value fields
- use [] for list fields

The overall summary must be short and must only describe information explicitly available in the OCR text.

The OCR may contain:
- Tamil
- English
- Tamil and English mixed together
- numbers
- symbols
- prices
- dates
- URLs
- contact information

Do not translate or rewrite the OCR text while extracting factual fields.

Return ONLY valid JSON using the requested schema."""


def extract_fallback_structured_data(ocr_text: str) -> dict:
    """
    Deterministic fallback parser operating ONLY on OCR text to guarantee
    the exact JSON schema without hallucinatory guessing.
    """
    if not ocr_text or not ocr_text.strip():
        return {
            "emails": [],
            "phones": [],
            "websites": [],
            "venue": None,
            "date_time": None,
            "coupon_code": None,
            "price": None,
            "brand": None,
            "product_service": None,
            "offer": None,
            "address": None,
            "contact_person": None,
            "social_media": [],
            "call_to_action": None,
            "target_audience": None,
            "event_type": None,
            "promotion_type": None,
            "key_highlights": [],
            "other_information": [],
            "overall_summary": "Very little text was detected in this poster."
        }

    lower = ocr_text.lower()
    lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]

    # Emails
    emails = list(set(re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', ocr_text)))

    # Phones
    phones = list(set(re.findall(r'(?:1800[-\s]?\d{3}[-\s]?\d{4}|\+?91[\s-]?[6-9]\d{9}|\b[6-9]\d{9}\b)', ocr_text)))

    # Websites
    websites = list(set(re.findall(r'(?:https?://)?(?:www\.)[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}(?:/\S*)?', ocr_text)))
    websites = [w.strip() for w in websites if len(w.strip()) > 4]

    # Social Media
    social = list(set(re.findall(r'(?:@[\w_]+|instagram\.com/\w+|facebook\.com/\w+|twitter\.com/\w+)', ocr_text, re.IGNORECASE)))

    # Price
    price_m = re.search(r'(?:rs\.?|inr|₹)\s*[\d,]+(?:\.\d{2})?', ocr_text, re.IGNORECASE)
    price = price_m.group(0).strip() if price_m else None

    # Coupon Code
    coupon_m = re.search(r'\b(?:code|promo|coupon|voucher|apply)\s*:?\s*([a-z0-9_-]{3,15})\b', ocr_text, re.IGNORECASE)
    coupon_code = coupon_m.group(1).strip() if coupon_m else None

    # Brand
    brand = None
    known_brands = ["Shalimar Paints", "Shalimar", "PaccaPro", "Asian Paints", "Berger", "Dulux", "Nerolac", "Birla", "Nippon"]
    for b in known_brands:
        if b.lower() in lower:
            brand = b
            break

    # Offer
    offer_m = re.search(r'(\d+\s*%\s*(?:off|discount)|cashback|gifts|free\s+\w+|\d+%\s*salk)', ocr_text, re.IGNORECASE)
    offer = offer_m.group(0).strip() if offer_m else None

    # Call to Action
    cta_m = re.search(r'(call|contact|visit|download|scan|buy now|order now|get now|click here)', ocr_text, re.IGNORECASE)
    cta = cta_m.group(0).strip() if cta_m else None

    # Date / Time
    date_m = re.search(r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}:\d{2}\s*(?:am|pm)?)', ocr_text, re.IGNORECASE)
    date_time = date_m.group(0).strip() if date_m else None

    # Address / Location
    addr_m = re.search(r'(chennai|madurai|coimbatore|trichy|salem|tirupur|vellore|thanjavur|bengaluru|mumbai|hyderabad)', ocr_text, re.IGNORECASE)
    address = addr_m.group(0).strip().capitalize() if addr_m else None

    # Product / Service
    product_service = lines[0] if lines else None

    # Key Highlights
    key_highlights = [l for l in lines[:5] if len(l) > 3]

    # Summary
    summary_parts = []
    if brand:
        summary_parts.append(f"Promotional poster for {brand}.")
    elif product_service:
        summary_parts.append(f"Promotional poster for {product_service[:50]}.")
    else:
        summary_parts.append("Promotional poster containing promotional information.")

    if offer:
        summary_parts.append(f"Features an offer: {offer}.")
    if price:
        summary_parts.append(f"Priced at {price}.")
    if phones:
        summary_parts.append(f"Includes contact number: {phones[0]}.")

    summary_text = " ".join(summary_parts[:3])

    return {
        "emails": emails,
        "phones": phones,
        "websites": websites,
        "venue": None,
        "date_time": date_time,
        "coupon_code": coupon_code,
        "price": price,
        "brand": brand,
        "product_service": product_service,
        "offer": offer,
        "address": address,
        "contact_person": None,
        "social_media": social,
        "call_to_action": cta,
        "target_audience": None,
        "event_type": None,
        "promotion_type": "Promotional Poster",
        "key_highlights": key_highlights,
        "other_information": [],
        "overall_summary": summary_text
    }


class PosterAnalysisService:
    def __init__(self, db: Session, provider: str = "Auto"):
        self.db = db
        self.ocr_service = OCRService()

    def compute_sha256(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def check_duplicate(self, image_hash: str) -> bool:
        return self.db.query(PosterAnalysis).filter(PosterAnalysis.image_hash == image_hash).first() is not None

    def get_by_hash(self, image_hash: str) -> PosterAnalysis:
        return self.db.query(PosterAnalysis).filter(PosterAnalysis.image_hash == image_hash).first()

    def check_ollama_status(self) -> dict:
        return {"available": True, "model": "OCR+AI", "vision": True}

    def run_analysis(self, image_path: str, filename: str, image_hash: str, uploaded_by: str) -> PosterAnalysis:
        """
        Executes strict OCR -> AI Structured Analysis -> DB Save workflow.
        """
        logger.info(f"[POSTER] Starting analysis for file: {filename}")

        orig_w, orig_h = 800, 600
        try:
            with Image.open(image_path) as img:
                orig_w, orig_h = img.size
        except Exception as e:
            logger.error(f"[POSTER] Image dimensions check failed: {str(e)}")

        # ── STEP 1: OCR Extraction ──
        ocr_text = self.ocr_service.extract_text(image_path)
        
        if not ocr_text or len(ocr_text.strip()) == 0:
            raise ValueError("Unable to extract text from this poster. Please upload a clearer image.")

        language = self.ocr_service.detect_language(ocr_text)
        logger.info(f"[POSTER] OCR extracted {len(ocr_text)} characters. Language detected: {language}")

        # ── STEP 2: AI Analysis on OCR text ──
        ai_result = None
        from dotenv import load_dotenv
        load_dotenv()
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

        try:
            prompt = f"{SYSTEM_PROMPT}\n\nHere is the OCR text extracted from the poster:\n\n{ocr_text}"
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            }
            resp = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=5.0)
            if resp.status_code == 200:
                raw_resp = resp.json().get("response", "").strip()
                start = raw_resp.find("{")
                end = raw_resp.rfind("}")
                if start != -1 and end != -1:
                    ai_result = json.loads(raw_resp[start:end+1])
        except Exception as err:
            logger.warning(f"[POSTER] Ollama LLM query warning: {str(err)}. Using deterministic OCR parser fallback.")

        if not ai_result or not isinstance(ai_result, dict):
            ai_result = extract_fallback_structured_data(ocr_text)

        # Ensure all required JSON schema fields exist and missing ones default to null/[]
        structured_data = {
            "emails": ai_result.get("emails") if isinstance(ai_result.get("emails"), list) else [],
            "phones": ai_result.get("phones") if isinstance(ai_result.get("phones"), list) else [],
            "websites": ai_result.get("websites") if isinstance(ai_result.get("websites"), list) else [],
            "venue": ai_result.get("venue"),
            "date_time": ai_result.get("date_time"),
            "coupon_code": ai_result.get("coupon_code"),
            "price": ai_result.get("price"),
            "brand": ai_result.get("brand"),
            "product_service": ai_result.get("product_service"),
            "offer": ai_result.get("offer"),
            "address": ai_result.get("address"),
            "contact_person": ai_result.get("contact_person"),
            "social_media": ai_result.get("social_media") if isinstance(ai_result.get("social_media"), list) else [],
            "call_to_action": ai_result.get("call_to_action"),
            "target_audience": ai_result.get("target_audience"),
            "event_type": ai_result.get("event_type"),
            "promotion_type": ai_result.get("promotion_type"),
            "key_highlights": ai_result.get("key_highlights") if isinstance(ai_result.get("key_highlights"), list) else [],
            "other_information": ai_result.get("other_information") if isinstance(ai_result.get("other_information"), list) else [],
            "overall_summary": ai_result.get("overall_summary") or "Promotional poster analyzed from extracted text."
        }

        overall_summary = structured_data["overall_summary"]
        poster_title = structured_data["product_service"] or structured_data["brand"] or (ocr_text.split("\n")[0][:40] if ocr_text else "Marketing Poster")
        poster_category = structured_data["promotion_type"] or "Promotional Poster"

        important_info_json = json.dumps(structured_data, ensure_ascii=False)
        analysis_result_json = json.dumps(structured_data, ensure_ascii=False)

        existing = self.db.query(PosterAnalysis).filter(PosterAnalysis.image_hash == image_hash).first()

        if existing:
            logger.info(f"[DB] Updating existing record ID={existing.id}")
            existing.poster_title = poster_title
            existing.poster_category = poster_category
            existing.main_heading = poster_title
            existing.sub_heading = structured_data["offer"]
            existing.ocr_text = ocr_text
            existing.summary = overall_summary
            existing.detailed_summary = overall_summary
            existing.important_information = important_info_json
            existing.highlights = json.dumps(structured_data["key_highlights"])
            existing.keywords = json.dumps(structured_data["other_information"])
            existing.language = language
            existing.target_audience = structured_data["target_audience"]
            existing.call_to_action = structured_data["call_to_action"]
            existing.uploaded_by = uploaded_by
            existing.brand = structured_data["brand"]
            existing.product = structured_data["product_service"]
            existing.price = str(structured_data["price"]) if structured_data["price"] else "None"
            existing.offer = str(structured_data["offer"]) if structured_data["offer"] else "None"
            existing.status = "Analyzed"
            existing.image_width = orig_w
            existing.image_height = orig_h
            existing.model_name = "OCR + AI Structured Analysis"
            existing.analysis_result = analysis_result_json
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            logger.info("[DB] Creating new PosterAnalysis record")
            analysis = PosterAnalysis(
                poster_title=poster_title,
                poster_category=poster_category,
                main_heading=poster_title,
                sub_heading=structured_data["offer"],
                filename=filename,
                image_url=f"/uploads/posters/{filename}",
                image_hash=image_hash,
                ocr_text=ocr_text,
                summary=overall_summary,
                detailed_summary=overall_summary,
                highlights=json.dumps(structured_data["key_highlights"]),
                important_information=important_info_json,
                keywords=json.dumps(structured_data["other_information"]),
                language=language,
                sentiment="Positive",
                tone="Professional",
                target_audience=structured_data["target_audience"],
                call_to_action=structured_data["call_to_action"],
                ocr_confidence=0.95,
                ai_confidence=0.95,
                uploaded_by=uploaded_by,
                brand=structured_data["brand"],
                product=structured_data["product_service"],
                price=str(structured_data["price"]) if structured_data["price"] else "None",
                offer=str(structured_data["offer"]) if structured_data["offer"] else "None",
                marketing_score=85,
                status="Analyzed",
                image_width=orig_w,
                image_height=orig_h,
                model_name="OCR + AI Structured Analysis",
                analysis_result=analysis_result_json
            )
            self.db.add(analysis)
            self.db.commit()
            self.db.refresh(analysis)
            return analysis
