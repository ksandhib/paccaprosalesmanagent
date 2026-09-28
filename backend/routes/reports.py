from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session, joinedload
from typing import List
from backend.database import get_db
from backend.utils import get_current_user, logger
from backend.models import Report, Sales, Collection, Competitor, ProductRequest, Complaint, Conversation
from backend.schemas import ReportSummarySchema, ReportDetailSchema

router = APIRouter(tags=["reports"])

@router.get("/reports", response_model=List[ReportDetailSchema])
def get_all_reports(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Returns all reports with sales, collections, and complaints joined
    for display in the DataTable.
    """
    logger.info("Fetching all reports with full associations")
    reports = db.query(Report).options(
        joinedload(Report.sales_details),
        joinedload(Report.collection_details),
        joinedload(Report.complaints),
        joinedload(Report.product_requests),
        joinedload(Report.competitor_activities),
        joinedload(Report.conversations)
    ).order_by(Report.date.desc(), Report.id.desc()).all()
    
    # Dynamically map values for frontend display compatibility
    for r in reports:
        if r.sentiment in ["Neutral", "Medium", None]:
            r.sentiment = "Medium"
        elif r.sentiment in ["Negative", "Not Good"]:
            r.sentiment = "Not Good"
        else:
            r.sentiment = "Positive"
            
    return reports

@router.get("/report/{report_id}", response_model=ReportDetailSchema)
def get_report_by_id(report_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Returns a single report details by ID, including complete dialogue history.
    """
    logger.info(f"Fetching report detail for ID: {report_id}")
    report = db.query(Report).options(
        joinedload(Report.sales_details),
        joinedload(Report.collection_details),
        joinedload(Report.complaints),
        joinedload(Report.product_requests),
        joinedload(Report.competitor_activities),
        joinedload(Report.conversations)
    ).filter(Report.id == report_id).first()
    
    if not report:
        logger.warning(f"Report ID {report_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
        
    # Dynamically map value for frontend display compatibility
    if report.sentiment in ["Neutral", "Medium", None]:
        report.sentiment = "Medium"
    elif report.sentiment in ["Negative", "Not Good"]:
        report.sentiment = "Not Good"
    else:
        report.sentiment = "Positive"
        
    return report

@router.post("/reports", status_code=status.HTTP_201_CREATED)
def create_manual_report(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    logger.info(f"User {current_user} creating manual daily report")
    try:
        sentiment = payload.get("sentiment", "Medium")
        if sentiment not in ["Positive", "Medium", "Not Good"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid sentiment. Sentiment must be: Positive, Medium, or Not Good"
            )
            
        # Create Report object
        report = Report(
            representative=payload.get("representative"),
            date=payload.get("date"),
            client_name=payload.get("client_name"),
            summary=payload.get("summary"),
            sentiment=sentiment,
            priority=payload.get("priority", "Medium"),
            voice_duration=0.0,  # Manual report has 0 duration
            file_path="Manual Entry",
            follow_up_date=payload.get("follow_up_date"),
            sales_raw=payload.get("sales_raw"),
            collection_raw=payload.get("collection_raw"),
            competition_raw=payload.get("competition_raw"),
            product_raw=payload.get("product_raw"),
            price_list_raw=payload.get("price_list_raw"),
            our_services_raw=payload.get("our_services_raw"),
            our_new_products_raw=payload.get("our_new_products_raw"),
            most_sell_products_raw=payload.get("most_sell_products_raw"),
            pending_stock_raw=payload.get("pending_stock_raw")
        )
        db.add(report)
        db.flush() # get report.id
        
        # Now populate child tables for stats backward compatibility
        # 1. Sales details
        sales_data = payload.get("sales_details", {})
        if sales_data and sales_data.get("item_name"):
            db.add(Sales(
                report_id=report.id,
                item_name=sales_data.get("item_name"),
                quantity=int(sales_data.get("quantity") or 0),
                amount=float(sales_data.get("amount") or 0.0),
                payment_status="Pending"
            ))
            
        # 2. Collection details
        coll_data = payload.get("collection_details", {})
        if coll_data and coll_data.get("amount_collected"):
            db.add(Collection(
                report_id=report.id,
                amount_collected=float(coll_data.get("amount_collected") or 0.0),
                payment_method=coll_data.get("payment_method"),
                reference_no=coll_data.get("status")
            ))
            
        # 3. Competition details
        comp_data = payload.get("competition_details", {})
        if comp_data and comp_data.get("competitor_name"):
            db.add(Competitor(
                report_id=report.id,
                competitor_name=comp_data.get("competitor_name"),
                activity_details=comp_data.get("remarks")
            ))
            
        # 4. Product request details
        prod_data = payload.get("product_details", {})
        if prod_data and prod_data.get("product_name"):
            db.add(ProductRequest(
                report_id=report.id,
                product_name=prod_data.get("product_name"),
                details=prod_data.get("remarks")
            ))
            
        # 5. Service feedback complaint
        srv_data = payload.get("service_details", {})
        if srv_data and srv_data.get("complaint"):
            db.add(Complaint(
                report_id=report.id,
                description=srv_data.get("complaint"),
                severity="Medium",
                status="Open"
            ))

        db.commit()
        return {"status": "success", "report_id": report.id}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating manual report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
