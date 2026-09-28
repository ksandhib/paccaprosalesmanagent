import os
import random
import datetime
import json
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import (
    Report, VoiceFile, Conversation, Sales, Collection,
    Complaint, ProductRequest, Competitor, PerformanceScore
)

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
    "Rajesh Enterprises", "Pioneer Adhesives", "Girish Paints & Hardware",
    "Kumar Traders", "Sri Lakshmi Agencies", "Modern Paint House",
    "Ganesh Hardware", "Classic Agencies", "Arun Traders", "Green Paints",
    "MSK Hardware", "Vinayaga Enterprises", "Sri Murugan Paints",
    "New Star Traders", "Royal Paints"
]

PRODUCTS = [
    {"name": "Premium Base Coat", "price": 450},
    {"name": "Waterproof Coating", "price": 600},
    {"name": "Wall Putty", "price": 180},
    {"name": "Interior Emulsion", "price": 520},
    {"name": "Exterior Weather Shield", "price": 680},
    {"name": "Tile Adhesive", "price": 320},
    {"name": "Cement Primer", "price": 280},
    {"name": "Acrylic Distemper", "price": 210}
]

COMPETITORS = ["Asian Paints", "Berger", "Nippon Paint", "Indigo Paints", "Dr. Fixit"]

IMPORTANT_POINTS_SAMPLE = {
    "Santhana Pandiyan": "Dealer requested Base Coat price list and sample package for 50 bags.",
    "Periyar Selvam": "Competitor Asian Paints offered 8% seasonal discount; dealer requested price match.",
    "Bala Murugan": "Collected ₹45,000 pending cheque payment for previous batch order.",
    "Rajeshwaran": "Urgent stock requirement reported for Waterproofing Coating (100 Ltrs).",
    "Vinoth Kumar": "New client enquiry registered for Wall Putty & Tile Adhesive dealership.",
    "Parthiban": "Dealer cleared partial outstanding payment via GPay ₹25,000.",
    "Sri Ram": "Client requested product demonstration for Exterior Weather Shield."
}

def reseed():
    print("Reseed metadata tables:", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Clearing existing transaction tables...")
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
        print("Existing transaction tables cleared.")

        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")

        # Generate dates spanning: today (0), last 7 days, last 30 days, last 120 days
        date_offsets = [0, 1, 2, 3, 5, 7, 10, 14, 20, 30, 45, 60, 90, 120]

        total_reports_created = 0

        for rep in REPS:
            # Create 1 report specifically for TODAY for each rep
            # Plus 5-6 historical reports for each rep
            rep_offsets = [0] + random.sample(date_offsets[1:], 6)

            for offset in rep_offsets:
                rpt_date = (today - datetime.timedelta(days=offset)).strftime("%Y-%m-%d")
                client = random.choice(CLIENT_NAMES)
                prod = random.choice(PRODUCTS)
                qty = random.randint(10, 80)
                amount = prod["price"] * qty
                coll_amt = amount * random.choice([0.5, 0.8, 1.0])
                fup_date = (today + datetime.timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d")

                is_today = (offset == 0)
                if is_today:
                    summary_text = IMPORTANT_POINTS_SAMPLE.get(rep, f"Visited {client}. Discussed product details and pricing.")
                else:
                    summary_text = f"Visited {client}. Discussed {prod['name']} requirements. Booked order for {qty} units."

                sentiment = random.choice(["Positive", "Positive", "Medium", "Positive"])
                priority = random.choice(["High", "Medium", "Medium", "Urgent"])

                sales_raw = f"Booked order for {qty} bags of {prod['name']} worth ₹{amount:,.2f}"
                collection_raw = f"Collected payment of ₹{coll_amt:,.2f} via GPay/Cheque"
                competition_raw = f"Competitor {random.choice(COMPETITORS)} active in local market"
                product_raw = f"Discussed {prod['name']} application and performance"
                price_raw = f"Shared updated price list for {prod['name']} at ₹{prod['price']}/unit"
                services_raw = f"Assured timely delivery within 24 hours to {client}"
                new_products_raw = "Introduced new Eco Waterproofing Range to dealer"
                most_sell_raw = f"Top moving item: {prod['name']}"
                pending_stock_raw = f"Stock level verified: {random.randint(5, 30)} units pending"

                report = Report(
                    representative=rep,
                    client_name=client,
                    date=rpt_date,
                    summary=summary_text,
                    sentiment=sentiment,
                    priority=priority,
                    voice_duration=float(random.randint(60, 240)),
                    file_path=f"uploads/voice/mock_{rep.lower().replace(' ', '_')}_{offset}.mp3",
                    follow_up_date=fup_date,
                    sales_raw=sales_raw,
                    collection_raw=collection_raw,
                    competition_raw=competition_raw,
                    product_raw=product_raw,
                    price_list_raw=price_raw,
                    our_services_raw=services_raw,
                    our_new_products_raw=new_products_raw,
                    most_sell_products_raw=most_sell_raw,
                    pending_stock_raw=pending_stock_raw,
                    model_used="qwen2.5:14b",
                    whisper_model_used="large-v3",
                    translation_model_used="NLLB-200"
                )
                db.add(report)
                db.flush()

                # Add Sales record
                sale = Sales(
                    report_id=report.id,
                    item_name=prod["name"],
                    quantity=qty,
                    amount=amount,
                    payment_status="Paid" if coll_amt >= amount else "Pending"
                )
                db.add(sale)

                # Add Collection record
                collection = Collection(
                    report_id=report.id,
                    amount_collected=coll_amt,
                    payment_method=random.choice(["GPay", "Cheque", "Bank Transfer"]),
                    reference_no=f"TXN{random.randint(100000, 999999)}"
                )
                db.add(collection)

                # Add PerformanceScore record (5 stars scale)
                s_sales = float(random.choice([4, 5, 4.5, 5]))
                s_coll = float(random.choice([4, 4.5, 5]))
                s_comp = float(random.choice([3, 4, 4.5]))
                s_prod = float(random.choice([4, 4.5, 5]))
                s_price = float(random.choice([3.5, 4, 4.5, 5]))
                s_serv = float(random.choice([4, 4.5, 5]))
                s_newp = float(random.choice([3.5, 4, 4.5]))
                s_most = float(random.choice([4, 4.5, 5]))
                s_stock = float(random.choice([3.5, 4, 4.5]))
                s_fup = float(random.choice([4.5, 5]))

                explanations = {
                    "sales": f"Successfully closed order worth ₹{amount:,.2f}",
                    "collection": f"Collected ₹{coll_amt:,.2f} payment",
                    "competition": "Gathered insights on competitor pricing",
                    "product": "Detailed product discussion completed",
                    "price_list": "Verified and explained price terms",
                    "our_services": "Promised priority delivery support",
                    "our_new_products": "Presented new products effectively",
                    "most_sell_products": "Reviewed demand for fast movers",
                    "pending_stock": "Audited client inventory levels",
                    "follow_up_date": f"Scheduled follow-up for {fup_date}"
                }

                perf = PerformanceScore(
                    report_id=report.id,
                    sales_score=s_sales,
                    collection_score=s_coll,
                    competition_score=s_comp,
                    product_score=s_prod,
                    price_list_score=s_price,
                    services_score=s_serv,
                    new_products_score=s_newp,
                    most_sell_products_score=s_most,
                    pending_stock_score=s_stock,
                    follow_up_score=s_fup,
                    explanations=json.dumps(explanations)
                )
                db.add(perf)

                # Add sample turns to Conversation
                db.add(Conversation(report_id=report.id, speaker="Sales Rep", text=f"Good morning, visiting {client} regarding {prod['name']} orders."))
                db.add(Conversation(report_id=report.id, speaker="Client", text=f"We need {qty} units. Please confirm pricing."))
                db.add(Conversation(report_id=report.id, speaker="Sales Rep", text=f"Confirmed at ₹{prod['price']} per unit. Delivery scheduled."))

                total_reports_created += 1

        db.commit()
        print(f"Seeding completed successfully! Created {total_reports_created} mock reports across {len(REPS)} sales representatives.")

    except Exception as e:
        db.rollback()
        print(f"Error during re-seeding: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    reseed()
