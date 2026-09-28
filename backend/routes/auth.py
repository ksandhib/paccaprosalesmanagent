from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.schemas import LoginRequest, Token
from backend.utils import verify_password, create_access_token, logger

router = APIRouter(tags=["authentication"])

@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Validates user credentials against the users table.
    Returns access token and details.
    """
    logger.info(f"Login attempt for user: {request.username}")
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        logger.warning(f"Login failed: User {request.username} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
        
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"Login failed: Password mismatch for user {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
        
    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"User {request.username} logged in successfully")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username
    }
