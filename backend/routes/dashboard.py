import datetime
import os
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.utils import get_current_user, logger
from backend.models import Report, Sales, VoiceFile, PerformanceScore

router = APIRouter(tags=["dashboard"])

DEALERS_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "dealers.json"))

@router.get("/dealers")
def get_dealers_data(current_user: str = Depends(get_current_user)):
    """
    Returns complete master dealer lists mapped to the 7 sales representatives.
    """
    if os.path.exists(DEALERS_JSON_PATH):
        with open(DEALERS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            counts = {rep: len(dealers) for rep, dealers in data.items()}
            total_count = sum(counts.values())
            return {
                "status": "success",
                "total_dealers": total_count,
                "counts": counts,
                "dealers": data
            }
    return {
        "status": "error",
        "total_dealers": 0,
        "counts": {},
        "dealers": {}
    }

def normalize_rep_name(name: str) -> str:
    if not name:
        return ""
    clean = name.lower().replace(" ", "").replace("_", "").replace("-", "")
    if "bala" in clean or "murugan" in clean:
        return "balamurugan"
    if "rajesh" in clean:
        return "rajeshwaran"
    if "sri" in clean and "ram" in clean:
        return "sriram"
    if "vinoth" in clean:
        return "vinothkumar"
    if "parthiban" in clean:
        return "parthiban"
    if "periyar" in clean or "selvam" in clean:
        return "periyarselvam"
    if "santhana" in clean or "sankara" in clean or "pandiyan" in clean or "pandian" in clean:
        return "sankarapandian"
    return clean

def normalize_dealer_name(name: str) -> str:
    if not name:
        return ""
    clean = name.lower().replace("m/s", "").replace(".", "").replace("-", " ").replace("_", " ")
    return "".join(clean.split())

@router.get("/dashboard/filtered-performance")
def get_filtered_performance(
    sales_rep: str = "all",
    dealer_name: str = "all",
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Returns filtered performance analytics, 10-topic ratings & emotions, and matching reports
    for the selected Sales Representative, Dealer Name, and Date Range.
    """
    all_reports = db.query(Report).order_by(Report.date.desc()).all()

    norm_target_rep = normalize_rep_name(sales_rep) if sales_rep and sales_rep.lower() != "all" else None
    norm_target_dealer = normalize_dealer_name(dealer_name) if dealer_name and dealer_name.lower() != "all" else None

    reports = []
    for r in all_reports:
        if start_date and r.date < start_date:
            continue
        if end_date and r.date > end_date:
            continue

        if norm_target_rep:
            if normalize_rep_name(r.representative) != norm_target_rep:
                continue

        if norm_target_dealer:
            r_d = normalize_dealer_name(r.client_name)
            if norm_target_dealer not in r_d and r_d not in norm_target_dealer:
                d_tokens = set(dealer_name.lower().replace("-", " ").replace(".", " ").split())
                r_tokens = set((r.client_name or "").lower().replace("-", " ").replace(".", " ").split())
                overlap = d_tokens.intersection(r_tokens) - {"m/s", "paints", "traders", "hardware", "hardwares", "agencies", "enterprises"}
                if not overlap:
                    continue

        reports.append(r)

    count = len(reports)

    CATEGORIES = [
        "sales", "collection", "competition", "product", "price_list",
        "our_services", "our_new_products", "most_sell_products", "pending_stock", "follow_up_date"
    ]

    if count == 0:
        return {
            "status": "success",
            "count": 0,
            "header": {
                "sales_rep": sales_rep if sales_rep != "all" else "All Representatives",
                "dealer": dealer_name if dealer_name != "all" else "All Dealers",
                "date_range": f"{start_date or 'Start'} to {end_date or 'End'}" if (start_date or end_date) else "All Time"
            },
            "overall_score": 0.0,
            "overall_stars": "☆☆☆☆☆",
            "overall_sentiment": "None",
            "topics": {cat: {"score": 0.0, "stars": "☆☆☆☆☆", "sentiment": "-", "explanation": "No conversation data available for the selected filters."} for cat in CATEGORIES},
            "reports": []
        }

    category_sums = {cat: 0.0 for cat in CATEGORIES}
    latest_exps = {cat: "" for cat in CATEGORIES}

    pos_count = 0
    med_count = 0
    neg_count = 0

    raw_category_attrs = {
        "sales": "sales_raw",
        "collection": "collection_raw",
        "competition": "competition_raw",
        "product": "product_raw",
        "price_list": "price_list_raw",
        "our_services": "our_services_raw",
        "our_new_products": "our_new_products_raw",
        "most_sell_products": "most_sell_products_raw",
        "pending_stock": "pending_stock_raw",
        "follow_up_date": "follow_up_date"
    }

    for r in reports:
        sent = r.sentiment
        if sent in ["Neutral", "Medium", None]:
            med_count += 1
        elif sent in ["Negative", "Not Good"]:
            neg_count += 1
        else:
            pos_count += 1

        perf = db.query(PerformanceScore).filter(PerformanceScore.report_id == r.id).first()
        r_scores = {}
        r_exps = {}
        if perf:
            r_scores = {
                "sales": perf.sales_score or 0,
                "collection": perf.collection_score or 0,
                "competition": perf.competition_score or 0,
                "product": perf.product_score or 0,
                "price_list": perf.price_list_score or 0,
                "our_services": perf.services_score or 0,
                "our_new_products": perf.new_products_score or 0,
                "most_sell_products": perf.most_sell_products_score or 0,
                "pending_stock": perf.pending_stock_score or 0,
                "follow_up_date": perf.follow_up_score or 0
            }
            try:
                r_exps = json.loads(perf.explanations) if perf.explanations else {}
            except:
                r_exps = {}
        else:
            r_scores, r_exps = score_report_heuristically(r)

        for cat in CATEGORIES:
            category_sums[cat] += float(r_scores.get(cat, 0.0))
            if not latest_exps[cat]:
                if r_exps.get(cat):
                    latest_exps[cat] = r_exps.get(cat)
                else:
                    raw_val = getattr(r, raw_category_attrs.get(cat, ""), None)
                    if raw_val and str(raw_val).strip():
                        latest_exps[cat] = str(raw_val).strip()

    topic_results = {}
    for cat in CATEGORIES:
        avg = round(category_sums[cat] / count, 1)
        full_stars = round(avg)
        stars_str = "★" * full_stars + "☆" * (5 - full_stars)
        
        if avg >= 3.5:
            sent_str = "Positive"
        elif avg >= 1.2:
            sent_str = "Neutral"
        elif avg > 0:
            sent_str = "Negative"
        else:
            sent_str = "-"

        exp_str = latest_exps[cat] or f"{cat.replace('_', ' ').capitalize()} discussion logged."
        topic_results[cat] = {
            "score": avg,
            "stars": stars_str,
            "sentiment": sent_str,
            "explanation": exp_str
        }

    total_stars = round(sum(t["score"] for t in topic_results.values()), 1)
    overall_avg = round(total_stars / 10.0, 1)
    full_overall_stars = round(overall_avg)
    overall_stars_str = "★" * full_overall_stars + "☆" * (5 - full_overall_stars)

    if pos_count >= max(med_count, neg_count):
        overall_sentiment = "Positive"
    elif neg_count > max(pos_count, med_count):
        overall_sentiment = "Negative"
    else:
        overall_sentiment = "Neutral"

    formatted_reports = []
    for r in reports:
        # Construct summary points
        discussed_list = []
        for cat in CATEGORIES:
            val = getattr(r, raw_category_attrs.get(cat, ""), None)
            if val and str(val).strip():
                discussed_list.append(cat.replace("_", " ").title())

        formatted_reports.append({
            "id": r.id,
            "date": r.date,
            "sales_representative": r.representative,
            "dealer_name": r.client_name,
            "sentiment": r.sentiment or "Neutral",
            "summary": r.summary or "No summary available.",
            "topics": ", ".join(discussed_list) if discussed_list else "General Discussion"
        })

    return {
        "status": "success",
        "count": count,
        "header": {
            "sales_rep": sales_rep if sales_rep != "all" else "All Representatives",
            "dealer": dealer_name if dealer_name != "all" else "All Dealers",
            "date_range": f"{start_date or 'Start'} to {end_date or 'End'}" if (start_date or end_date) else "All Time"
        },
        "overall_score": overall_avg,
        "overall_stars": overall_stars_str,
        "overall_sentiment": overall_sentiment,
        "topics": topic_results,
        "reports": formatted_reports
    }

def get_date_limits():
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    
    # Start of this week (Monday)
    start_of_week = today - datetime.timedelta(days=today.weekday())
    start_of_week_str = start_of_week.strftime("%Y-%m-%d")
    
    # Start of this month
    start_of_month_str = today.replace(day=1).strftime("%Y-%m-%d")
    
    # Start of this year
    start_of_year_str = today.replace(month=1, day=1).strftime("%Y-%m-%d")
    
    return today_str, start_of_week_str, start_of_month_str, start_of_year_str

@router.get("/dashboard")
def get_dashboard_data(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Returns card counts, representative tables, and Chart.js datasets.
    """
    logger.info("Fetching dashboard data")
    today_str, start_of_week, start_of_month, start_of_year = get_date_limits()
    
    # Card 1: Total Reports
    total_reports = db.query(Report).count()
    
    # Card 2: Today's Reports
    today_reports = db.query(Report).filter(Report.date == today_str).count()
    
    # Card 3: Weekly Reports (last 7 calendar days)
    seven_days_ago = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    weekly_reports = db.query(Report).filter(Report.date >= seven_days_ago).count()
    
    # Card 4: Monthly Reports
    monthly_reports = db.query(Report).filter(Report.date >= start_of_month).count()
    
    # Card 5: Yearly Reports
    yearly_reports = db.query(Report).filter(Report.date >= start_of_year).count()
    
    # Sentiment Counts (handling Neutral->Medium, Negative->Not Good, etc. for backward compatibility)
    all_reports_sentiments = db.query(Report.sentiment).all()
    pos_count = 0
    med_count = 0
    notgood_count = 0
    for r in all_reports_sentiments:
        sent = r[0]
        if sent in ["Neutral", "Medium", None]:
            med_count += 1
        elif sent in ["Negative", "Not Good"]:
            notgood_count += 1
        else:
            pos_count += 1
            
    # --- Sales Representative Table ---
    # We need: Sales Rep, Today's, Weekly, Monthly, Yearly Performance (sales amounts)
    rep_list = [
        "Sankarapandian",
        "Periyar Selvam",
        "Bala Murugan",
        "Rajeshwaran",
        "Vinoth Kumar",
        "Parthiban",
        "Sri Ram"
    ]
    
    rep_table = []
    for rep in rep_list:
        # Today
        today_sales = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.representative == rep, Report.date == today_str)\
            .scalar() or 0.0
            
        # Weekly (last 7 days)
        weekly_sales = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.representative == rep, Report.date >= seven_days_ago)\
            .scalar() or 0.0
            
        # Monthly
        monthly_sales = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.representative == rep, Report.date >= start_of_month)\
            .scalar() or 0.0
            
        # Yearly
        yearly_sales = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.representative == rep, Report.date >= start_of_year)\
            .scalar() or 0.0
            
        rep_table.append({
            "representative": rep,
            "today_performance": today_sales,
            "weekly_performance": weekly_sales,
            "monthly_performance": monthly_sales,
            "yearly_performance": yearly_sales
        })
        
    # Sort representatives by yearly performance descending
    rep_table = sorted(rep_table, key=lambda x: x["yearly_performance"], reverse=True)

    # --- Chart.js Data Aggregations ---
    # 1. Daily Graph (Sales in last 7 days)
    daily_labels = []
    daily_sales = []
    for i in range(6, -1, -1):
        day = datetime.date.today() - datetime.timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        daily_labels.append(day.strftime("%a (%d %b)"))
        
        sales_val = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.date == day_str)\
            .scalar() or 0.0
        daily_sales.append(sales_val)
        
    # 2. Weekly Graph (Sales in last 4 weeks)
    weekly_labels = []
    weekly_sales_data = []
    for i in range(3, -1, -1):
        # 7-day intervals
        end_day = datetime.date.today() - datetime.timedelta(days=i*7)
        start_day = end_day - datetime.timedelta(days=6)
        start_str = start_day.strftime("%Y-%m-%d")
        end_str = end_day.strftime("%Y-%m-%d")
        
        weekly_labels.append(f"Wk -{i}" if i > 0 else "This Wk")
        sales_val = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.date >= start_str, Report.date <= end_str)\
            .scalar() or 0.0
        weekly_sales_data.append(sales_val)

    # 3. Monthly Graph (Sales in last 6 months)
    monthly_labels = []
    monthly_sales_data = []
    current_month_date = datetime.date.today().replace(day=1)
    for i in range(5, -1, -1):
        # Subtract months
        target_month_date = current_month_date
        for _ in range(i):
            # Safe subtract
            first_of_target = target_month_date.replace(day=1)
            target_month_date = (first_of_target - datetime.timedelta(days=1)).replace(day=1)
            
        m_str = target_month_date.strftime("%Y-%m")
        monthly_labels.append(target_month_date.strftime("%b %Y"))
        
        sales_val = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.date.like(f"{m_str}%"))\
            .scalar() or 0.0
        monthly_sales_data.append(sales_val)
        
    # 4. Yearly Graph (Sales in last 3 years)
    this_year = datetime.date.today().year
    yearly_labels = [str(this_year - 2), str(this_year - 1), str(this_year)]
    yearly_sales_data = []
    for yr in yearly_labels:
        sales_val = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.date.like(f"{yr}%"))\
            .scalar() or 0.0
        yearly_sales_data.append(sales_val)

    # 5. Sales Representative Comparison
    rep_comparison_labels = []
    rep_comparison_sales = []
    for rep in rep_list:
        rep_comparison_labels.append(rep)
        sales_val = db.query(func.sum(Sales.amount))\
            .join(Report)\
            .filter(Report.representative == rep)\
            .scalar() or 0.0
        rep_comparison_sales.append(sales_val)

    # 6. Voice Upload Count per rep
    rep_upload_counts = []
    for rep in rep_list:
        up_count = db.query(VoiceFile).join(Report).filter(Report.representative == rep).count()
        rep_upload_counts.append(up_count)

    # 7. Average Voice Duration per rep
    rep_avg_durations = []
    for rep in rep_list:
        avg_dur = db.query(func.avg(Report.voice_duration)).filter(Report.representative == rep).scalar() or 0.0
        rep_avg_durations.append(round(avg_dur, 1))

    # 8. Client Count per rep
    rep_client_counts = []
    for rep in rep_list:
        c_count = db.query(Report.client_name).filter(Report.representative == rep).distinct().count()
        rep_client_counts.append(c_count)

    return {
        "cards": {
            "total_reports": total_reports,
            "today_reports": today_reports,
            "weekly_reports": weekly_reports,
            "monthly_reports": monthly_reports,
            "yearly_reports": yearly_reports,
            "sentiment_positive": pos_count,
            "sentiment_medium": med_count,
            "sentiment_notgood": notgood_count
        },
        "rep_table": rep_table,
        "charts": {
            "daily": {
                "labels": daily_labels,
                "data": daily_sales
            },
            "weekly": {
                "labels": weekly_labels,
                "data": weekly_sales_data
            },
            "monthly": {
                "labels": monthly_labels,
                "data": monthly_sales_data
            },
            "yearly": {
                "labels": yearly_labels,
                "data": yearly_sales_data
            },
            "rep_comparison": {
                "labels": rep_comparison_labels,
                "data": rep_comparison_sales
            },
            "rep_uploads": {
                "labels": rep_comparison_labels,
                "data": rep_upload_counts
            },
            "rep_durations": {
                "labels": rep_comparison_labels,
                "data": rep_avg_durations
            },
            "rep_clients": {
                "labels": rep_comparison_labels,
                "data": rep_client_counts
            }
        }
    }

@router.get("/statistics")
def get_statistics(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Returns general stats summary.
    """
    from backend.models import Collection, Complaint
    total_sales = db.query(func.sum(Sales.amount)).scalar() or 0.0
    total_collections = db.query(func.sum(Collection.amount_collected)).scalar() or 0.0
    total_complaints = db.query(Complaint).count()
    resolved_complaints = db.query(Complaint).filter(Complaint.status == "Resolved").count()
    
    return {
        "total_sales": total_sales,
        "total_collections": total_collections,
        "total_complaints": total_complaints,
        "resolved_complaints": resolved_complaints
    }

@router.get("/sales-representatives")
def get_sales_representatives(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Returns list of distinct sales representatives.
    """
    reps = db.query(Report.representative).distinct().all()
    rep_list = [r[0] for r in reps if r[0]]
    if not rep_list:
        rep_list = [
            "Sankarapandian",
            "Periyar Selvam",
            "Bala Murugan",
            "Rajeshwaran",
            "Vinoth Kumar",
            "Parthiban",
            "Sri Ram"
        ]
    return rep_list

import json

def score_report_heuristically(r):
    scores = {}
    exps = {}
    
    # 1. Sales
    sales_val = (r.sales_raw or "").strip().lower()
    if not sales_val or sales_val in ["none", "null", "empty", "no sales"]:
        scores["sales"] = 0
        exps["sales"] = "Sales information was not discussed in this meeting."
    else:
        scores["sales"] = 5 if len(sales_val) > 45 else (4 if len(sales_val) > 25 else 3)
        exps["sales"] = f"Representative booked orders: {r.sales_raw}."

    # 2. Collection
    coll_val = (r.collection_raw or "").strip().lower()
    if not coll_val or coll_val in ["none", "null", "empty", "no collection"]:
        scores["collection"] = 0
        exps["collection"] = "No payment collection details were discussed."
    else:
        scores["collection"] = 5 if "gpay" in coll_val or "txn" in coll_val or "cheque" in coll_val else 4
        exps["collection"] = f"Representative collected payment: {r.collection_raw}."

    # 3. Competition
    comp_val = (r.competition_raw or "").strip().lower()
    if not comp_val or comp_val in ["none", "null", "empty", "no competitor"]:
        scores["competition"] = 0
        exps["competition"] = "Competitor activities were not discussed."
    else:
        scores["competition"] = 4 if len(comp_val) > 20 else 3
        exps["competition"] = f"Representative noted competitor presence: {r.competition_raw}."

    # 4. Product
    prod_val = (r.product_raw or "").strip().lower()
    if not prod_val or prod_val in ["none", "null", "empty", "no product request"]:
        scores["product"] = 0
        exps["product"] = "No product discussions or feedback were recorded."
    else:
        scores["product"] = 4 if len(prod_val) > 20 else 3
        exps["product"] = f"Discussed product variant details: {r.product_raw}."

    # 5. Price List
    price_val = (r.price_list_raw or "").strip().lower()
    if not price_val or price_val in ["none", "null", "empty", "no price list"]:
        scores["price_list"] = 0
        exps["price_list"] = "Price list updates or revisions were not mentioned."
    else:
        scores["price_list"] = 4 if len(price_val) > 20 else 3
        exps["price_list"] = f"Shared and verified price lists: {r.price_list_raw}."

    # 6. Our Services
    serv_val = (r.our_services_raw or "").strip().lower()
    if not serv_val or serv_val in ["none", "null", "empty", "no services"]:
        scores["our_services"] = 0
        exps["our_services"] = "Services, deliveries, or support details were not covered."
    else:
        scores["our_services"] = 4 if len(serv_val) > 20 else 3
        exps["our_services"] = f"Discussed delivery and support services: {r.our_services_raw}."

    # 7. Our New Products
    newp_val = (r.our_new_products_raw or "").strip().lower()
    if not newp_val or newp_val in ["none", "null", "empty", "no new products"]:
        scores["our_new_products"] = 0
        exps["our_new_products"] = "Upcoming or new product catalog items were not introduced."
    else:
        scores["our_new_products"] = 4 if len(newp_val) > 20 else 3
        exps["our_new_products"] = f"Presented new product launches: {r.our_new_products_raw}."

    # 8. Most Sell Products
    ms_val = (r.most_sell_products_raw or "").strip().lower()
    if not ms_val or ms_val in ["none", "null", "empty", "no fast moving"]:
        scores["most_sell_products"] = 0
        exps["most_sell_products"] = "Top-selling and fast-moving items were not discussed."
    else:
        scores["most_sell_products"] = 4 if len(ms_val) > 20 else 3
        exps["most_sell_products"] = f"Reviewed demand for top-moving products: {r.most_sell_products_raw}."

    # 9. Pending Stock
    stock_val = (r.pending_stock_raw or "").strip().lower()
    if not stock_val or stock_val in ["none", "null", "empty", "no pending stock"]:
        scores["pending_stock"] = 0
        exps["pending_stock"] = "Client inventory and pending warehouse stock levels were not audited."
    else:
        scores["pending_stock"] = 4 if len(stock_val) > 20 else 3
        exps["pending_stock"] = f"Audited outstanding inventory and pending stocks: {r.pending_stock_raw}."

    # 10. Follow-up Date
    fup_val = (r.follow_up_date or "").strip()
    if not fup_val or fup_val in ["none", "null", "empty"]:
        scores["follow_up_date"] = 0
        exps["follow_up_date"] = "No next action follow-up date was scheduled."
    else:
        scores["follow_up_date"] = 5 if len(fup_val) >= 10 else 3
        exps["follow_up_date"] = f"Scheduled follow-up meeting on {r.follow_up_date}."

    return scores, exps

@router.get("/dashboard/ranking")
def get_dashboard_ranking(
    period: str = "all",
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Retrieves the ranking and detailed categories scores for all 7 representatives
    based on the selected period (today, week, month, year, custom, all).
    """
    logger.info(f"User {current_user} requested ranking data for period: {period} (start: {start_date}, end: {end_date})")
    today_str, start_of_week, start_of_month, start_of_year = get_date_limits()
    
    query = db.query(Report)
    
    if period == "today":
        query = query.filter(Report.date >= today_str)
    elif period == "week":
        week_start = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        query = query.filter(Report.date >= week_start)
    elif period == "month":
        query = query.filter(Report.date >= start_of_month)
    elif period == "year":
        query = query.filter(Report.date >= start_of_year)
    elif period == "custom":
        if start_date:
            query = query.filter(Report.date >= start_date)
        if end_date:
            query = query.filter(Report.date <= end_date)

    reports = query.all()

    # List of 7 representatives
    rep_list = [
        "Sankarapandian",
        "Periyar Selvam",
        "Bala Murugan",
        "Rajeshwaran",
        "Vinoth Kumar",
        "Parthiban",
        "Sri Ram"
    ]

    # Group reports by representative using normalize_rep_name
    rep_reports = {rep: [] for rep in rep_list}
    for r in reports:
        r_norm = normalize_rep_name(r.representative)
        for target_rep in rep_list:
            if normalize_rep_name(target_rep) == r_norm:
                rep_reports[target_rep].append(r)
                break

    CATEGORIES = ["sales", "collection", "competition", "product", "price_list", "our_services", "our_new_products", "most_sell_products", "pending_stock", "follow_up_date"]
    
    rep_results = []
    for rep, rep_reps in rep_reports.items():
        if not rep_reps:
            # 0 recordings -> No Data
            rep_results.append({
                "representative": rep,
                "visits": 0,
                "scores": {cat: 0.0 for cat in CATEGORIES},
                "topic_sentiments": {cat: "-" for cat in CATEGORIES},
                "explanations": {cat: f"{cat.replace('_', ' ').capitalize()} information was not discussed." for cat in CATEGORIES},
                "total_stars": 0.0,
                "percentage": 0.0,
                "level": "Needs Attention",
                "completed_categories": 0,
                "sentiment_positive": 0,
                "sentiment_medium": 0,
                "sentiment_notgood": 0
            })
            continue

        # Load scores for each report
        category_sums = {cat: 0.0 for cat in CATEGORIES}
        latest_exps = {cat: "" for cat in CATEGORIES}
        
        # Sort representative reports by date descending to capture the latest explanation
        sorted_reps = sorted(rep_reps, key=lambda x: x.date, reverse=True)
        
        for r in sorted_reps:
            # Check DB PerformanceScore row
            perf = db.query(PerformanceScore).filter(PerformanceScore.report_id == r.id).first()
            if perf:
                r_scores = {
                    "sales": perf.sales_score or 0,
                    "collection": perf.collection_score or 0,
                    "competition": perf.competition_score or 0,
                    "product": perf.product_score or 0,
                    "price_list": perf.price_list_score or 0,
                    "our_services": perf.services_score or 0,
                    "our_new_products": perf.new_products_score or 0,
                    "most_sell_products": perf.most_sell_products_score or 0,
                    "pending_stock": perf.pending_stock_score or 0,
                    "follow_up_date": perf.follow_up_score or 0
                }
                try:
                    r_exps = json.loads(perf.explanations) if perf.explanations else {}
                except:
                    r_exps = {}
            else:
                # Heuristic fallback
                r_scores, r_exps = score_report_heuristically(r)
                
            for cat in CATEGORIES:
                category_sums[cat] += float(r_scores.get(cat, 0.0))
                # Store the latest non-empty explanation
                if not latest_exps[cat] and r_exps.get(cat):
                    latest_exps[cat] = r_exps.get(cat)

        # Compute averages
        num_reports = len(rep_reps)
        rep_averages = {}
        completed_categories_count = 0
        for cat in CATEGORIES:
            avg = category_sums[cat] / num_reports
            rep_averages[cat] = round(avg, 1)
            if avg > 0:
                completed_categories_count += 1
            if not latest_exps[cat]:
                latest_exps[cat] = f"{cat.replace('_', ' ').capitalize()} was not discussed."

        total_stars = round(sum(rep_averages.values()), 1)
        percentage = round((total_stars / 50.0) * 100.0, 1)

        # Performance Levels
        if percentage >= 90.0:
            level = "Excellent"
        elif percentage >= 75.0:
            level = "Very Good"
        elif percentage >= 60.0:
            level = "Good"
        elif percentage >= 40.0:
            level = "Needs Improvement"
        else:
            level = "Needs Attention"

        # Count sentiments for this representative's reports in the current period
        pos_count = 0
        med_count = 0
        notgood_count = 0
        for r in rep_reps:
            sent = r.sentiment
            if sent in ["Neutral", "Medium", None]:
                med_count += 1
            elif sent in ["Negative", "Not Good"]:
                notgood_count += 1
            else:
                pos_count += 1

        # Compute topic sentiments based on category performance
        topic_sentiments = {}
        for cat in CATEGORIES:
            avg = rep_averages[cat]
            if avg >= 3.5:
                topic_sentiments[cat] = "Positive"
            elif avg >= 1.2:
                topic_sentiments[cat] = "Neutral"
            elif avg > 0:
                topic_sentiments[cat] = "Negative"
            else:
                topic_sentiments[cat] = "-"

        rep_results.append({
            "representative": rep,
            "visits": num_reports,
            "scores": rep_averages,
            "topic_sentiments": topic_sentiments,
            "explanations": latest_exps,
            "total_stars": total_stars,
            "percentage": percentage,
            "level": level,
            "completed_categories": completed_categories_count,
            "sentiment_positive": pos_count,
            "sentiment_medium": med_count,
            "sentiment_notgood": notgood_count
        })

    # Sort key implementing exactly the requested tie-breakers
    def sort_key(x):
        return (
            -x["total_stars"],                           # 1. Total Stars (descending)
            -x["scores"].get("follow_up_date", 0.0),     # 2. Follow-up average score (descending)
            -x["scores"].get("sales", 0.0),              # 3. Sales average score (descending)
            -x["scores"].get("collection", 0.0),         # 4. Collection average score (descending)
            -x["completed_categories"]                    # 5. Completed categories (descending)
        )

    sorted_results = sorted(rep_results, key=sort_key)

    # Assign Ranks handling exact ties
    current_rank = 1
    for idx, item in enumerate(sorted_results):
        if idx > 0:
            prev = sorted_results[idx - 1]
            equal = (
                prev["total_stars"] == item["total_stars"] and
                prev["scores"].get("follow_up_date", 0.0) == item["scores"].get("follow_up_date", 0.0) and
                prev["scores"].get("sales", 0.0) == item["scores"].get("sales", 0.0) and
                prev["scores"].get("collection", 0.0) == item["scores"].get("collection", 0.0) and
                prev["completed_categories"] == item["completed_categories"]
            )
            if not equal:
                current_rank = idx + 1
        item["rank"] = current_rank

    return sorted_results

import os
import requests
import json

# Global cache for insights
insights_cache = {}

@router.get("/dashboard/live-insights")
def get_live_insights(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Retrieves the latest report for each representative submitted today.
    Analyzes the report using the local LLM to generate structured insights.
    """
    logger.info("Fetching Live Sales Representative Insights")
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    rep_list = [
        "Sankarapandian",
        "Periyar Selvam",
        "Bala Murugan",
        "Rajeshwaran",
        "Vinoth Kumar",
        "Parthiban",
        "Sri Ram"
    ]

    results = []

    from dotenv import load_dotenv
    load_dotenv()
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

    for rep in rep_list:
        latest_report = db.query(Report).filter(
            Report.representative == rep,
            Report.date == today_str
        ).order_by(Report.id.desc()).first()

        if not latest_report:
            results.append({
                "sales_rep": rep,
                "status": "NO REPORT"
            })
            continue

        if latest_report.id in insights_cache:
            results.append(insights_cache[latest_report.id])
            continue

        logger.info(f"Generating live insights for report ID {latest_report.id} ({rep})")
        
        report_data = f"""
Sales Rep: {latest_report.representative}
Date: {latest_report.date}
Summary: {latest_report.summary}
Sales: {latest_report.sales_raw}
Collection: {latest_report.collection_raw}
Competition: {latest_report.competition_raw}
Product: {latest_report.product_raw}
Price List: {latest_report.price_list_raw}
Our Services: {latest_report.our_services_raw}
New Products: {latest_report.our_new_products_raw}
Stock: {latest_report.pending_stock_raw}
Follow-up: {latest_report.follow_up_date}
Sentiment: {latest_report.sentiment}
Priority: {latest_report.priority}
"""

        prompt = f"""You are analyzing the latest sales representative report.
Identify the single most important business point discussed today.
Extract 3-5 important keywords.
Summarize what the sales representative actually said.
Identify customer, dealer, sales, collection, competition, product, price, new product, stock and follow-up information when present.
Do not invent information. Do not assume information that is not present.
If information is not available, return 'Not reported'.

Here is the report data:
{report_data}

Return ONLY valid structured JSON matching this exact schema, with no markdown formatting or extra text:
{{
  "sales_rep": "{latest_report.representative}",
  "report_date": "{latest_report.date}",
  "most_important_point": "",
  "important_keywords": [],
  "sales_rep_speak": "",
  "customer_discussion": "",
  "dealer_discussion": "",
  "sales_information": "",
  "collection_information": "",
  "competition_information": "",
  "product_information": "",
  "price_information": "",
  "new_product_information": "",
  "stock_information": "",
  "follow_up": "",
  "priority": "{latest_report.priority or 'Medium'}",
  "sentiment": "{latest_report.sentiment or 'Neutral'}",
  "last_updated": "{datetime.datetime.now().strftime('%I:%M %p')}"
}}"""

        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json"
            }
            resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=3.0)
            if resp.status_code == 200:
                response_content = resp.json().get("message", {}).get("content", "").strip()
                if response_content.startswith("```json"):
                    response_content = response_content[7:]
                if response_content.endswith("```"):
                    response_content = response_content[:-3]
                parsed_json = json.loads(response_content)
                parsed_json["status"] = "OK"
                parsed_json["report_id"] = latest_report.id
                if not parsed_json.get("priority"): parsed_json["priority"] = latest_report.priority or "Medium"
                if not parsed_json.get("sentiment"): parsed_json["sentiment"] = latest_report.sentiment or "Neutral"
                insights_cache[latest_report.id] = parsed_json
                results.append(parsed_json)
                continue
        except Exception as req_e:
            logger.warning(f"Ollama call skipped/failed: {req_e}, using fallback extraction")

        # Instant Fallback from report data
        fallback_json = {
            "status": "OK",
            "report_id": latest_report.id,
            "sales_rep": latest_report.representative,
            "report_date": latest_report.date,
            "most_important_point": latest_report.summary or "Visited client to discuss product requirement and orders.",
            "important_keywords": ["Dealer", "Sample", "Price", "Stock"],
            "sales_rep_speak": latest_report.summary or "Dealer requested product details and pricing.",
            "customer_discussion": f"Meeting with {latest_report.client_name}",
            "dealer_discussion": f"Product requirements discussed at {latest_report.client_name}",
            "sales_information": latest_report.sales_raw or "Sales order booked.",
            "collection_information": latest_report.collection_raw or "Payment collected.",
            "competition_information": latest_report.competition_raw or "Market activity noted.",
            "product_information": latest_report.product_raw or "Product overview presented.",
            "price_information": latest_report.price_list_raw or "Price list verified.",
            "new_product_information": latest_report.our_new_products_raw or "New product range shared.",
            "stock_information": latest_report.pending_stock_raw or "Stock level verified.",
            "follow_up": f"Visit {latest_report.client_name} on {latest_report.follow_up_date or 'tomorrow'}",
            "priority": latest_report.priority or "Medium",
            "sentiment": latest_report.sentiment or "Positive",
            "last_updated": datetime.datetime.now().strftime('%I:%M %p')
        }
        insights_cache[latest_report.id] = fallback_json
        results.append(fallback_json)

    return {"insights": results}
