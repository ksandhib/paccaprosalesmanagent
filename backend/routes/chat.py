import datetime
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils import get_current_user, logger
from backend.models import ChatHistory, User
from backend.schemas import ChatRequest, ChatResponse
from backend.services.chat_service import ChatService

router = APIRouter(tags=["chat"])
chat_service = ChatService()

@router.get("/chat/history")
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Retrieves the complete chat history for the logged-in user.
    """
    logger.info(f"Fetching assistant chat history for user: {current_user}")
    user_record = db.query(User).filter(User.username == current_user).first()
    if not user_record:
        return []
        
    history = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_record.id
    ).order_by(ChatHistory.timestamp.asc()).all()
    
    return [
        {
            "message": h.message,
            "response": h.response,
            "timestamp": h.timestamp.isoformat()
        } for h in history
    ]

@router.post("/chat", response_model=ChatResponse)
def post_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Accepts assistant queries, processes them, records chat logs,
    and returns a static response (traditional endpoint fallback).
    """
    logger.info(f"User {current_user} sent assistant message: {request.message}")
    
    try:
        user_record = db.query(User).filter(User.username == current_user).first()
        user_id = user_record.id if user_record else None
        
        response_text = chat_service.process_message(db, request.message)
        
        db_chat = ChatHistory(
            user_id=user_id,
            message=request.message,
            response=response_text,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(db_chat)
        db.commit()
        
        return {
            "message": request.message,
            "response": response_text,
            "timestamp": db_chat.timestamp
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Chat assistance failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat assistant failed: {str(e)}"
        )

@router.post("/chat/stream")
def post_chat_message_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Accepts queries, saves history to DB, and streams responses chunk-by-chunk.
    """
    logger.info(f"User {current_user} requested streaming chat response: {request.message}")
    
    try:
        user_record = db.query(User).filter(User.username == current_user).first()
        user_id = user_record.id if user_record else None
        
        response_text = chat_service.process_message(db, request.message)
        
        # Save to database first
        db_chat = ChatHistory(
            user_id=user_id,
            message=request.message,
            response=response_text,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(db_chat)
        db.commit()
        
        # Stream response word by word
        def stream_generator():
            words = response_text.split(" ")
            for idx, word in enumerate(words):
                yield (word + " " if idx < len(words) - 1 else word)
                time.sleep(0.04) # 40ms delay per word to simulate real-time AI streaming
                
        return StreamingResponse(stream_generator(), media_type="text/plain")
        
    except Exception as e:
        logger.error(f"Streaming chat failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Streaming chat failed: {str(e)}"
        )
