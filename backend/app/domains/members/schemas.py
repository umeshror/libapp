"""Member domain schemas for API request/response contracts."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# --- Core CRUD Schemas ---

class MemberBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class MemberCreate(MemberBase):
    pass


class MemberResponse(MemberBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Member Detail Schemas ---

class MembershipAnalyticsSummary(BaseModel):
    total_books_borrowed: int
    overdue_rate_percent: float
    risk_level: str


class MemberCoreDetails(BaseModel):
    """Member profile with membership stats and risk assessment."""

    member: MemberResponse
    membership_duration_days: int
    active_borrows_count: int
    analytics_summary: MembershipAnalyticsSummary


class MemberBorrowHistoryItem(BaseModel):
    id: UUID
    book_id: UUID
    book_title: str
    borrowed_at: datetime
    due_date: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    duration_days: Optional[int] = None
    was_overdue: bool


class MemberBorrowHistoryResponse(BaseModel):
    data: List[MemberBorrowHistoryItem]
    meta: dict


class ActivityTrendItem(BaseModel):
    month: str
    count: int


class MemberAnalyticsResponse(BaseModel):
    """Deep behavioral analytics for a member."""

    total_books_borrowed: int
    active_books: int
    average_borrow_duration: float
    longest_borrow_duration: Optional[int]
    shortest_borrow_duration: Optional[int]
    overdue_count: int
    overdue_rate_percent: float
    favorite_author: Optional[str]
    borrow_frequency_per_month: float
    risk_level: str
    activity_trend: List[ActivityTrendItem]
