import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    representative = Column(String, index=True, nullable=False)
    client_name = Column(String, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)  # Format: YYYY-MM-DD
    summary = Column(Text, nullable=True)
    sentiment = Column(String, default="Neutral")  # Positive, Negative, Neutral
    priority = Column(String, default="Medium")  # High, Medium, Low
    voice_duration = Column(Float, default=0.0)    # In seconds
    file_path = Column(String, nullable=True)
    follow_up_date = Column(String, nullable=True)
    sales_raw = Column(Text, nullable=True)
    collection_raw = Column(Text, nullable=True)
    competition_raw = Column(Text, nullable=True)
    product_raw = Column(Text, nullable=True)
    price_list_raw = Column(Text, nullable=True)
    our_services_raw = Column(Text, nullable=True)
    our_new_products_raw = Column(Text, nullable=True)
    most_sell_products_raw = Column(Text, nullable=True)
    pending_stock_raw = Column(Text, nullable=True)
    model_used = Column(String, nullable=True, default="qwen2.5:14b")
    whisper_model_used = Column(String, nullable=True, default="large-v3")
    translation_model_used = Column(String, nullable=True, default="NLLB-200")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    sales_details = relationship("Sales", back_populates="report", cascade="all, delete-orphan")
    collection_details = relationship("Collection", back_populates="report", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="report", cascade="all, delete-orphan")
    product_requests = relationship("ProductRequest", back_populates="report", cascade="all, delete-orphan")
    competitor_activities = relationship("Competitor", back_populates="report", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="report", cascade="all, delete-orphan")
    voice_files = relationship("VoiceFile", back_populates="report", cascade="all, delete-orphan")

class VoiceFile(Base):
    __tablename__ = "voice_files"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True, index=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    processed_path = Column(String, nullable=True)
    status = Column(String, default="Pending")  # Pending, Processing, Completed, Failed
    sha256_hash = Column(String, unique=True, index=True, nullable=True)  # SHA-256 for duplicate checking
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("Report", back_populates="voice_files")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    speaker = Column(String, nullable=False)  # "Sales Rep", "Client", "AI Agent"
    text = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=True)   # Timestamp in seconds from start

    report = relationship("Report", back_populates="conversations")

class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    summary_text = Column(Text, nullable=False)

class Sales(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    item_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    amount = Column(Float, default=0.0)
    payment_status = Column(String, default="Pending")  # Paid, Pending, Partially Paid

    report = relationship("Report", back_populates="sales_details")

class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    amount_collected = Column(Float, default=0.0)
    payment_method = Column(String, nullable=True)  # Cash, Check, Bank Transfer, GPay
    reference_no = Column(String, nullable=True)

    report = relationship("Report", back_populates="collection_details")

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    severity = Column(String, default="Low")  # High, Medium, Low
    status = Column(String, default="Open")  # Open, Resolved, In Progress

    report = relationship("Report", back_populates="complaints")

class ProductRequest(Base):
    __tablename__ = "product_requests"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    product_name = Column(String, nullable=False)
    details = Column(Text, nullable=True)

    report = relationship("Report", back_populates="product_requests")

class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    competitor_name = Column(String, nullable=False)
    activity_details = Column(Text, nullable=True)

    report = relationship("Report", back_populates="competitor_activities")

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=True)


class PosterAnalysis(Base):
    __tablename__ = "poster_analysis"

    id = Column(Integer, primary_key=True, index=True)
    poster_title = Column(String, index=True, nullable=True)
    poster_category = Column(String, index=True, nullable=True)
    main_heading = Column(String, nullable=True)
    sub_heading = Column(String, nullable=True)
    filename = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    image_hash = Column(String, unique=True, index=True, nullable=False)
    ocr_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    detailed_summary = Column(Text, nullable=True)
    highlights = Column(Text, nullable=True)
    important_information = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    tone = Column(String, nullable=True)
    target_audience = Column(Text, nullable=True)
    call_to_action = Column(Text, nullable=True)
    ocr_confidence = Column(Float, default=1.0)
    ai_confidence = Column(Float, default=1.0)
    uploaded_by = Column(String, nullable=True)
    
    # Newly added vision analysis fields
    brand = Column(String, nullable=True)
    product = Column(String, nullable=True)
    price = Column(String, nullable=True)
    offer = Column(String, nullable=True)
    marketing_score = Column(Integer, default=0)
    marketing_suggestions = Column(Text, nullable=True)
    improvement_suggestions = Column(Text, nullable=True)
    marketing_analysis = Column(Text, nullable=True)
    
    # Extra verification & raw JSON logging columns
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    model_name = Column(String, nullable=True)
    analysis_result = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class PerformanceScore(Base):
    __tablename__ = "performance_scores"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, unique=True)
    
    # 10 performance category scores (0 to 5)
    sales_score = Column(Integer, default=0)
    collection_score = Column(Integer, default=0)
    competition_score = Column(Integer, default=0)
    product_score = Column(Integer, default=0)
    price_list_score = Column(Integer, default=0)
    services_score = Column(Integer, default=0)
    new_products_score = Column(Integer, default=0)
    most_sell_products_score = Column(Integer, default=0)
    pending_stock_score = Column(Integer, default=0)
    follow_up_score = Column(Integer, default=0)
    
    # Explanations stored as a JSON string
    explanations = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

