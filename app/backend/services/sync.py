import os
import json
import time
import datetime
import random
import hashlib
from sqlalchemy.orm import Session
from backend.models import Report, VoiceFile, Conversation, Sales, Collection, Complaint, ProductRequest, Competitor, PerformanceScore
from backend.services.speech import SpeechService
from backend.services.translation import TranslationService
from backend.services.analysis import AnalysisService

# Setup file paths
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config"))
HISTORY_FILE = os.path.join(CONFIG_DIR, "sync_history.json")
UPLOADS_VOICE_DIR = "uploads/voice"
UPLOADS_PROCESSED_DIR = "uploads/processed"

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(UPLOADS_VOICE_DIR, exist_ok=True)
os.makedirs(UPLOADS_PROCESSED_DIR, exist_ok=True)

class SyncService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.speech_service = SpeechService(models_dir="models")
        self.translation_service = TranslationService()
        self.analysis_service = AnalysisService()

    def get_sync_status(self) -> dict:
        """
        Gathers live status metrics of the synchronization module.
        """
        history = self.get_sync_history()
        last_sync = history[0]["date"] if history else "Never"
        
        # Check if the simulated cloud recordings already exist in db
        rec1_exists = self.db.query(VoiceFile).filter(VoiceFile.original_filename == "cloud_recording_santhana_46.mp3").first() is not None
        rec2_exists = self.db.query(VoiceFile).filter(VoiceFile.original_filename == "cloud_recording_periyar_47.mp3").first() is not None
        
        pending_count = 0
        if not rec1_exists: pending_count += 1
        if not rec2_exists: pending_count += 1
        
        total_downloaded = self.db.query(VoiceFile).count()
        total_analyzed = self.db.query(Report).count()
        
        # Calculate uploads storage size
        storage_mb = 0.0
        for root, dirs, files in os.walk("uploads"):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.exists(fp):
                    storage_mb += os.path.getsize(fp) / (1024 * 1024)
        
        # Today's Sync Operations Count
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        today_sync_count = sum(1 for h in history if h["date"].startswith(today_str))

        return {
            "last_sync_time": last_sync,
            "connection_status": "Connected",
            "server_status": "Online",
            "pending_recordings": pending_count,
            "total_downloaded": total_downloaded,
            "total_analyzed": total_analyzed,
            "today_sync": today_sync_count,
            "storage_used": f"{storage_mb:.2f} MB",
            "ai_status": "Ready"
        }

    def get_sync_history(self) -> list:
        """
        Returns the last 10 synchronization operations history list.
        """
        if not os.path.exists(HISTORY_FILE):
            # Seed default history for visual realism
            default_history = [
                {
                    "date": (datetime.datetime.now() - datetime.timedelta(days=1, hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
                    "downloaded_files": 3,
                    "analyzed_files": 3,
                    "duration": "14.2s",
                    "status": "Success"
                },
                {
                    "date": (datetime.datetime.now() - datetime.timedelta(days=3, hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                    "downloaded_files": 2,
                    "analyzed_files": 2,
                    "duration": "9.8s",
                    "status": "Success"
                }
            ]
            with open(HISTORY_FILE, "w") as f:
                json.dump(default_history, f, indent=4)
            return default_history

        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)[:10]
        except Exception:
            return []

    def log_sync_operation(self, downloaded: int, analyzed: int, duration_sec: float, status: str):
        """
        Appends a new sync run log entry to history.
        """
        history = self.get_sync_history()
        new_entry = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "downloaded_files": downloaded,
            "analyzed_files": analyzed,
            "duration": f"{duration_sec:.1f}s",
            "status": status
        }
        history.insert(0, new_entry)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[:10], f, indent=4)

    def execute_sync(self) -> dict:
        """
        Simulates connection check and processes the two designated cloud recording sync runs.
        """
        start_time = time.time()
        
        # Check pending
        rec1_exists = self.db.query(VoiceFile).filter(VoiceFile.original_filename == "cloud_recording_santhana_46.mp3").first() is not None
        rec2_exists = self.db.query(VoiceFile).filter(VoiceFile.original_filename == "cloud_recording_periyar_47.mp3").first() is not None
        
        pending_files = []
        if not rec1_exists:
            pending_files.append({
                "filename": "cloud_recording_santhana_46.mp3",
                "rep": "Santhana Pandiyan",
                "client": "Classic Agencies",
                "dialogue": [
                    {"speaker": "Sales Rep", "text": "Hi Classic Agencies, this is Santhana Pandiyan. Do you need a shipment of Wall Putty?", "timestamp": 1.5},
                    {"speaker": "Client", "text": "Yes, please book 40 cartons of Wall Putty. But we need a price quotation first.", "timestamp": 7.2},
                    {"speaker": "Sales Rep", "text": "Sure, I will register the sales order now. Can we clear the ₹18,000 pending payment next week?", "timestamp": 15.0},
                    {"speaker": "Client", "text": "Yes, we will settle that. Thank you.", "timestamp": 22.8}
                ]
            })
        
        if not rec2_exists:
            pending_files.append({
                "filename": "cloud_recording_periyar_47.mp3",
                "rep": "Periyar Selvam",
                "client": "Arun Traders",
                "dialogue": [
                    {"speaker": "Sales Rep", "text": "Good morning, Periyar Selvam here. I am following up on outstanding payments.", "timestamp": 2.0},
                    {"speaker": "Client", "text": "Hello, I just transferred ₹35,000 via GPay. Reference is GPAY44981. But we have a complaint.", "timestamp": 8.5},
                    {"speaker": "Sales Rep", "text": "Oh, what is the complaint?", "timestamp": 15.3},
                    {"speaker": "Client", "text": "We received a damaged bucket, and the wrong shade was supplied.", "timestamp": 20.0},
                    {"speaker": "Sales Rep", "text": "I apologize. I will log a complaint. Also, do you need more Waterproof Coating next week?", "timestamp": 26.5},
                    {"speaker": "Client", "text": "Yes, register a request for Waterproof Coating.", "timestamp": 33.1}
                ]
            })

        if not pending_files:
            return {
                "status": "synchronized",
                "downloaded": 0,
                "analyzed": 0,
                "message": "No new recordings available. Everything is already synchronized."
            }

        # Processes each file
        for idx, item in enumerate(pending_files):
            # Create a mock physical file inside uploads/voice/ to represent download
            dest_path = os.path.abspath(os.path.join(UPLOADS_VOICE_DIR, item["filename"]))
            with open(dest_path, "w") as f:
                f.write(f"Simulated audio file data for {item['filename']}")

            # Run transcription (simulate with our specific high-fidelity dialog segments)
            duration = float(random.randint(45, 90))
            segments = item["dialogue"]

            # Translate segments (if needed, translate text)
            for seg in segments:
                seg["text"] = self.translation_service.translate(seg["text"])

            # Run Analysis
            analysis = self.analysis_service.analyze_transcript(segments)

            # Insert Database records
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            
            sales_list = [f"{s['quantity']}x {s['item_name']} (INR {s['amount']})" for s in analysis["sales"]]
            sales_raw = ", ".join(sales_list) if sales_list else "None"
            
            coll_list = [f"INR {c['amount_collected']} via {c['payment_method']}" for c in analysis["collections"]]
            collection_raw = ", ".join(coll_list) if coll_list else "None"
            
            comp_list = [c["competitor_name"] for c in analysis["competitors"]]
            competition_raw = ", ".join(comp_list) if comp_list else "None"
            
            prod_list = [p["product_name"] for p in analysis["product_requests"]]
            product_raw = ", ".join(prod_list) if prod_list else "None"
            
            report = Report(
                representative=item["rep"],
                client_name=item["client"],
                date=today_str,
                summary=analysis["summary"],
                sentiment=analysis["sentiment"],
                priority=analysis["priority"],
                voice_duration=duration,
                file_path=dest_path,
                follow_up_date=analysis.get("follow_up_date"),
                sales_raw=sales_raw,
                collection_raw=collection_raw,
                competition_raw=competition_raw,
                product_raw=product_raw,
                price_list_raw="None",
                our_services_raw="None",
                our_new_products_raw="None",
                most_sell_products_raw="None",
                pending_stock_raw="None",
                model_used=self.analysis_service.ollama_model,
                whisper_model_used=self.speech_service.whisper_model,
                translation_model_used=self.translation_service.translation_model
            )
            self.db.add(report)
            self.db.flush()

            # Generate and save Performance Scores
            scores_data = analysis.get("scores", {})
            def get_cat_score(cat):
                c_data = scores_data.get(cat, {})
                if isinstance(c_data, dict):
                    return c_data.get("score", 0)
                return 0
                
            explanations_dict = {}
            for cat in ["sales", "collection", "competition", "product", "price_list", "our_services", "our_new_products", "most_sell_products", "pending_stock", "follow_up_date"]:
                c_data = scores_data.get(cat, {})
                if isinstance(c_data, dict):
                    explanations_dict[cat] = c_data.get("explanation", "")
                else:
                    explanations_dict[cat] = ""
                    
            perf_score = PerformanceScore(
                report_id=report.id,
                sales_score=get_cat_score("sales"),
                collection_score=get_cat_score("collection"),
                competition_score=get_cat_score("competition"),
                product_score=get_cat_score("product"),
                price_list_score=get_cat_score("price_list"),
                services_score=get_cat_score("our_services"),
                new_products_score=get_cat_score("our_new_products"),
                most_sell_products_score=get_cat_score("most_sell_products"),
                pending_stock_score=get_cat_score("pending_stock"),
                follow_up_score=get_cat_score("follow_up_date"),
                explanations=json.dumps(explanations_dict)
            )
            self.db.add(perf_score)

            # Move file to processed
            processed_path = os.path.abspath(os.path.join(UPLOADS_PROCESSED_DIR, item["filename"]))
            if os.path.exists(dest_path):
                try:
                    import shutil
                    shutil.move(dest_path, processed_path)
                    report.file_path = processed_path
                except Exception:
                    processed_path = dest_path

            fake_hash = hashlib.sha256(item["filename"].encode()).hexdigest()
            db_voice = VoiceFile(
                report_id=report.id,
                original_filename=item["filename"],
                file_path=processed_path,
                processed_path=processed_path,
                status="Completed",
                sha256_hash=fake_hash
            )
            self.db.add(db_voice)

            # Save Child Models
            for c in segments:
                self.db.add(Conversation(
                    report_id=report.id,
                    speaker=c["speaker"],
                    text=c["text"],
                    timestamp=float(c["timestamp"])
                ))
            
            for s in analysis["sales"]:
                self.db.add(Sales(
                    report_id=report.id,
                    item_name=s["item_name"],
                    quantity=s["quantity"],
                    amount=float(s["amount"]),
                    payment_status=s["payment_status"]
                ))
            
            for col in analysis["collections"]:
                self.db.add(Collection(
                    report_id=report.id,
                    amount_collected=float(col["amount_collected"]),
                    payment_method=col["payment_method"],
                    reference_no=col["reference_no"]
                ))

            for comp in analysis["complaints"]:
                self.db.add(Complaint(
                    report_id=report.id,
                    description=comp["description"],
                    severity=comp["severity"],
                    status=comp["status"]
                ))

            for pr in analysis["product_requests"]:
                self.db.add(ProductRequest(
                    report_id=report.id,
                    product_name=pr["product_name"],
                    details=pr["details"]
                ))

            for cmp_act in analysis["competitors"]:
                self.db.add(Competitor(
                    report_id=report.id,
                    competitor_name=cmp_act["competitor_name"],
                    activity_details=cmp_act["activity_details"]
                ))

        self.db.commit()

        duration_sec = time.time() - start_time
        downloaded = len(pending_files)
        analyzed = len(pending_files)
        
        self.log_sync_operation(downloaded, analyzed, duration_sec, "Success")

        return {
            "status": "success",
            "downloaded": downloaded,
            "analyzed": analyzed,
            "message": "Synchronization Completed Successfully"
        }
