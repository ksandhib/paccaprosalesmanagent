import os
import json
import io
import time
import threading
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Form
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils import get_current_user, logger
from backend.models import PosterAnalysis
from backend.schemas import PosterAnalysisEditSchema
from backend.services.poster_analysis_service import PosterAnalysisService

# Define reportlab imports dynamically to ensure safety
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except ImportError:
    pass

router = APIRouter(tags=["poster-analysis"])

POSTERS_DIR = "uploads/posters"
os.makedirs(POSTERS_DIR, exist_ok=True)

@router.get("/api/ollama/status")
def get_ollama_status(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Check if Ollama local service is running and if the vision model is installed.
    """
    service = PosterAnalysisService(db)
    return service.check_ollama_status()

@router.post("/poster/upload")
def upload_poster_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Validate size and format of uploaded marketing poster image, save it temporarily
    and return file metadata including size, path, and SHA-256 hash.
    """
    logger.info(f"User {current_user} uploading poster image: {file.filename}")
    
    # Validation: Format Check
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format. Only PNG, JPG, JPEG, WEBP images allowed."
        )

    # Read bytes to validate size and compute hash
    content = file.file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > 50:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large. Maximum size is 50MB."
        )
    
    # Compute SHA-256 hash
    service = PosterAnalysisService(db)
    image_hash = service.compute_sha256(content)
    
    # Prevent duplicate uploads blocking by returning check flags
    existing = service.get_by_hash(image_hash)
    
    # Save file
    filename = f"{image_hash[:12]}{ext}"
    dest_path = os.path.join(POSTERS_DIR, filename)
    with open(dest_path, "wb") as f:
        f.write(content)
        
    return {
        "status": "success",
        "duplicate": existing is not None,
        "existing_id": existing.id if existing else None,
        "filename": filename,
        "size_bytes": len(content),
        "file_size": f"{file_size_mb:.2f} MB",
        "image_hash": image_hash,
        "image_url": f"/uploads/posters/{filename}"
    }

@router.post("/poster/analyze")
def analyze_poster(
    filename: str = Form(...),
    image_hash: str = Form(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Runs OCR extraction and AI structured analysis, streaming status updates back to the client.
    """
    logger.info(f"User {current_user} requested analysis for poster: {filename}")
    
    def event_generator():
        try:
            service = PosterAnalysisService(db)

            yield json.dumps({"step": 1, "message": "Uploading poster..."}) + "\n"
            existing = service.get_by_hash(image_hash)
            is_duplicate = existing is not None

            image_path = os.path.join(POSTERS_DIR, filename)
            if not os.path.exists(image_path):
                yield json.dumps({"step": -1, "message": "Uploaded image file not found on server."}) + "\n"
                return

            yield json.dumps({"step": 2, "message": "Extracting text..."}) + "\n"
            time.sleep(0.5)
            yield json.dumps({"step": 3, "message": "OCR completed"}) + "\n"
            yield json.dumps({"step": 4, "message": "Analyzing extracted text with AI..."}) + "\n"

            # ── Run analysis in a background thread ──
            ANALYSIS_TIMEOUT = 120  # seconds
            result_holder = {"analysis": None, "error": None, "done": False}

            def run_in_thread():
                try:
                    result_holder["analysis"] = service.run_analysis(
                        image_path=image_path,
                        filename=filename,
                        image_hash=image_hash,
                        uploaded_by=current_user
                    )
                except Exception as ex:
                    result_holder["error"] = str(ex)
                finally:
                    result_holder["done"] = True

            t = threading.Thread(target=run_in_thread, daemon=True)
            t.start()

            # Stream heartbeat messages every 2 seconds until done or timeout
            elapsed = 0
            heartbeat_interval = 2
            while not result_holder["done"] and elapsed < ANALYSIS_TIMEOUT:
                time.sleep(heartbeat_interval)
                elapsed += heartbeat_interval

            if not result_holder["done"]:
                yield json.dumps({"step": -1, "message": f"Analysis timed out after {ANALYSIS_TIMEOUT} seconds."}) + "\n"
                return

            if result_holder["error"]:
                yield json.dumps({"step": -1, "message": f"Analysis failed: {result_holder['error']}"}) + "\n"
                return

            analysis = result_holder["analysis"]

            if analysis.image_hash != image_hash:
                yield json.dumps({"step": -1, "message": "Analysis result does not match uploaded image."}) + "\n"
                return

            yield json.dumps({
                "step": 5,
                "message": "Analysis completed",
                "success": True,
                "duplicate": is_duplicate,
                "reanalyzed": is_duplicate,
                "id": analysis.id
            }) + "\n"

        except Exception as e:
            logger.error("Error during poster stream analysis: {}".format(str(e)))
            yield json.dumps({"step": -1, "message": "Analysis failed: {}".format(str(e))}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/poster/history")
def get_poster_history(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Returns complete chronological history of all marketing poster analyses.
    """
    logger.info(f"User {current_user} fetching poster analysis history")
    history = db.query(PosterAnalysis).order_by(PosterAnalysis.id.desc()).all()
    
    results = []
    for item in history:
        # Safely parse JSON strings
        try:
            hl = json.loads(item.highlights) if item.highlights else []
        except:
            hl = []
        try:
            info = json.loads(item.important_information) if item.important_information else {}
        except:
            info = {}
            
        results.append({
            "id": item.id,
            "poster_title": item.poster_title,
            "poster_category": item.poster_category,
            "main_heading": item.main_heading,
            "sub_heading": item.sub_heading,
            "filename": item.filename,
            "image_url": item.image_url,
            "image_hash": item.image_hash,
            "ocr_text": item.ocr_text,
            "summary": item.summary,
            "detailed_summary": item.detailed_summary,
            "highlights": hl,
            "important_information": info,
            "language": item.language,
            "sentiment": item.sentiment,
            "tone": item.tone,
            "target_audience": item.target_audience,
            "call_to_action": item.call_to_action,
            "ocr_confidence": item.ocr_confidence,
            "ai_confidence": item.ai_confidence,
            "uploaded_by": item.uploaded_by,
            "status": item.status or "Analyzed",
            "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "brand": item.brand,
            "product": item.product,
            "price": item.price,
            "offer": item.offer,
            "marketing_score": item.marketing_score,
            "marketing_suggestions": json.loads(item.marketing_suggestions) if item.marketing_suggestions else [],
            "improvement_suggestions": json.loads(item.improvement_suggestions) if item.improvement_suggestions else [],
            "marketing_analysis": json.loads(item.marketing_analysis) if item.marketing_analysis else {},
            "image_width": item.image_width,
            "image_height": item.image_height,
            "model_name": item.model_name,
            "analysis_result": json.loads(item.analysis_result) if item.analysis_result else {}
        })
    return results

@router.get("/poster/{poster_id}")
def get_poster_details(
    poster_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Fetch a single poster analysis details by ID.
    """
    logger.info(f"User {current_user} viewing details of poster: {poster_id}")
    item = db.query(PosterAnalysis).filter(PosterAnalysis.id == poster_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poster record not found"
        )
        
    try:
        hl = json.loads(item.highlights) if item.highlights else []
    except:
        hl = []
    try:
        info = json.loads(item.important_information) if item.important_information else {}
    except:
        info = {}
    try:
        kw = json.loads(item.keywords) if item.keywords else []
    except:
        kw = []

    return {
        "id": item.id,
        "poster_title": item.poster_title,
        "poster_category": item.poster_category,
        "main_heading": item.main_heading,
        "sub_heading": item.sub_heading,
        "filename": item.filename,
        "image_url": item.image_url,
        "image_hash": item.image_hash,
        "ocr_text": item.ocr_text,
        "summary": item.summary,
        "detailed_summary": item.detailed_summary,
        "highlights": hl,
        "important_information": info,
        "keywords": kw,
        "language": item.language,
        "sentiment": item.sentiment,
        "tone": item.tone,
        "target_audience": item.target_audience,
        "call_to_action": item.call_to_action,
        "ocr_confidence": item.ocr_confidence,
        "ai_confidence": item.ai_confidence,
        "uploaded_by": item.uploaded_by,
        "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "brand": item.brand,
        "product": item.product,
        "price": item.price,
        "offer": item.offer,
        "marketing_score": item.marketing_score,
        "marketing_suggestions": json.loads(item.marketing_suggestions) if item.marketing_suggestions else [],
        "improvement_suggestions": json.loads(item.improvement_suggestions) if item.improvement_suggestions else [],
        "marketing_analysis": json.loads(item.marketing_analysis) if item.marketing_analysis else {},
        "image_width": item.image_width,
        "image_height": item.image_height,
        "model_name": item.model_name,
        "analysis_result": json.loads(item.analysis_result) if item.analysis_result else {}
    }

@router.put("/poster/{poster_id}")
def edit_poster_fields(
    poster_id: int,
    payload: PosterAnalysisEditSchema,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Updates the customizable parameters (title, category, headings) of the analysis.
    """
    logger.info(f"User {current_user} updating fields of poster: {poster_id}")
    item = db.query(PosterAnalysis).filter(PosterAnalysis.id == poster_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poster record not found"
        )
        
    if payload.poster_title is not None:
        item.poster_title = payload.poster_title
    if payload.poster_category is not None:
        item.poster_category = payload.poster_category
    if payload.main_heading is not None:
        item.main_heading = payload.main_heading
    if payload.sub_heading is not None:
        item.sub_heading = payload.sub_heading
        
    db.commit()
    return {"status": "success", "message": "Poster metadata updated successfully."}

@router.delete("/poster/{poster_id}")
def delete_poster(
    poster_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Deletes the analysis record from database and wipes the associated file from disk.
    """
    logger.info(f"User {current_user} deleting poster record: {poster_id}")
    item = db.query(PosterAnalysis).filter(PosterAnalysis.id == poster_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poster record not found"
        )
        
    # Delete image file from filesystem
    image_path = os.path.join(POSTERS_DIR, item.filename)
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
            logger.info(f"Deleted image file: {image_path}")
        except Exception as e:
            logger.error(f"Failed to delete image file {image_path}: {str(e)}")
            
    db.delete(item)
    db.commit()
    return {"status": "success", "message": "Poster and analysis record deleted."}

@router.post("/poster/{poster_id}/reanalyze")
def reanalyze_poster(
    poster_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Re-runs the OCR and AI analysis on the existing file.
    """
    logger.info(f"User {current_user} re-analyzing poster: {poster_id}")
    item = db.query(PosterAnalysis).filter(PosterAnalysis.id == poster_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poster record not found"
        )
        
    image_path = os.path.join(POSTERS_DIR, item.filename)
    if not os.path.exists(image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source image file has been deleted from server."
        )
        
    service = PosterAnalysisService(db)
    
    # Run vision analysis on the existing file (this updates the existing record)
    service.run_analysis(
        image_path=image_path,
        filename=item.filename,
        image_hash=item.image_hash,
        uploaded_by=current_user
    )
    
    return {"status": "success", "message": "Poster re-analyzed successfully."}

@router.get("/poster/{poster_id}/export/json")
def export_poster_json(
    poster_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Export the poster analysis as a raw structured JSON file.
    """
    logger.info(f"User {current_user} exporting poster {poster_id} to JSON")
    item = db.query(PosterAnalysis).filter(PosterAnalysis.id == poster_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poster record not found"
        )
        
    try:
        hl = json.loads(item.highlights) if item.highlights else []
    except:
        hl = []
    try:
        info = json.loads(item.important_information) if item.important_information else {}
    except:
        info = {}
    try:
        kw = json.loads(item.keywords) if item.keywords else []
    except:
        kw = []

    data = {
        "id": item.id,
        "poster_title": item.poster_title,
        "poster_category": item.poster_category,
        "main_heading": item.main_heading,
        "sub_heading": item.sub_heading,
        "filename": item.filename,
        "image_url": item.image_url,
        "ocr_text": item.ocr_text,
        "summary": item.summary,
        "detailed_summary": item.detailed_summary,
        "highlights": hl,
        "important_information": info,
        "keywords": kw,
        "language": item.language,
        "sentiment": item.sentiment,
        "tone": item.tone,
        "target_audience": item.target_audience,
        "call_to_action": item.call_to_action,
        "ocr_confidence": item.ocr_confidence,
        "ai_confidence": item.ai_confidence,
        "uploaded_by": item.uploaded_by,
        "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    content = json.dumps(data, indent=4)
    response = StreamingResponse(io.BytesIO(content.encode()), media_type="application/json")
    response.headers["Content-Disposition"] = f"attachment; filename=poster_analysis_{poster_id}.json"
    return response

@router.get("/poster/{poster_id}/export/pdf")
def export_poster_pdf(
    poster_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Generate and download a beautifully styled PDF of the Poster Analysis.
    """
    logger.info(f"User {current_user} exporting poster {poster_id} to PDF")
    item = db.query(PosterAnalysis).filter(PosterAnalysis.id == poster_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poster record not found"
        )

    try:
        info = json.loads(item.important_information) if item.important_information else {}
    except:
        info = {}

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=15
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#475569')
    )

    story = []
    
    # Document Header
    story.append(Paragraph("PaccaPro AI - Poster Analysis Report", title_style))
    story.append(Spacer(1, 10))
    
    # Metadata Table
    meta_data = [
        [Paragraph("Poster Title:", meta_style), Paragraph(item.poster_title or "Untitled", body_style),
         Paragraph("Category:", meta_style), Paragraph(item.poster_category or "Marketing", body_style)],
        [Paragraph("Language:", meta_style), Paragraph(item.language or "English", body_style),
         Paragraph("Uploaded By:", meta_style), Paragraph(item.uploaded_by or "Admin", body_style)],
        [Paragraph("OCR Confidence:", meta_style), Paragraph(f"{item.ocr_confidence * 100:.1f}%", body_style),
         Paragraph("Upload Date:", meta_style), Paragraph(item.created_at.strftime("%Y-%m-%d %H:%M:%S"), body_style)]
    ]
    
    t = Table(meta_data, colWidths=[100, 160, 100, 160])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f1f5f9')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Summaries
    story.append(Paragraph("Executive Summary", section_style))
    story.append(Paragraph(item.summary or "N/A", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Detailed Analysis", section_style))
    story.append(Paragraph(item.detailed_summary or "N/A", body_style))
    story.append(Spacer(1, 10))

    # Important Information
    story.append(Paragraph("Extracted Contacts & Details", section_style))
    contact_text = f"<b>Emails:</b> {', '.join(info.get('emails', [])) or 'None'}<br/>" \
                   f"<b>Phones:</b> {', '.join(info.get('phones', [])) or 'None'}<br/>" \
                   f"<b>Website:</b> {', '.join(info.get('urls', [])) or 'None'}<br/>" \
                   f"<b>Venue:</b> {info.get('venue', 'N/A')}<br/>" \
                   f"<b>Date / Time:</b> {info.get('date', 'N/A')} at {info.get('time', 'N/A')}<br/>" \
                   f"<b>Offer/Discount:</b> {info.get('discount', 'None')} (Promo: {info.get('coupon_code', 'None')})"
    story.append(Paragraph(contact_text, body_style))
    story.append(Spacer(1, 10))
    
    # OCR Text
    story.append(Paragraph("Verbatim OCR Transcription", section_style))
    ocr_p = Paragraph(item.ocr_text.replace("\n", "<br/>") if item.ocr_text else "No OCR text extracted.", body_style)
    story.append(ocr_p)
    
    doc.build(story)
    
    buffer.seek(0)
    response = StreamingResponse(buffer, media_type="application/pdf")
    response.headers["Content-Disposition"] = f"attachment; filename=poster_analysis_{poster_id}.pdf"
    return response
