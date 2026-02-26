"""Book domain schemas for API request/response contracts."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# --- Core CRUD Schemas ---

class BookBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    author: str = Field(..., min_length=2, max_length=100)
    isbn: str = Field(..., pattern=r"^[\d-]{10,17}$")
    total_copies: int = Field(1, ge=1, le=1000)
    available_copies: int = Field(1, ge=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    total_copies: Optional[int] = None
    available_copies: Optional[int] = None


class BookResponse(BookBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Book Detail Schemas ---

class BorrowerInfo(BaseModel):
    """An active borrower of a specific book."""

    borrow_id: UUID
    member_id: UUID
    name: str
    borrowed_at: datetime
    due_date: Optional[datetime] = None
    days_until_due: int

    model_config = ConfigDict(from_attributes=True)


class BorrowHistoryItem(BaseModel):
    """A past borrower entry for a specific book."""

    member_id: UUID
    member_name: str
    borrowed_at: datetime
    returned_at: datetime
    duration_days: int

    model_config = ConfigDict(from_attributes=True)


class BorrowHistoryResponse(BaseModel):
    data: List[BorrowHistoryItem]
    meta: dict


class BookAnalytics(BaseModel):
    """Computed analytics for a single book."""

    total_times_borrowed: int
    average_borrow_duration: float
    last_borrowed_at: Optional[datetime]
    popularity_rank: int
    availability_status: str

    longest_borrow_duration: Optional[int] = None
    shortest_borrow_duration: Optional[int] = None
    return_delay_count: int = 0


class BookDetailResponse(BaseModel):
    """Aggregated book detail with borrowers, history, and analytics."""

    book: BookResponse
    current_borrowers: List[BorrowerInfo]
    borrow_history: BorrowHistoryResponse
    analytics: BookAnalytics
