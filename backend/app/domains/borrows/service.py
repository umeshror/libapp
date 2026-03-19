"""Borrow domain service — handles borrow/return lifecycle with inventory locking."""

from datetime import datetime, timedelta, timezone
import uuid
from uuid import UUID
from typing import Optional
from fastapi import BackgroundTasks
from app.shared.uow import AbstractUnitOfWork
from app.domains.borrows.schemas import BorrowRecordResponse
from app.shared.schemas import PaginatedResponse, PaginationMeta
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.core.config import settings
from app.core.exceptions import (
    InventoryUnavailableError,
    BorrowLimitExceededError,
    AlreadyReturnedError,
    MemberNotFoundError,
    BookNotFoundError,
    BorrowRecordNotFoundError,
    ActiveBorrowExistsError,
)
from app.core.decorators import db_retry, measure_borrow_metrics
from app.shared.audit import log_audit_event


class BorrowService:
    """Handles borrow/return lifecycle with explicit Unit of Work management."""

    def __init__(self, uow: AbstractUnitOfWork, background_tasks: Optional[BackgroundTasks] = None):
        self.uow = uow
        self.background_tasks = background_tasks

    @measure_borrow_metrics
    @db_retry(max_retries=3)
    def borrow_book(
        self,
        book_id: UUID,
        member_id: UUID,
        borrowed_at: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
    ) -> BorrowRecordResponse:
        """
        Borrows a book for a member.
        - Enforces business rules within a session transaction.
        - Uses pessimistic locking for inventory integrity.
        - Offloads auditing to background tasks.
        """
        with self.uow:
            active_borrows_result = self.uow.borrows.list(
                member_id=member_id,
                status=BorrowStatus.BORROWED,
                limit=1,
            )
            active_count = active_borrows_result["total"]

            if active_count >= settings.MAX_ACTIVE_BORROWS:
                raise BorrowLimitExceededError(
                    f"Member has reached the maximum limit of {settings.MAX_ACTIVE_BORROWS} active borrows."
                )

            member = self.uow.members.get(member_id)
            if not member:
                raise MemberNotFoundError("Member not found.")

            existing_borrow = self.uow.borrows.get_active_borrow(book_id, member_id)
            if existing_borrow:
                raise ActiveBorrowExistsError(
                    "Member already has an active borrow for this book."
                )

            book = self.uow.books.get_with_lock(book_id)
            if not book:
                raise BookNotFoundError("Book not found.")

            if book.available_copies < 1:
                raise InventoryUnavailableError("No copies available for borrowing.")

            book.available_copies -= 1  # type: ignore

            if not borrowed_at:
                borrowed_at = datetime.now(timezone.utc)

            if not due_date:
                due_date = borrowed_at + timedelta(
                    days=settings.DEFAULT_BORROW_DURATION_DAYS
                )

            borrow_record = BorrowRecord(
                id=uuid.uuid4(),
                book_id=book_id,
                member_id=member_id,
                borrowed_at=borrowed_at,
                due_date=due_date,
                status=BorrowStatus.BORROWED,
            )
            self.uow.session.add(borrow_record)
            self.uow.commit()
            self.uow.refresh(borrow_record)
            
            if self.background_tasks:
                self.background_tasks.add_task(
                    log_audit_event,
                    self.uow.session,
                    "BORROW_CREATE",
                    str(borrow_record.id),
                    f"Member {member_id} borrowed book {book_id}"
                )
            return BorrowRecordResponse.model_validate(borrow_record)

    @measure_borrow_metrics
    @db_retry(max_retries=3)
    def return_book(
        self, borrow_id: UUID, returned_at: Optional[datetime] = None
    ) -> BorrowRecordResponse:
        """Returns a borrowed book."""
        with self.uow:
            borrow_record = self.uow.borrows.get_by_id_with_lock(borrow_id)
            if not borrow_record:
                raise BorrowRecordNotFoundError("Borrow record not found.")

            if borrow_record.status != BorrowStatus.BORROWED:
                raise AlreadyReturnedError("Book is already returned.")

            borrow_record.status = BorrowStatus.RETURNED  # type: ignore
            borrow_record.returned_at = returned_at or datetime.now(timezone.utc)  # type: ignore

            book = self.uow.books.get_with_lock(borrow_record.book_id)  # type: ignore
            if not book:
                raise BookNotFoundError(
                    "Book associated with this borrow record not found."
                )

            book.available_copies += 1  # type: ignore
            self.uow.commit()
            self.uow.refresh(borrow_record)
            
            if self.background_tasks:
                self.background_tasks.add_task(
                    log_audit_event,
                    self.uow.session,
                    "BORROW_RETURN",
                    str(borrow_id),
                    f"Borrow {borrow_id} returned"
                )
            return BorrowRecordResponse.model_validate(borrow_record)

    def list_borrows(
        self,
        offset: int = 0,
        limit: int = 20,
        member_id: Optional[UUID] = None,
        overdue: bool = False,
        query: Optional[str] = None,
        sort: str = "-borrowed_at",
        cursor: Optional[str] = None,
    ) -> PaginatedResponse[BorrowRecordResponse]:
        """List borrows using UoW."""
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        sort_field = sort
        sort_order = "asc"
        if sort.startswith("-"):
            sort_field = sort[1:]
            sort_order = "desc"

        allowed = ["borrowed_at", "due_date", "status", "returned_at"]
        if sort_field not in allowed:
            raise ValueError(f"Invalid sort field: {sort_field}. Allowed: {allowed}")

        with self.uow:
            result = self.uow.borrows.list(
                skip=offset,
                limit=limit,
                member_id=member_id,
                overdue=overdue,
                query=query,
                sort_field=sort_field,
                sort_order=sort_order,
                cursor=cursor,
            )

        items = result["items"]
        total = result["total"]
        next_cursor = result.get("next_cursor")

        return PaginatedResponse(
            data=[BorrowRecordResponse.model_validate(r) for r in items],
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=next_cursor is not None if cursor else (offset + limit) < total,
                next_cursor=next_cursor,
            ),
        )
