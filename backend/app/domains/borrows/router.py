"""Borrow domain API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Optional
from uuid import UUID
from app.shared.deps import get_uow
from app.shared.uow import UnitOfWork
from app.shared.schemas import PaginatedResponse
from app.domains.borrows.service import BorrowService
from app.domains.borrows.schemas import BorrowRequest, BorrowRecordResponse
from app.core.security import rate_limit_dependency

router = APIRouter()


@router.post("/", response_model=BorrowRecordResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_dependency)])
def create_borrow(
    borrow_in: BorrowRequest, 
    background_tasks: BackgroundTasks,
    uow: UnitOfWork = Depends(get_uow)
):
    """Borrow a book for a member."""
    service = BorrowService(uow, background_tasks)
    return service.borrow_book(borrow_in.book_id, borrow_in.member_id)


@router.get("/", response_model=PaginatedResponse[BorrowRecordResponse], dependencies=[Depends(rate_limit_dependency)])
def list_borrows(
    offset: int = 0,
    limit: int = 20,
    q: Optional[str] = None,
    sort: str = "-borrowed_at",
    cursor: Optional[str] = None,
    uow: UnitOfWork = Depends(get_uow),
):
    """List all borrow records (active and returned)."""
    service = BorrowService(uow)
    try:
        return service.list_borrows(
            offset=offset, limit=limit, query=q, sort=sort, cursor=cursor
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{borrow_id}/return/", response_model=BorrowRecordResponse, dependencies=[Depends(rate_limit_dependency)])
def return_borrow(
    borrow_id: UUID, 
    background_tasks: BackgroundTasks,
    uow: UnitOfWork = Depends(get_uow)
):
    """Return a borrowed book."""
    service = BorrowService(uow, background_tasks)
    return service.return_book(borrow_id)


@router.get("/overdue/", response_model=PaginatedResponse[BorrowRecordResponse], dependencies=[Depends(rate_limit_dependency)])
def list_overdue_borrows(
    offset: int = 0,
    limit: int = 20,
    sort: str = "-due_date",
    cursor: Optional[str] = None,
    uow: UnitOfWork = Depends(get_uow),
):
    """List all overdue borrows."""
    service = BorrowService(uow)
    try:
        return service.list_borrows(
            overdue=True, offset=offset, limit=limit, sort=sort, cursor=cursor
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
