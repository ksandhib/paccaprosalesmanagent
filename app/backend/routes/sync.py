from fastapi import APIRouter, Depends, HTTPException
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
