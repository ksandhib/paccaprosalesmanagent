import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load configuration
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "config.json"))

# Default values
DB_REL_PATH = "database/database.db"

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            DB_REL_PATH = config.get("database_path", DB_REL_PATH)
    except Exception:
        pass

# Ensure database directory exists
DB_ABS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", DB_REL_PATH))
DB_DIR = os.path.dirname(DB_ABS_PATH)
os.makedirs(DB_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_ABS_PATH}"

# Connect args needed for SQLite to allow multiple threads
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
