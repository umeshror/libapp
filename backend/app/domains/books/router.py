"""Book domain API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.shared.deps import get_db
from app.shared.schemas import PaginatedResponse
from app.domains.books.service import BookService
from app.domains.books.schemas import (
    BookCreate, BookUpdate, BookResponse, BookDetailResponse,
)
from app.core.security import rate_limit_dependency

router = APIRouter()


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_dependency)])
def create_book(book_in: BookCreate, db: Session = Depends(get_db)):
    service = BookService(db)
    return service.create_book(book_in)


@router.get("/", response_model=PaginatedResponse[BookResponse], dependencies=[Depends(rate_limit_dependency)])
def list_books(
    offset: int = 0,
    limit: int = 20,
    q: Optional[str] = None,
    sort: str = "-created_at",
    cursor: Optional[str] = None,
    db: Session = Depends(get_db),
):
    service = BookService(db)
    try:
        return service.list_books(
            offset=offset, limit=limit, query=q, sort=sort, cursor=cursor
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: UUID, db: Session = Depends(get_db)):
    service = BookService(db)
    book = service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookResponse, dependencies=[Depends(rate_limit_dependency)])
def update_book(book_id: UUID, book_in: BookUpdate, db: Session = Depends(get_db)):
    service = BookService(db)
    book = service.update_book(book_id, book_in)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.get("/{book_id}/details", response_model=BookDetailResponse)
def get_book_details(
    book_id: UUID,
    history_limit: int = 10,
    history_offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get comprehensive book details with borrowers, history, and analytics."""
    service = BookService(db)
    return service.get_book_details(book_id, history_limit, history_offset)
