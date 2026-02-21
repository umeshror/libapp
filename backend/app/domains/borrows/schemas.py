"""Borrow domain schemas for API request/response contracts."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.domains.books.schemas import BookResponse
from app.domains.members.schemas import MemberResponse


# --- Core CRUD Schemas ---

class BorrowRecordBase(BaseModel):
    book_id: UUID
    member_id: UUID


class BorrowRecordCreate(BorrowRecordBase):
    pass


class BorrowRecordResponse(BorrowRecordBase):
    """API response for a borrow record with optional nested book/member."""

    id: UUID
    borrowed_at: datetime
    due_date: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    status: str
    book: Optional[BookResponse] = None
    member: Optional[MemberResponse] = None

    model_config = ConfigDict(from_attributes=True)


# --- Request Schemas ---

class BorrowRequest(BaseModel):
    """Request body for borrowing a book."""

    book_id: UUID
    member_id: UUID
