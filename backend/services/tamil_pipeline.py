import os
import json
import re
import hashlib
import requests
import time
from dotenv import load_dotenv
from backend.utils import logger

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

class TamilPipeline:
    def __init__(self):
        self.ollama_url = OLLAMA_BASE_URL
        self.ollama_model = OLLAMA_MODEL

    def clean_transcript(self, raw_transcript: str) -> str:
        original_len = len(raw_transcript)
        
        lines = raw_transcript.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove meaningless bare "Speaker X:" labels
            if re.match(r'^Speaker \d+:$', line):
                continue
            
            # Remove repeated consecutive words (ASR stutter)
            words = line.split()
            if words:
                cleaned_words = [words[0]]
                for word in words[1:]:
                    if word.strip('.,!?').lower() != cleaned_words[-1].strip('.,!?').lower():
                        cleaned_words.append(word)
                line = ' '.join(cleaned_words)
            
            cleaned_lines.append(line)
        
        # Remove obviously repeated lines
        final_lines = []
        for line in cleaned_lines:
            if not final_lines or line != final_lines[-1]:
                final_lines.append(line)
                
        cleaned_transcript = '\n'.join(final_lines)
        
        logger.info(f"[STT_CLEANED] Cleaned transcript: {len(cleaned_transcript)} chars from {original_len} chars")
        return cleaned_transcript

    def extract_topics(self, cleaned_transcript: str, representative: str, client_name: str) -> dict:
        prompt = f"""
You are an expert business analyst AI parsing a spoken conversation transcript.
The transcript is primarily in conversational Tamil (Tamil text or mixed Tamil-English).
Your goal is to extract information into a STRICT JSON format for a dashboard.

IMPORTANT RULES:
1. ONLY use information present in the transcript. DO NOT hallucinate.
2. If a topic is not mentioned, set its rating to 0, emotion to "Neutral", and details to "Not Mentioned".
3. A rating of 0 means "Not Discussed". A rating of 1 to 5 means it was discussed (1=very bad, 5=very good).
4. Extract relevant evidence in Tamil.
5. Identify Tamil numbers: ஆயிரம் (thousand), லட்சம் (lakh), etc. 
   Examples: 
   - "ஆர்டர்" = order
   - "கலெக்ஷன்" = collection
   - "ஸ்டாக்" = stock
   - "பெண்டிங்" = pending

Representative: {representative}
Client Name: {client_name}

Transcript:
{cleaned_transcript}

Respond ONLY with valid JSON matching this schema:
{{
  "summary": "Brief English summary of the conversation",
  "overall_emotion": "Positive|Neutral|Negative",
  "overall_rating": 3,
  "priority": "Low|Medium|High",
  "topics": {{
    "sales": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": []
    }},
    "collection": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": [],
      "total_amount": null,
      "pending_amount": null,
      "overdue_amount": null,
      "payment_method": null,
      "payment_status": null
    }},
    "competition": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": [],
      "competitors": []
    }},
    "product": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": [],
      "products": []
    }},
    "price_list": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": []
    }},
    "our_services": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": [],
      "services": []
    }},
    "our_new_products": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": [],
      "products": []
    }},
    "most_sell_products": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": [],
      "products": []
    }},
    "pending_stock": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": []
    }},
    "follow_up_date": {{
      "rating": 0,
      "emotion": "Neutral",
      "summary": "Not Mentioned",
      "details": "Not Mentioned",
      "evidence": [],
      "date": null
    }}
  }},
  "important_points": []
}}
"""
        logger.info("[AI_EXTRACTION_INPUT] Sending to Ollama...")
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "num_predict": 2048,
                "temperature": 0.1
            }
        }
        
        for attempt in range(2):
            try:
                response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()
                logger.info("[AI_EXTRACTION_OUTPUT] Received response from Ollama")
                return json.loads(data["response"])
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(2)
                
        logger.warning("Ollama extraction failed after 2 attempts. Falling back to regex.")
        return self.regex_fallback_extract(cleaned_transcript, representative, client_name)

    def regex_fallback_extract(self, cleaned_transcript: str, representative: str, client_name: str) -> dict:
        text_lower = cleaned_transcript.lower()
        
        result = {
            "summary": "Fallback extraction used due to AI failure.",
            "overall_emotion": "Neutral",
            "overall_rating": 3,
            "priority": "Medium",
            "topics": {
                topic: {
                    "rating": 0,
                    "emotion": "Neutral",
                    "summary": "Not Mentioned",
                    "details": "Not Mentioned",
                    "evidence": []
                } for topic in [
                    "sales", "collection", "competition", "product", "price_list",
                    "our_services", "our_new_products", "most_sell_products", "pending_stock", "follow_up_date"
                ]
            },
            "important_points": []
        }
        
        result["topics"]["collection"].update({
            "total_amount": None, "pending_amount": None, "overdue_amount": None, "payment_method": None, "payment_status": None
        })
        result["topics"]["competition"].update({"competitors": []})
        result["topics"]["product"].update({"products": []})
        result["topics"]["our_services"].update({"services": []})
        result["topics"]["our_new_products"].update({"products": []})
        result["topics"]["most_sell_products"].update({"products": []})
        result["topics"]["follow_up_date"].update({"date": None})
        
        # Collection: Tamil number words + currency patterns
        parsed_amounts = []
        aayiram = re.findall(r'(\d+)\s*(?:ஆயிரம்|thousand|k|ஆயிரம)', cleaned_transcript, re.IGNORECASE)
        for m in aayiram:
            parsed_amounts.append(int(float(m) * 1000))
        lakh = re.findall(r'(\d+(?:\.\d+)?)\s*(?:லட்சம்|லட்சம|lakh|lakhs|lac)', cleaned_transcript, re.IGNORECASE)
        for m in lakh:
            parsed_amounts.append(int(float(m) * 100000))
        currency = re.findall(r'(?:₹|rs\.?|inr)\s*(\d{1,3}(?:,\d{3})+|\d{4,7})', cleaned_transcript, re.IGNORECASE)
        for m in currency:
            parsed_amounts.append(int(m.replace(",", "")))
        
        if parsed_amounts:
            coll = result["topics"]["collection"]
            coll["rating"] = 3
            coll["total_amount"] = parsed_amounts[0]
            coll["pending_amount"] = parsed_amounts[0]
            amounts_str = ", ".join([f"INR {a:,}" for a in parsed_amounts])
            coll["details"] = f"Collection amounts: {amounts_str}"
            coll["summary"] = "Collections discussed"
            coll["evidence"] = [str(a) for a in parsed_amounts]
            pmethod = "GPay" if any(w in text_lower for w in ["gpay", "upi", "online"]) else ("Cheque" if any(w in text_lower for w in ["cheque", "செக்"]) else "Cash")
            coll["payment_method"] = pmethod
        else:
            amounts = re.findall(r'(?:rs|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)', text_lower)
            if amounts:
                coll = result["topics"]["collection"]
                coll["rating"] = 3
                coll["details"] = f"Mentioned amounts: {', '.join(amounts)}"
                coll["summary"] = "Collections discussed"
        
        # Sales: Tamil order keywords
        order_kw = ["ஆர்டர்", "மூட்டை", "bags", "boxes", "order", "கார்டன்"]
        lines = cleaned_transcript.split("\n")
        sales_found = []
        for line in lines:
            if any(k in line.lower() for k in order_kw):
                nums = re.findall(r'\b(\d{1,4})\b', line)
                prod = "Product"
                for pw in ["சுவர் புட்டி", "putty", "cement", "சிமெண்ட்", "primer", "emulsion", "paintex", "floor coat"]:
                    if pw in line.lower():
                        prod = pw.replace("சுவர் புட்டி", "Wall Putty").replace("சிமெண்ட்", "Cement").title()
                        break
                if nums:
                    sales_found.append(f"{nums[0]}x {prod}")
        if sales_found:
            result["topics"]["sales"]["rating"] = 3
            result["topics"]["sales"]["details"] = ", ".join(list(dict.fromkeys(sales_found)))
            result["topics"]["sales"]["summary"] = "Sales orders discussed"
            
        # Products
        products = ['paintex', 'floor coat', 'karayan', 'putty', 'cement', 'primer', 'emulsion', 'plaster', 'adhesive',
                     'சுவர் புட்டி', 'சிமெண்ட்', 'பெயிண்டெக்ஸ்']
        found_products = [p.title() for p in products if p in text_lower]
        if found_products:
            result["topics"]["product"]["rating"] = 3
            result["topics"]["product"]["details"] = f"Products: {', '.join(found_products)}"
            result["topics"]["product"]["summary"] = "Products discussed"
            result["topics"]["product"]["products"] = found_products
            
        # Competitors
        competitors = ['asian', 'berger', 'dulux', 'birla', 'nerolac']
        found_comps = [c for c in competitors if c in text_lower]
        if found_comps:
            result["topics"]["competition"]["rating"] = 3
            result["topics"]["competition"]["details"] = f"Competitors mentioned: {', '.join(found_comps)}"
            result["topics"]["competition"]["summary"] = "Competition discussed"
            result["topics"]["competition"]["competitors"] = [{"name": c, "product": "", "price": None} for c in found_comps]
            
        # Services
        services = ['transport', 'delivery', 'டிரான்ஸ்போர்ட்', 'டெலிவரி']
        found_servs = [s for s in services if s in text_lower]
        if found_servs:
            result["topics"]["our_services"]["rating"] = 3
            result["topics"]["our_services"]["details"] = f"Services: {', '.join(found_servs)}"
            result["topics"]["our_services"]["summary"] = "Services discussed"
            result["topics"]["our_services"]["services"] = found_servs
            
        # Pending stock
        stock_kw = ['stock', 'godown', 'pending stock', 'ஸ்டாக்', 'கோடவுன்', 'இருப்பு']
        if any(k in text_lower for k in stock_kw):
            result["topics"]["pending_stock"]["rating"] = 3
            result["topics"]["pending_stock"]["details"] = "Stock mentioned"
            result["topics"]["pending_stock"]["summary"] = "Stock discussed"
            
        # Follow-up
        follow_up_keywords = ['next week', 'tomorrow', 'monday', 'wednesday', 'tuesday', 'thursday', 'friday', 'saturday', 'sunday',
                              'அடுத்த வாரம்', 'நாளை', 'புதன்கிழமை', 'செவ்வாய்']
        found_follow_ups = [f for f in follow_up_keywords if f in text_lower]
        if found_follow_ups:
            result["topics"]["follow_up_date"]["rating"] = 3
            result["topics"]["follow_up_date"]["details"] = f"Follow up: {found_follow_ups[0]}"
            result["topics"]["follow_up_date"]["summary"] = "Follow up discussed"
            result["topics"]["follow_up_date"]["date"] = found_follow_ups[0]
            
        return result

    def validate_extraction(self, extraction: dict, cleaned_transcript: str) -> dict:
        text_lower = cleaned_transcript.lower()
        validated = json.loads(json.dumps(extraction))
        
        if "collection" in validated.get("topics", {}):
            coll = validated["topics"]["collection"]
            for field in ["total_amount", "pending_amount", "overdue_amount"]:
                val = coll.get(field)
                if val is not None and isinstance(val, (int, float)):
                    if str(val) not in text_lower:
                         coll[field] = None
                         
        if "product" in validated.get("topics", {}):
            prod = validated["topics"]["product"]
            valid_prods = []
            for p in prod.get("products", []):
                if p.lower() in text_lower:
                    valid_prods.append(p)
            prod["products"] = valid_prods
            if not valid_prods and prod.get("rating", 0) > 0:
                prod["rating"] = 0
                prod["details"] = "Not Mentioned"
                
        if "competition" in validated.get("topics", {}):
            comp = validated["topics"]["competition"]
            valid_comps = []
            for c in comp.get("competitors", []):
                name = c.get("name", "")
                if name.lower() in text_lower:
                    valid_comps.append(c)
            comp["competitors"] = valid_comps
            if not valid_comps and comp.get("rating", 0) > 0:
                comp["rating"] = 0
                comp["details"] = "Not Mentioned"
                
        logger.info("[VALIDATION_RESULT] Validation completed.")
        
        text_hash = hashlib.sha256(cleaned_transcript.encode('utf-8')).hexdigest()
        validated["text_hash"] = text_hash
        
        return validated

    def build_report_data(self, validated: dict, representative: str, client_name: str, date_str: str = "") -> tuple:
        topics = validated.get("topics", {})
        
        def get_details(topic_name):
            d = topics.get(topic_name, {}).get("details", "")
            if not d or d.lower() in ["null", "none"]:
                return "Not Mentioned"
            return d
            
        report_fields = {
            "summary": validated.get("summary", ""),
            "sentiment": validated.get("overall_emotion", "Neutral"),
            "priority": validated.get("priority", "Medium"),
            "follow_up_date": topics.get("follow_up_date", {}).get("date"),
            "sales_raw": get_details("sales"),
            "collection_raw": get_details("collection"),
            "competition_raw": get_details("competition"),
            "product_raw": get_details("product"),
            "price_list_raw": get_details("price_list"),
            "our_services_raw": get_details("our_services"),
            "our_new_products_raw": get_details("our_new_products"),
            "most_sell_products_raw": get_details("most_sell_products"),
            "pending_stock_raw": get_details("pending_stock"),
            "overall_rating": validated.get("overall_rating", 3),
            "overall_emotion": validated.get("overall_emotion", "Neutral"),
            "important_points": json.dumps(validated.get("important_points", [])),
            "text_hash": validated.get("text_hash", "")
        }
        
        explanations = {k: v.get("summary", "Not Mentioned") for k, v in topics.items()}
        
        perf_score_fields = {
            "sales_score": topics.get("sales", {}).get("rating", 0),
            "collection_score": topics.get("collection", {}).get("rating", 0),
            "competition_score": topics.get("competition", {}).get("rating", 0),
            "product_score": topics.get("product", {}).get("rating", 0),
            "price_list_score": topics.get("price_list", {}).get("rating", 0),
            "services_score": topics.get("our_services", {}).get("rating", 0),
            "new_products_score": topics.get("our_new_products", {}).get("rating", 0),
            "most_sell_products_score": topics.get("most_sell_products", {}).get("rating", 0),
            "pending_stock_score": topics.get("pending_stock", {}).get("rating", 0),
            "follow_up_score": topics.get("follow_up_date", {}).get("rating", 0),
            
            "sales_emotion": topics.get("sales", {}).get("emotion", "Neutral"),
            "collection_emotion": topics.get("collection", {}).get("emotion", "Neutral"),
            "competition_emotion": topics.get("competition", {}).get("emotion", "Neutral"),
            "product_emotion": topics.get("product", {}).get("emotion", "Neutral"),
            "price_list_emotion": topics.get("price_list", {}).get("emotion", "Neutral"),
            "services_emotion": topics.get("our_services", {}).get("emotion", "Neutral"),
            "new_products_emotion": topics.get("our_new_products", {}).get("emotion", "Neutral"),
            "most_sell_products_emotion": topics.get("most_sell_products", {}).get("emotion", "Neutral"),
            "pending_stock_emotion": topics.get("pending_stock", {}).get("emotion", "Neutral"),
            "follow_up_emotion": topics.get("follow_up_date", {}).get("emotion", "Neutral"),
            
            "explanations": json.dumps(explanations),
            "topic_details": json.dumps(topics)
        }
        
        return report_fields, perf_score_fields
