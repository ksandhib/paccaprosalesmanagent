from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class SalesSchema(BaseModel):
    item_name: str
    quantity: int
    amount: float
    payment_status: str

    class Config:
        from_attributes = True

class CollectionSchema(BaseModel):
    amount_collected: float
    payment_method: Optional[str] = None
    reference_no: Optional[str] = None

    class Config:
        from_attributes = True

class ComplaintSchema(BaseModel):
    description: str
    severity: str
    status: str

    class Config:
        from_attributes = True

class ProductRequestSchema(BaseModel):
    product_name: str
    details: Optional[str] = None

    class Config:
        from_attributes = True

class CompetitorSchema(BaseModel):
    competitor_name: str
    activity_details: Optional[str] = None

    class Config:
        from_attributes = True

class ConversationSchema(BaseModel):
    speaker: str
    text: str
    timestamp: Optional[float] = None

    class Config:
        from_attributes = True

class ReportSummarySchema(BaseModel):
    id: int
    representative: str
    client_name: str
    date: str
    summary: Optional[str] = None
    sentiment: str
    priority: str
    voice_duration: float
    file_path: Optional[str] = None
    follow_up_date: Optional[str] = None
    sales_raw: Optional[str] = None
    collection_raw: Optional[str] = None
    competition_raw: Optional[str] = None
    product_raw: Optional[str] = None
    price_list_raw: Optional[str] = None
    our_services_raw: Optional[str] = None
    our_new_products_raw: Optional[str] = None
    most_sell_products_raw: Optional[str] = None
    pending_stock_raw: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ReportDetailSchema(ReportSummarySchema):
    sales_details: List[SalesSchema] = []
    collection_details: List[CollectionSchema] = []
    complaints: List[ComplaintSchema] = []
    product_requests: List[ProductRequestSchema] = []
    competitor_activities: List[CompetitorSchema] = []
    conversations: List[ConversationSchema] = []

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str
    response: str
    timestamp: datetime


class PosterAnalysisEditSchema(BaseModel):
    poster_title: Optional[str] = None
    poster_category: Optional[str] = None
    main_heading: Optional[str] = None
    sub_heading: Optional[str] = None
