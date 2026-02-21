from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.book import Book
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.member import Member
from app.domains.books.schemas import (
    BookCreate, BookUpdate, BookResponse,
    BorrowerInfo, BorrowHistoryItem, BookAnalytics,
)


class BookRepository:
    """Data access layer for Book entities and their borrow relationships."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, obj_in: BookCreate) -> BookResponse:
        db_obj = Book(
            title=obj_in.title,
            author=obj_in.author,
            isbn=obj_in.isbn,
            total_copies=obj_in.total_copies,
            available_copies=obj_in.available_copies,
        )
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return BookResponse.model_validate(db_obj)

    def get(self, id: UUID) -> Optional[BookResponse]:
        statement = select(Book).where(Book.id == id)
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return BookResponse.model_validate(result)
        return None

    def get_by_isbn(self, isbn: str) -> Optional[BookResponse]:
        statement = select(Book).where(Book.isbn == isbn)
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return BookResponse.model_validate(result)
        return None

    def get_with_lock(self, id: UUID) -> Optional[Book]:
        """
        Fetches a book by ID with a row lock (SELECT FOR UPDATE).
        Returns the ORM object directly as it is intended for transactional updates within a service.
        Constraint: Service must handle the session commit.
        """
        statement = select(Book).where(Book.id == id).with_for_update()
        result = self.session.execute(statement).scalar_one_or_none()
        return result

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        """
        Lists books with filtering, sorting, and pagination.
        Returns a dict with items (ORM objects) and total count.
        """
        # Base query
        stmt = select(Book)

        # Filtering (Search)
        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                (Book.title.ilike(search_term))
                | (Book.author.ilike(search_term))
                | (Book.isbn.ilike(search_term))
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        # Sorting
        sort_column = getattr(Book, sort_field, Book.created_at)

        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Deterministic secondary sort
        stmt = stmt.order_by(Book.id)

        # Pagination
        stmt = stmt.offset(skip).limit(limit)

        results = self.session.execute(stmt).scalars().all()

        return {"items": results, "total": total}

    def update(self, id: UUID, obj_in: BookUpdate) -> Optional[BookResponse]:
        db_obj = self.session.get(Book, id)
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return BookResponse.model_validate(db_obj)

    def get_current_borrowers(self, book_id: UUID) -> List[BorrowerInfo]:
        """
        Get active borrowers (status is BORROWED).
        """
        stmt = (
            select(
                Member.id,
                Member.name,
                BorrowRecord.borrowed_at,
                BorrowRecord.due_date,
                BorrowRecord.id.label("borrow_id"),
            )
            .join(BorrowRecord, Member.id == BorrowRecord.member_id)
            .where(
                BorrowRecord.book_id == book_id,
                BorrowRecord.status == BorrowStatus.BORROWED,
            )
            .order_by(BorrowRecord.due_date.asc())
        )

        results = self.session.execute(stmt).all()

        borrower_infos = []
        for r in results:
            due = r.due_date
            if due:
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                delta = due - datetime.now(timezone.utc)
                days_until = delta.days
            else:
                days_until = 0

            borrower_infos.append(
                BorrowerInfo(
                    borrow_id=r.borrow_id,
                    member_id=r.id,
                    name=r.name,
                    borrowed_at=r.borrowed_at,
                    due_date=r.due_date,
                    days_until_due=days_until,
                )
            )

        return borrower_infos

    def get_borrow_history(
        self, book_id: UUID, limit: int, offset: int
    ) -> Tuple[List[BorrowHistoryItem], int]:
        """
        Get past borrowers (status is RETURNED), paginated.
        Returns (items, total_count).
        """
        base_stmt = (
            select(
                Member.id,
                Member.name,
                BorrowRecord.borrowed_at,
                BorrowRecord.returned_at,
            )
            .join(Member, BorrowRecord.member_id == Member.id)
            .where(
                BorrowRecord.book_id == book_id,
                BorrowRecord.status == BorrowStatus.RETURNED,
                BorrowRecord.returned_at.is_not(None),
            )
        )

        # Count total
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_count = self.session.execute(count_stmt).scalar() or 0

        # Fetch paginated results
        stmt = (
            base_stmt.order_by(BorrowRecord.returned_at.desc())
            .limit(limit)
            .offset(offset)
        )
        results = self.session.execute(stmt).all()

        items = []
        for r in results:
            duration = 0
            if r.returned_at and r.borrowed_at:
                duration = (r.returned_at - r.borrowed_at).days

            items.append(
                BorrowHistoryItem(
                    member_id=r.id,
                    member_name=r.name,
                    borrowed_at=r.borrowed_at,
                    returned_at=r.returned_at,
                    duration_days=duration,
                )
            )

        return items, total_count

