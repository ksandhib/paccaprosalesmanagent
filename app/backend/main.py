import os
import json
import threading
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import engine, Base, SessionLocal
from backend.utils import get_password_hash, logger
from backend.models import User, Report, Sales, Collection, Complaint, ProductRequest, Competitor, Conversation, VoiceFile, PosterAnalysis, PerformanceScore

# Import routers
from backend.routes.auth import router as auth_router
from backend.routes.sync import router as sync_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.reports import router as reports_router
from backend.routes.chat import router as chat_router
from backend.routes.ai_model import router as ai_model_router
from backend.routes.reports_export import router as reports_export_router
from backend.routes.poster_analysis import router as poster_analysis_router

# List of 16 required portable directories
REQUIRED_DIRECTORIES = [
    "backend", "frontend", "database", "uploads", "uploads/voice", "uploads/processed",
    "backups", "logs", "cache", "temp", "config", "python", "ffmpeg", "ollama", 
    "models", "reports", "exports", "assets"
]

# Ensure directories exist
logger.info("Verifying system portable folders structure...")
for d in REQUIRED_DIRECTORIES:
    os.makedirs(d, exist_ok=True)
logger.info("System folders verified successfully.")

# Load server settings
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "config.json"))
HOST = "127.0.0.1"
PORT = 8000

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
            HOST = cfg.get("host", HOST)
            PORT = cfg.get("port", PORT)
    except:
        pass

# Initialize database tables
logger.info("Initializing SQLite database tables & indexes...")
Base.metadata.create_all(bind=engine)

# Seed default database records
db = SessionLocal()
try:
    # 1. Seed or update default admin user to ensure correct bcrypt scheme compatibility
    from dotenv import load_dotenv
    load_dotenv()
    def_user = os.getenv("DEFAULT_USERNAME", "kumar")
    def_pass = os.getenv("DEFAULT_PASSWORD", "1973")
    
    admin_user = db.query(User).filter(User.username == def_user).first()
    if not admin_user:
        logger.info(f"Seeding default user account '{def_user}'...")
        admin_user = User(
            username=def_user,
            password_hash=get_password_hash(def_pass)
        )
        db.add(admin_user)
        db.commit()
        logger.info("Default user seeded.")
    else:
        logger.info(f"Enforcing correct password hashing algorithm for user: {def_user}")
        admin_user.password_hash = get_password_hash(def_pass)
        db.commit()

    # 2. Seed mock reports if database is empty
    report_count = db.query(Report).count()
    if report_count == 0:
        logger.info("Seeding initial mock reports...")
        try:
            from reseed_database import reseed
            reseed()
            logger.info("New mock records seeded successfully via reseed module.")
        except Exception as seed_err:
            logger.error(f"Error seeding database via reseed module: {str(seed_err)}")

except Exception as err:
    db.rollback()
    logger.error(f"Error seeding database: {str(err)}")
finally:
    db.close()

# Create FastAPI Instance
app = FastAPI(
    title="PaccaPro AI Sales Analysis System (PASAS) API",
    description="Backend API for managing voice sales transcription, report parsing, dashboard metrics, and interactive assistant logs.",
    version="1.0.0"
)

# CORS Middleware Configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(sync_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(chat_router)
app.include_router(ai_model_router)
app.include_router(reports_export_router)
app.include_router(poster_analysis_router)

# Mount static uploads folder for poster images serving
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(FRONTEND_DIR):
    @app.get("/")
    def read_root():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
        
    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
    logger.info("Mounted static frontend folder")
else:
    logger.warning(f"Frontend folder not found at {FRONTEND_DIR}. API only mode enabled.")
