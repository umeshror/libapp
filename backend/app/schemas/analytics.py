from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import date


class AnalyticsOverview(BaseModel):
    total_books: int
    active_borrows: int
    overdue_borrows: int
    utilization_rate: float


class OverdueBreakdown(BaseModel):
    days_1_3: int = 0
    days_4_7: int = 0
    days_7_plus: int = 0


class TopMember(BaseModel):
    member_id: str
    name: str
    borrow_count: int


class InventoryHealth(BaseModel):
    low_stock_books: int
    never_borrowed_books: int
    fully_unavailable_books: int


class DailyActiveMember(BaseModel):
    date: date
    count: int


class DailyBorrowCount(BaseModel):
    date: date
    count: int


class BorrowForecast(BaseModel):
    projected_next_7_days_total: int
    daily_projection: int


class AnalyticsSummaryResponse(BaseModel):
    overview: AnalyticsOverview
    overdue_breakdown: OverdueBreakdown
    top_members: List[TopMember]
    inventory_health: InventoryHealth
    daily_active_members: List[DailyActiveMember]
    daily_borrows: List[DailyBorrowCount]
    forecast: BorrowForecast
    generated_at: str

    model_config = ConfigDict(from_attributes=True)
