import os
import json
import time
import datetime
import random
import hashlib
import re
from sqlalchemy.orm import Session
from backend.models import Report, VoiceFile, Conversation, Sales, Collection, Complaint, ProductRequest, Competitor, PerformanceScore
from backend.services.speech import SpeechService
from backend.services.translation import TranslationService
from backend.services.analysis import AnalysisService
from backend.services.tamil_pipeline import TamilPipeline

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
        self.tamil_pipeline = TamilPipeline()

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
                "rep": "Sankarapandian",
                "client": "Classic Agencies",
                "dialogue": [
                    {"speaker": "Sales Rep", "text": "Hi Classic Agencies, this is Sankarapandian. Do you need a shipment of Wall Putty?", "timestamp": 1.5},
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

    def save_manual_upload(self, upload_file, representative: str, client_name: str, date_str: str, time_str: str) -> dict:
        """
        Saves a manually uploaded voice recording file up to 1 GB in 64KB chunks.
        Creates a VoiceFile record with status="Uploaded".
        """
        filename = upload_file.filename
        content_type = getattr(upload_file, "content_type", "unknown")
        
        ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".webm"}
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed formats: WAV, MP3, M4A, AAC, OGG, WEBM.")

        os.makedirs(UPLOADS_VOICE_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"manual_{timestamp}_{filename.replace(' ', '_')}"
        file_path = os.path.abspath(os.path.join(UPLOADS_VOICE_DIR, safe_filename))

        MAX_BYTES = 1024 * 1024 * 1024  # 1 GB
        total_written = 0
        sha256_hash = hashlib.sha256()

        with open(file_path, "wb") as f_out:
            while True:
                chunk = upload_file.file.read(64 * 1024)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > MAX_BYTES:
                    f_out.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise ValueError("File size exceeds the maximum allowed limit of 1 GB.")
                f_out.write(chunk)
                sha256_hash.update(chunk)

        file_hash = sha256_hash.hexdigest()

        from backend.utils import logger
        logger.info(f"[AUDIO] File received\nFilename: {filename}\nMIME Type: {content_type}\nFile Size: {total_written} bytes\nSales Representative: {representative}\nClient: {client_name}\nDate: {date_str}\nTime: {time_str}")
        logger.info(f"[AUDIO] File saved successfully: {file_path}")
        logger.info(f"[AUDIO] Format validated")

        existing = self.db.query(VoiceFile).filter(VoiceFile.sha256_hash == file_hash).first()
        if existing:
            # If existing record has no transcript, run ElevenLabs STT now
            existing_transcript = (existing.tamil_transcript or "").strip()
            if not existing_transcript:
                from backend.utils import logger as _logger
                _logger.info(f"[ELEVENLABS STT] Duplicate file found but no transcript. Re-running STT on: {existing.file_path}")
                stt_path = existing.file_path if os.path.exists(existing.file_path or "") else file_path
                stt_res = self.speech_service.transcribe_elevenlabs(stt_path, language_code="tam")
                existing_transcript = stt_res.get("transcript", "").strip()
                if existing_transcript:
                    existing.tamil_transcript = existing_transcript
                    self.db.commit()

            return {
                "id": existing.id,
                "filename": existing.original_filename,
                "file_path": existing.file_path,
                "file_size": total_written,
                "representative": representative,
                "client_name": client_name,
                "date": date_str,
                "time": time_str,
                "status": existing.status,
                "tamil_summary": existing_transcript,
                "transcript": existing_transcript,
                "message": "File already uploaded in local database."
            }

        voice_file = VoiceFile(
            original_filename=filename,
            file_path=file_path,
            processed_path=file_path,
            status="Uploaded",
            sha256_hash=file_hash
        )
        self.db.add(voice_file)
        self.db.commit()
        # Transcribe audio using ElevenLabs Scribe STT
        stt_res = self.speech_service.transcribe_elevenlabs(file_path, language_code="tam")
        full_tamil_transcript = stt_res.get("transcript", "").strip()

        if not full_tamil_transcript:
            from backend.utils import logger as _log
            _log.warning("[STT_RAW] ElevenLabs returned empty transcript for file: " + filename)

        voice_file.tamil_transcript = full_tamil_transcript
        self.db.commit()

        return {
            "id": voice_file.id,
            "filename": filename,
            "file_path": file_path,
            "file_size": total_written,
            "representative": representative,
            "client_name": client_name,
            "date": date_str,
            "time": time_str,
            "status": "Uploaded",
            "tamil_summary": full_tamil_transcript,
            "transcript": full_tamil_transcript,
            "model_used": stt_res.get("model_used", "ElevenLabs Scribe v2"),
            "message": "Voice recording uploaded and transcribed successfully."
        }

    def analyze_manual_voice_file(self, voice_file_id: int, representative: str, client_name: str, date_str: str) -> dict:
        """
        Runs Tamil pipeline analysis on a manually uploaded voice file.
        Reuses the ElevenLabs transcript stored in VoiceFile.tamil_transcript.
        """
        from backend.utils import logger
        voice_file = self.db.query(VoiceFile).filter(VoiceFile.id == voice_file_id).first()
        if not voice_file:
            raise ValueError(f"Voice file with ID {voice_file_id} not found.")

        voice_file.status = "Analyzing..."
        self.db.commit()

        start_time = time.time()

        try:
            # Reuse the ElevenLabs transcript already stored
            tamil_transcript = (voice_file.tamil_transcript or "").strip()
            if not tamil_transcript:
                # If no transcript stored, try ElevenLabs again
                voice_file.status = "Transcribing Tamil Speech..."
                self.db.commit()
                file_path = voice_file.file_path
                if file_path and os.path.exists(file_path):
                    stt_res = self.speech_service.transcribe_elevenlabs(file_path, language_code="tam")
                    tamil_transcript = stt_res.get("transcript", "").strip()
                    if tamil_transcript:
                        voice_file.tamil_transcript = tamil_transcript
                        self.db.commit()

            if not tamil_transcript:
                voice_file.status = "Failed"
                self.db.commit()
                raise ValueError("No Tamil transcript available. Please upload the audio again.")

            logger.info(f"[MANUAL AI] Analyzing voice file ID {voice_file_id} with TamilPipeline ({len(tamil_transcript)} chars)")

            # Use TamilPipeline: clean → extract → validate → build
            cleaned = self.tamil_pipeline.clean_transcript(tamil_transcript)
            extraction = self.tamil_pipeline.extract_topics(cleaned, representative, client_name)
            validated = self.tamil_pipeline.validate_extraction(extraction, cleaned)
            report_data, perf_data = self.tamil_pipeline.build_report_data(validated, representative, client_name, date_str)

            # Save Report
            report = Report(
                representative=representative,
                client_name=client_name,
                date=date_str or datetime.date.today().strftime("%Y-%m-%d"),
                summary=report_data.get("summary", "Sales interaction recorded."),
                sentiment=report_data.get("sentiment", "Neutral"),
                priority=report_data.get("priority", "Medium"),
                voice_duration=float(report_data.get("voice_duration", 60.0)),
                file_path=voice_file.file_path,
                follow_up_date=report_data.get("follow_up_date"),
                sales_raw=report_data.get("sales_raw", "Not Mentioned"),
                collection_raw=report_data.get("collection_raw", "Not Mentioned"),
                competition_raw=report_data.get("competition_raw", "Not Mentioned"),
                product_raw=report_data.get("product_raw", "Not Mentioned"),
                price_list_raw=report_data.get("price_list_raw", "Not Mentioned"),
                our_services_raw=report_data.get("our_services_raw", "Not Mentioned"),
                our_new_products_raw=report_data.get("our_new_products_raw", "Not Mentioned"),
                most_sell_products_raw=report_data.get("most_sell_products_raw", "Not Mentioned"),
                pending_stock_raw=report_data.get("pending_stock_raw", "Not Mentioned"),
                model_used=self.tamil_pipeline.ollama_model,
                whisper_model_used="ElevenLabs Scribe v2",
                translation_model_used="Direct Tamil Extraction",
                tamil_transcript=tamil_transcript,
                english_transcript=report_data.get("summary", ""),
                overall_rating=report_data.get("overall_rating", 3),
                overall_emotion=report_data.get("overall_emotion", "Neutral"),
                important_points=report_data.get("important_points", "[]"),
                text_hash=report_data.get("text_hash")
            )
            self.db.add(report)
            self.db.flush()

            # Save PerformanceScore
            perf_score = PerformanceScore(report_id=report.id, **perf_data)
            self.db.add(perf_score)

            voice_file.report_id = report.id
            voice_file.status = "Completed"
            self.db.commit()

            logger.info(f"[DASHBOARD_DATA] Voice file {voice_file_id} → Report ID {report.id} saved.")

            duration_sec = time.time() - start_time
            self.log_sync_operation(downloaded=0, analyzed=1, duration_sec=duration_sec, status="Tamil Pipeline Voice Success")

            topics_data = validated.get("topics", {})
            return {
                "status": "completed",
                "voice_file_id": voice_file.id,
                "report_id": report.id,
                "representative": representative,
                "client_name": client_name,
                "date": report.date,
                "duration": report.voice_duration,
                "summary": report.summary,
                "sentiment": report.sentiment,
                "priority": report.priority,
                "tamil_transcript": tamil_transcript,
                "english_transcript": report_data.get("summary", ""),
                "overall_rating": report.overall_rating,
                "overall_emotion": report.overall_emotion,
                "topics": topics_data,
                "message": "Tamil voice recording analyzed successfully."
            }

        except Exception as err:
            self.db.rollback()
            voice_file.status = "Failed"
            self.db.commit()
            from backend.utils import logger
            logger.error(f"Voice file analysis failed: {str(err)}")
            raise err

    def analyze_manual_tamil_text(self, representative: str, client_name: str, tamil_summary: str, date_str: str = "") -> dict:
        start_time = time.time()
        from backend.utils import logger
        logger.info(f"[MANUAL AI] Starting Tamil pipeline analysis for Representative: '{representative}', Client: '{client_name}'")

        if not tamil_summary or not tamil_summary.strip():
            raise ValueError("Please paste the Tamil voice summary before analyzing.")

        try:
            # Step 1: Clean the Tamil transcript
            cleaned_transcript = self.tamil_pipeline.clean_transcript(tamil_summary)

            # Step 2: Extract topics directly from Tamil (NO translation)
            extraction = self.tamil_pipeline.extract_topics(cleaned_transcript, representative, client_name)

            # Step 3: Validate extraction against transcript
            validated = self.tamil_pipeline.validate_extraction(extraction, cleaned_transcript)

            # Step 4: Build dashboard data
            report_data, perf_data = self.tamil_pipeline.build_report_data(validated, representative, client_name, date_str)

            # Step 5: Save Report to DB
            words_count = len(tamil_summary.split())
            estimated_duration = max(15.0, round(words_count / 2.5, 1))

            report = Report(
                representative=representative,
                client_name=client_name,
                date=date_str or datetime.date.today().strftime("%Y-%m-%d"),
                summary=report_data.get("summary", "Sales interaction recorded."),
                sentiment=report_data.get("sentiment", "Neutral"),
                priority=report_data.get("priority", "Medium"),
                voice_duration=estimated_duration,
                file_path=None,
                follow_up_date=report_data.get("follow_up_date"),
                sales_raw=report_data.get("sales_raw", "Not Mentioned"),
                collection_raw=report_data.get("collection_raw", "Not Mentioned"),
                competition_raw=report_data.get("competition_raw", "Not Mentioned"),
                product_raw=report_data.get("product_raw", "Not Mentioned"),
                price_list_raw=report_data.get("price_list_raw", "Not Mentioned"),
                our_services_raw=report_data.get("our_services_raw", "Not Mentioned"),
                our_new_products_raw=report_data.get("our_new_products_raw", "Not Mentioned"),
                most_sell_products_raw=report_data.get("most_sell_products_raw", "Not Mentioned"),
                pending_stock_raw=report_data.get("pending_stock_raw", "Not Mentioned"),
                model_used=self.tamil_pipeline.ollama_model,
                whisper_model_used="Manual Text Input",
                translation_model_used="Direct Tamil Extraction",
                tamil_transcript=tamil_summary,
                english_transcript=report_data.get("summary", ""),
                overall_rating=report_data.get("overall_rating", 3),
                overall_emotion=report_data.get("overall_emotion", "Neutral"),
                important_points=report_data.get("important_points", "[]"),
                text_hash=report_data.get("text_hash")
            )
            self.db.add(report)
            self.db.flush()

            # Step 6: Save PerformanceScore to DB
            topics_data = validated.get("topics", {})

            existing_perf = self.db.query(PerformanceScore).filter(PerformanceScore.report_id == report.id).first()
            if existing_perf:
                for key, val in perf_data.items():
                    setattr(existing_perf, key, val)
            else:
                perf_score = PerformanceScore(report_id=report.id, **perf_data)
                self.db.add(perf_score)

            self.db.commit()

            logger.info(f"[DASHBOARD_DATA] Report ID {report.id} saved. Sales: {report.sales_raw[:60] if report.sales_raw else 'N/A'}, Collection: {report.collection_raw[:60] if report.collection_raw else 'N/A'}")

            duration_sec = time.time() - start_time
            self.log_sync_operation(downloaded=0, analyzed=1, duration_sec=duration_sec, status="Tamil Pipeline Success")

            return {
                "success": True,
                "status": "completed",
                "analysis_id": report.id,
                "report_id": report.id,
                "representative": representative,
                "client_name": client_name,
                "date": report.date,
                "summary": report.summary,
                "sentiment": report.sentiment,
                "priority": report.priority,
                "tamil_transcript": tamil_summary,
                "english_transcript": report_data.get("summary", ""),
                "overall_rating": report.overall_rating,
                "overall_emotion": report.overall_emotion,
                "topics": topics_data,
                "message": "Tamil voice summary analyzed successfully."
            }

        except Exception as err:
            self.db.rollback()
            from backend.utils import logger
            logger.error(f"Tamil pipeline analysis failed: {str(err)}")
            raise err



