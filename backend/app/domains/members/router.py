"""Member domain API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.shared.deps import get_db
from app.shared.schemas import PaginatedResponse
from app.domains.members.service import MemberService
from app.domains.members.schemas import (
    MemberCreate,
    MemberResponse,
    MemberCoreDetails,
    MemberBorrowHistoryResponse,
    MemberAnalyticsResponse,
)

router = APIRouter()


@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(member_in: MemberCreate, db: Session = Depends(get_db)):
    service = MemberService(db)
    return service.create_member(member_in)


@router.get("/", response_model=PaginatedResponse[MemberResponse])
def list_members(
    offset: int = 0,
    limit: int = 20,
    q: Optional[str] = None,
    sort: str = "-created_at",
    db: Session = Depends(get_db),
):
    service = MemberService(db)
    try:
        return service.list_members(offset=offset, limit=limit, query=q, sort=sort)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{member_id}", response_model=MemberCoreDetails)
def get_member(member_id: UUID, db: Session = Depends(get_db)):
    """Get core member details including stats and analytics summary."""
    service = MemberService(db)
    return service.get_member_details(member_id)


@router.get("/{member_id}/stats", response_model=MemberCoreDetails)
def get_member_stats(member_id: UUID, db: Session = Depends(get_db)):
    """Get core member stats (active borrows, overdue rate, etc.)."""
    service = MemberService(db)
    return service.get_member_details(member_id)


@router.get("/{member_id}/history", response_model=MemberBorrowHistoryResponse)
def get_member_borrow_history(
    member_id: UUID,
    limit: int = 10,
    offset: int = 0,
    status: str = "all",
    sort: str = "borrowed_at",
    order: str = "desc",
    db: Session = Depends(get_db),
):
    """Get paginated borrow history for a member."""
    service = MemberService(db)
    return service.get_member_borrow_history(member_id, limit, offset, status, sort, order)


@router.get("/{member_id}/analytics", response_model=MemberAnalyticsResponse)
def get_member_analytics(member_id: UUID, db: Session = Depends(get_db)):
    """Get deep analytics and behavioral insights for a member."""
    service = MemberService(db)
    return service.get_member_analytics(member_id)


# --- Member-scoped borrow operations ---

from app.domains.borrows.service import BorrowService
from app.domains.borrows.schemas import BorrowRecordResponse


@router.post(
    "/{member_id}/borrows/",
    response_model=BorrowRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def borrow_book_for_member(
    member_id: UUID, book_id: UUID, db: Session = Depends(get_db)
):
    """Borrow a book for a specific member (member-scoped)."""
    service = BorrowService(db)
    return service.borrow_book(book_id, member_id)


@router.get(
    "/{member_id}/borrows/",
    response_model=PaginatedResponse[BorrowRecordResponse],
)
def list_borrows_by_member(
    member_id: UUID,
    offset: int = 0,
    limit: int = 20,
    sort: str = "-borrowed_at",
    db: Session = Depends(get_db),
):
    """List borrow history for a specific member."""
    service = BorrowService(db)
    try:
        return service.list_borrows(
            member_id=member_id, offset=offset, limit=limit, sort=sort
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
