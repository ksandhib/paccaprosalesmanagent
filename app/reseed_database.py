import os
import random
import datetime
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Report, VoiceFile, Conversation, Sales, Collection, Complaint, ProductRequest, Competitor, PerformanceScore

# Database connection
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "database", "database.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

REPS = [
    "Santhana Pandiyan",
    "Periyar Selvam",
    "Bala Murugan",
    "Rajeshwaran",
    "Vinoth Kumar",
    "Parthiban",
    "Sri Ram"
]

CLIENT_NAMES = [
    "Rajesh Enterprises",
    "Pioneer Adhesives",
    "Girish Paints & Hardware",
    "Kumar Traders",
    "Sri Lakshmi Agencies",
    "Modern Paint House",
    "Ganesh Hardware",
    "Classic Agencies",
    "Arun Traders",
    "Green Paints",
    "MSK Hardware",
    "Vinayaga Enterprises",
    "Sri Murugan Paints",
    "New Star Traders",
    "Royal Paints"
]

PRODUCTS = [
    {"name": "Premium Blue Polymer", "price": 250},
    {"name": "Premium Red Polymer", "price": 260},
    {"name": "Eco Adhesive", "price": 320},
    {"name": "Wall Putty", "price": 180},
    {"name": "Interior Emulsion", "price": 450},
    {"name": "Exterior Paint", "price": 550},
    {"name": "Waterproof Coating", "price": 600},
    {"name": "Tile Adhesive", "price": 220},
    {"name": "Crack Filler", "price": 150},
    {"name": "Primer", "price": 280},
    {"name": "Weather Shield", "price": 580},
    {"name": "Acrylic Distemper", "price": 190},
    {"name": "Cement Primer", "price": 240},
    {"name": "Wood Finish", "price": 650},
    {"name": "Texture Paint", "price": 480}
]

COMPETITORS = ["Asian Paints", "Berger", "Nippon Paint", "Acme Corp", "Indigo Paints", "Dr. Fixit"]
PRODUCT_REQUESTS = ["Fast Dry Polymer", "Waterproof Coating", "Premium Primer", "Exterior Emulsion", "Crack Resistant Putty", "Eco Adhesive Variant"]
COMPLAINTS = ["Shortage of 5 cartons", "Damaged bucket received", "Late delivery", "Wrong shade supplied", "Leakage complaint"]

PAYMENT_METHODS = ["GPay", "Cash", "Bank Transfer", "Cheque"]

def reseed():
    import backend.models
    print("Reseed metadata tables:", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Clearing existing transaction tables...")
        # Clear tables except 'users' to keep auth credentials intact
        db.query(Conversation).delete()
        db.query(PerformanceScore).delete()
        db.query(Sales).delete()
        db.query(Collection).delete()
        db.query(Complaint).delete()
        db.query(ProductRequest).delete()
        db.query(Competitor).delete()
        db.query(VoiceFile).delete()
        db.query(Report).delete()
        db.commit()
        print("Existing data cleared successfully.")

        db.commit()
        print("Seeder database cleared successfully. 0 reports loaded.")

    except Exception as e:
        db.rollback()
        print(f"Error during re-seeding: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    reseed()
