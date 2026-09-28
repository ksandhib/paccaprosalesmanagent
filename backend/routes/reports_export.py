import io
import csv
import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from backend.database import get_db
from backend.utils import get_current_user, logger
from backend.models import Report

# reportlab for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# openpyxl for Excel generation
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

router = APIRouter(tags=["reports_export"])

@router.get("/reports/export/csv")
def export_reports_csv(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Exports all report records into a CSV format file stream.
    """
    logger.info(f"User {current_user} requested CSV export of all reports")
    reports = db.query(Report).options(
        joinedload(Report.sales_details),
        joinedload(Report.collection_details),
        joinedload(Report.complaints)
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Report ID", "Representative", "Client Name", "Date", "Summary",
        "Sales", "Collection", "Competition", "Product", "Price List",
        "Our Services", "Our New Products", "Most Sell Products", "Pending Stock",
        "Follow-up Date", "Duration (s)", "Sentiment", "Priority"
    ])

    for r in reports:
        writer.writerow([
            r.id, r.representative, r.client_name, r.date, r.summary or "",
            r.sales_raw or "None", r.collection_raw or "None", r.competition_raw or "None",
            r.product_raw or "None", r.price_list_raw or "None", r.our_services_raw or "None",
            r.our_new_products_raw or "None", r.most_sell_products_raw or "None", r.pending_stock_raw or "None",
            r.follow_up_date or "None", r.voice_duration, r.sentiment, r.priority
        ])

    output.seek(0)
    response = StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8')), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=paccapro_sales_report.csv"
    return response

@router.get("/reports/export/excel")
def export_reports_excel(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Generates a professional multi-sheet Excel spreadsheet of reports.
    """
    logger.info(f"User {current_user} requested Excel export of all reports")
    reports = db.query(Report).options(
        joinedload(Report.sales_details),
        joinedload(Report.collection_details),
        joinedload(Report.complaints)
    ).all()

    wb = openpyxl.Workbook()
    
    # Sheet 1: Reports Summary
    ws = wb.active
    ws.title = "Reports Overview"
    
    # Style configuration
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark navy blue
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    
    headers = [
        "Report ID", "Representative", "Client Name", "Date", "Summary",
        "Sales", "Collection", "Competition", "Product", "Price List",
        "Our Services", "Our New Products", "Most Sell Products", "Pending Stock",
        "Follow-up Date", "Duration (s)", "Sentiment", "Priority"
    ]
    
    ws.append(headers)
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for r in reports:
        ws.append([
            r.id, r.representative, r.client_name, r.date, r.summary or "",
            r.sales_raw or "None", r.collection_raw or "None", r.competition_raw or "None",
            r.product_raw or "None", r.price_list_raw or "None", r.our_services_raw or "None",
            r.our_new_products_raw or "None", r.most_sell_products_raw or "None", r.pending_stock_raw or "None",
            r.follow_up_date or "None", r.voice_duration, r.sentiment, r.priority
        ])

    # Dynamic column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    # Save to binary output
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = "attachment; filename=paccapro_sales_report.xlsx"
    return response

@router.get("/reports/export/pdf")
def export_reports_pdf(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Generates a print-ready PDF summary report.
    """
    logger.info(f"User {current_user} requested PDF export of all reports")
    reports = db.query(Report).options(
        joinedload(Report.sales_details),
        joinedload(Report.collection_details),
        joinedload(Report.complaints)
    ).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styling
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=15
    )
    
    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#475569'),
        spaceAfter=20
    )
    
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )

    # Header section
    story.append(Paragraph("PaccaPro AI Sales Analysis System (PASAS)", title_style))
    story.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | Requestor: {current_user}", meta_style))
    story.append(Spacer(1, 10))

    # Compile table data
    table_data = [[
        Paragraph("<b>Rep</b>", cell_style),
        Paragraph("<b>Date</b>", cell_style),
        Paragraph("<b>Client Name</b>", cell_style),
        Paragraph("<b>Summary Outline</b>", cell_style),
        Paragraph("<b>Sales</b>", cell_style),
        Paragraph("<b>Collection</b>", cell_style),
        Paragraph("<b>Sentiment</b>", cell_style)
    ]]

    for r in reports:
        table_data.append([
            Paragraph(r.representative, cell_style),
            Paragraph(r.date, cell_style),
            Paragraph(r.client_name, cell_style),
            Paragraph(r.summary or "", cell_style),
            Paragraph(r.sales_raw or "None", cell_style),
            Paragraph(r.collection_raw or "None", cell_style),
            Paragraph(r.sentiment, cell_style)
        ])

    # Page width mapping
    col_widths = [60, 60, 90, 120, 70, 70, 60]
    
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(t)
    doc.build(story)
    
    buffer.seek(0)
    response = StreamingResponse(buffer, media_type="application/pdf")
    response.headers["Content-Disposition"] = "attachment; filename=paccapro_sales_report.pdf"
    return response
