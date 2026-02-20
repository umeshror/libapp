from datetime import datetime, timedelta, timezone
import uuid
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.book_repository import BookRepository
from app.repositories.borrow_repository import BorrowRepository
from app.repositories.member_repository import MemberRepository
from app.schemas import BorrowRecordResponse, PaginatedResponse, PaginationMeta
from app.models.borrow_record import BorrowStatus
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


class BorrowService:
    def __init__(self, session: Session):
        self.session = session
        self.book_repo = BookRepository(session)
        self.member_repo = MemberRepository(session)
        self.borrow_repo = BorrowRepository(session)

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
        Enforces:
        - Max 5 active borrows per member
        - Available copies > 0
        - Atomic update of inventory and creation of borrow record

        Args:
            borrowed_at: Optional override for seeding/migration. Defaults to now.
            due_date: Optional override for seeding/migration. Defaults to now + 14 days.
        """
        # Check active borrows limit
        # We need to count active borrows for this member.
        # Using list with status=BORROWED.
        # Since we just need count, we could optimize but list returns 'total' which is count.
        active_borrows_result = self.borrow_repo.list(
            member_id=member_id,
            status=BorrowStatus.BORROWED,
            limit=1,  # We just need the total count from metadata
        )
        from app.core.config import settings

        active_count = active_borrows_result["total"]

        if active_count >= settings.MAX_ACTIVE_BORROWS:
            raise BorrowLimitExceededError(
                f"Member has reached the maximum limit of {settings.MAX_ACTIVE_BORROWS} active borrows."
            )

        # Check if member exists
        member = self.member_repo.get(member_id)
        if not member:
            raise MemberNotFoundError("Member not found.")

        # Check for existing active borrow of the same book
        existing_borrow = self.borrow_repo.get_active_borrow(book_id, member_id)
        if existing_borrow:
            raise ActiveBorrowExistsError(
                "Member already has an active borrow for this book."
            )

        # Transactional block
        # Lock the book row
        book = self.book_repo.get_with_lock(book_id)
        if not book:
            raise BookNotFoundError("Book not found.")

        if book.available_copies < 1:
            raise InventoryUnavailableError("No copies available for borrowing.")

        # Decrement copies
        book.available_copies -= 1  # type: ignore

        # Create borrow record
        from app.models.borrow_record import BorrowRecord

        if not borrowed_at:
            borrowed_at = datetime.now(timezone.utc)

        from app.core.config import settings

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
        self.session.add(borrow_record)
        self.session.flush()

        # Create response before commit to avoid DetachedInstanceError or refresh issues
        response = BorrowRecordResponse.model_validate(borrow_record)

        self.session.commit()
        return response

    @measure_borrow_metrics
    @db_retry(max_retries=3)
    def return_book(
        self, borrow_id: UUID, returned_at: Optional[datetime] = None
    ) -> BorrowRecordResponse:
        """
        Returns a borrowed book.
        Enforces:
        - Updates status to RETURNED
        - Atomically increments available_copies

        Args:
            returned_at: Optional override for seeding/migration. Defaults to now.
        """
        # Lock the borrow record
        borrow_record = self.borrow_repo.get_by_id_with_lock(borrow_id)
        if not borrow_record:
            raise BorrowRecordNotFoundError("Borrow record not found.")

        if borrow_record.status != BorrowStatus.BORROWED:
            raise AlreadyReturnedError("Book is already returned.")

        # Update status
        borrow_record.status = BorrowStatus.RETURNED  # type: ignore
        borrow_record.returned_at = returned_at or datetime.now(timezone.utc)  # type: ignore

        # Lock and update book
        book = self.book_repo.get_with_lock(borrow_record.book_id)  # type: ignore
        if not book:
            # Should not happen via FK constraint but good to check
            raise BookNotFoundError(
                "Book associated with this borrow record not found."
            )

        book.available_copies += 1  # type: ignore

        self.session.flush()
        response = BorrowRecordResponse.model_validate(borrow_record)

        self.session.commit()
        return response

    def list_borrows(
        self,
        offset: int = 0,
        limit: int = 20,
        member_id: Optional[UUID] = None,
        overdue: bool = False,
        query: Optional[str] = None,
        sort: str = "-borrowed_at",
    ) -> PaginatedResponse[BorrowRecordResponse]:
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

        result = self.borrow_repo.list(
            skip=offset,
            limit=limit,
            member_id=member_id,
            overdue=overdue,
            query=query,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        items = result["items"]
        total = result["total"]

        return PaginatedResponse(
            data=[BorrowRecordResponse.model_validate(r) for r in items],
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + limit) < total,
            ),
        )
