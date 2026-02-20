from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional
from .pagination import PaginatedResponse, PaginationMeta

__all__ = ["PaginatedResponse", "PaginationMeta"]


class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    total_copies: int = 1
    available_copies: int = 1


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


class BorrowRecordBase(BaseModel):
    book_id: UUID
    member_id: UUID


class BorrowRecordCreate(BorrowRecordBase):
    pass


class BorrowRecordResponse(BorrowRecordBase):
    id: UUID
    borrowed_at: datetime
    due_date: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    status: str
    book: Optional[BookResponse] = None
    member: Optional[MemberResponse] = None

    model_config = ConfigDict(from_attributes=True)
