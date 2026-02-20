from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.schemas import BookResponse


class BorrowerInfo(BaseModel):
    borrow_id: UUID
    member_id: UUID
    name: str
    borrowed_at: datetime
    due_date: Optional[datetime] = None
    days_until_due: int

    model_config = ConfigDict(from_attributes=True)


class BorrowHistoryItem(BaseModel):
    member_id: UUID
    member_name: str
    borrowed_at: datetime
    returned_at: datetime
    duration_days: int

    model_config = ConfigDict(from_attributes=True)


class BorrowHistoryResponse(BaseModel):
    data: List[BorrowHistoryItem]
    meta: dict  # total, limit, offset, has_more


class BookAnalytics(BaseModel):
    total_times_borrowed: int
    average_borrow_duration: float  # days
    last_borrowed_at: Optional[datetime]
    popularity_rank: int
    availability_status: str  # AVAILABLE, LOW_STOCK, OUT_OF_STOCK

    # Insights
    longest_borrow_duration: Optional[int] = None
    shortest_borrow_duration: Optional[int] = None
    return_delay_count: int = 0


class BookDetailResponse(BaseModel):
    book: BookResponse
    current_borrowers: List[BorrowerInfo]
    borrow_history: BorrowHistoryResponse
    analytics: BookAnalytics
