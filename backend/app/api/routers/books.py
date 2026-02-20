from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.api.deps import get_db
from app.services.book_service import BookService
from app.schemas import BookCreate, BookUpdate, BookResponse, PaginatedResponse
from app.schemas.book_details import BookDetailResponse
from typing import Optional

router = APIRouter()


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(book_in: BookCreate, db: Session = Depends(get_db)):
    service = BookService(db)
    return service.create_book(book_in)


@router.get("/", response_model=PaginatedResponse[BookResponse])
def list_books(
    offset: int = 0,
    limit: int = 20,
    q: Optional[str] = None,
    sort: str = "-created_at",
    db: Session = Depends(get_db),
):
    service = BookService(db)
    try:
        return service.list_books(offset=offset, limit=limit, query=q, sort=sort)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: UUID, db: Session = Depends(get_db)):
    service = BookService(db)
    book = service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookResponse)
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
    """
    Get comprehensive book details including:
    - Core metadata
    - Current active borrowers
    - Paginated borrow history
    - Analytics and insights
    """
    service = BookService(db)
    return service.get_book_details(book_id, history_limit, history_offset)
