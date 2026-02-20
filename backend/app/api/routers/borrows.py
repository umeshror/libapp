from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.api.deps import get_db
from app.services.borrow_service import BorrowService
from app.schemas import BorrowRecordResponse, PaginatedResponse

router = APIRouter()


class BorrowRequest(BaseModel):
    book_id: UUID
    member_id: UUID


@router.post(
    "/borrows/",
    response_model=BorrowRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_borrow(borrow_in: BorrowRequest, db: Session = Depends(get_db)):
    """
    Borrow a book for a member.
    """
    service = BorrowService(db)
    return service.borrow_book(borrow_in.book_id, borrow_in.member_id)


@router.get("/borrows/", response_model=PaginatedResponse[BorrowRecordResponse])
def list_borrows(
    offset: int = 0,
    limit: int = 20,
    q: Optional[str] = None,
    sort: str = "-borrowed_at",
    db: Session = Depends(get_db),
):
    """
    List all borrow records (active and returned).
    """
    service = BorrowService(db)
    try:
        return service.list_borrows(offset=offset, limit=limit, query=q, sort=sort)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/members/{member_id}/borrows/",
    response_model=BorrowRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def borrow_book_deprecated(
    member_id: UUID, book_id: UUID, db: Session = Depends(get_db)
):
    """
    Borrow a book for a member (Deprecated: Use POST /borrows).
    """
    service = BorrowService(db)
    return service.borrow_book(book_id, member_id)


@router.post("/borrows/{borrow_id}/return/", response_model=BorrowRecordResponse)
def return_borrow(borrow_id: UUID, db: Session = Depends(get_db)):
    """
    Return a borrowed book.
    """
    service = BorrowService(db)
    return service.return_book(borrow_id)


@router.get(
    "/members/{member_id}/borrows/",
    response_model=PaginatedResponse[BorrowRecordResponse],
)
def list_borrows_by_member(
    member_id: UUID,
    offset: int = 0,
    limit: int = 20,
    sort: str = "-borrowed_at",
    db: Session = Depends(get_db),
):
    """
    List history of borrows for a member.
    """
    service = BorrowService(db)
    try:
        return service.list_borrows(
            member_id=member_id, offset=offset, limit=limit, sort=sort
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/borrows/overdue/", response_model=PaginatedResponse[BorrowRecordResponse])
def list_overdue_borrows(
    offset: int = 0,
    limit: int = 20,
    sort: str = "-due_date",
    db: Session = Depends(get_db),
):
    """
    List all overdue borrows.
    """
    service = BorrowService(db)
    try:
        return service.list_borrows(overdue=True, offset=offset, limit=limit, sort=sort)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
