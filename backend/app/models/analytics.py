# FILE: backend/app/models/analytics.py
from pydantic import BaseModel
from typing import List, Optional

class SalesTrendPoint(BaseModel):
    date: str
    amount: float
    count: int

class TopProductItem(BaseModel):
    product_name: str
    total_revenue: float
    total_quantity: float

class AnalyticsDashboardData(BaseModel):
    sales_trend: List[SalesTrendPoint]
    top_products: List[TopProductItem]
    total_revenue_period: float
    total_transactions_period: int