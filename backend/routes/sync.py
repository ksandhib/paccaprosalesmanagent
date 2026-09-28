from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils import get_current_user, logger
from backend.services.sync import SyncService

router = APIRouter(tags=["sync"])

@router.get("/sync/status")
def get_sync_status(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    logger.info(f"User {current_user} requested sync dashboard status.")
    try:
        sync_service = SyncService(db)
        return sync_service.get_sync_status()
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sync/history")
def get_sync_history(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    logger.info(f"User {current_user} requested sync history.")
    try:
        sync_service = SyncService(db)
        return sync_service.get_sync_history()
    except Exception as e:
        logger.error(f"Error getting sync history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/run")
def run_sync(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    logger.info(f"User {current_user} triggered cloud sync execution.")
    try:
        sync_service = SyncService(db)
        return sync_service.execute_sync()
    except Exception as e:
        logger.error(f"Error executing sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/voice/transcribe")
def voice_transcribe(
    file: UploadFile = File(None),
    audio: UploadFile = File(None),
    sales_representative: str = Form(None),
    representative: str = Form("Sankarapandian"),
    client_name: str = Form("General Client"),
    date: str = Form(""),
    time: str = Form(""),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    upload_file = file or audio
    if not upload_file:
        raise HTTPException(status_code=400, detail="Please upload a valid audio file.")

    rep = sales_representative or representative or "Sankarapandian"
    import uuid
    req_id = str(uuid.uuid4())
    logger.info(f"User {current_user} requested ElevenLabs Tamil transcription (req_id={req_id}, file={upload_file.filename})")
    try:
        sync_service = SyncService(db)
        res = sync_service.save_manual_upload(upload_file, rep, client_name, date, time)
        return {
            "success": True,
            "request_id": req_id,
            "analysis_id": str(uuid.uuid4()),
            "voice_file_id": res.get("id"),
            "language": "ta",
            "transcript": res.get("tamil_summary") or res.get("transcript"),
            "speakers": True
        }
    except ValueError as ve:
        logger.warning(f"Validation error on voice transcribe: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error handling voice transcribe: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/manual-upload")
def manual_voice_upload(
    file: UploadFile = File(...),
    representative: str = Form("Sankarapandian"),
    client_name: str = Form("General Client"),
    date: str = Form(""),
    time: str = Form(""),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    logger.info(f"User {current_user} uploaded manual voice recording: {file.filename}")
    try:
        sync_service = SyncService(db)
        return sync_service.save_manual_upload(file, representative, client_name, date, time)
    except ValueError as ve:
        logger.warning(f"Validation error on manual voice upload: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error handling manual voice upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/manual-analyze/{voice_file_id}")
def manual_voice_analyze(
    voice_file_id: int,
    representative: str = Form("Sankarapandian"),
    client_name: str = Form("General Client"),
    date: str = Form(""),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    logger.info(f"User {current_user} triggered local AI analysis for voice file ID {voice_file_id}")
    try:
        sync_service = SyncService(db)
        return sync_service.analyze_manual_voice_file(voice_file_id, representative, client_name, date)
    except ValueError as ve:
        logger.warning(f"Validation error on manual voice analyze: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during manual voice AI analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/analysis/tamil")
@router.post("/api/voice-summary/analyze")
@router.post("/sync/manual-text-analyze")
def analyze_manual_text_summary(
    representative: str = Form(None),
    client_name: str = Form(None),
    tamil_summary: str = Form(None),
    date: str = Form(""),
    request_id: str = Form(""),
    sales_rep_id: str = Form(None),
    client_id: str = Form(None),
    tamil_text: str = Form(None),
    payload: dict = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    rep = representative or sales_rep_id or (payload.get("sales_rep_id") if payload else None) or (payload.get("representative") if payload else None) or "Sankarapandian"
    c_name = client_name or client_id or (payload.get("client_id") if payload else None) or (payload.get("client_name") if payload else None) or "General Client"
    text = tamil_summary or tamil_text or (payload.get("tamil_text") if payload else None) or (payload.get("tamil_summary") if payload else None) or ""

    if not text.strip():
        raise HTTPException(status_code=400, detail="Please paste the Tamil conversation summary.")

    logger.info(f"User {current_user} submitted manual Tamil voice summary text for AI analysis (rep: {rep}, client: {c_name})")
    try:
        sync_service = SyncService(db)
        return sync_service.analyze_manual_tamil_text(rep, c_name, text, date)
    except ValueError as ve:
        logger.warning(f"Validation error on manual text analyze: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during manual text AI analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
