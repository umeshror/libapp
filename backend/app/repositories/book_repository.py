from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.book import Book
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.member import Member
from app.schemas import BookCreate, BookUpdate, BookResponse
from app.schemas.book_details import BorrowerInfo, BorrowHistoryItem, BookAnalytics


class BookRepository:
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

        # Optimization: Get total count before pagination
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        # Sorting
        # Security: sort_field is validated by Service, but we double check or use getattr safe
        # Default to created_at if field not found
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

    def get_analytics(self, book_id: UUID, book: Book) -> BookAnalytics:
        # 1. Total times borrowed
        total_stmt = select(func.count(BorrowRecord.id)).where(BorrowRecord.book_id == book_id)
        total_borrows = self.session.execute(total_stmt).scalar() or 0

        # 2. Avg duration (only for returned)
        if self.session.bind and self.session.bind.dialect.name == "sqlite":
            diff_expr = (func.julianday(BorrowRecord.returned_at) - func.julianday(BorrowRecord.borrowed_at)) * 86400
        else:
            diff_expr = func.extract("epoch", BorrowRecord.returned_at - BorrowRecord.borrowed_at)

        avg_stmt = select(func.avg(diff_expr)).where(
            BorrowRecord.book_id == book_id, BorrowRecord.returned_at.is_not(None)
        )
        avg_duration = self.session.execute(avg_stmt).scalar()
        avg_days = (float(avg_duration) / 86400.0) if avg_duration is not None else 0.0

        # 3. Last borrowed
        last_stmt = select(func.max(BorrowRecord.borrowed_at)).where(BorrowRecord.book_id == book_id)
        last_borrowed = self.session.execute(last_stmt).scalar()
        if isinstance(last_borrowed, str):
            from dateutil.parser import parse
            last_borrowed = parse(last_borrowed)

        # 4. Popularity Rank
        subq = (
            select(
                BorrowRecord.book_id, func.count(BorrowRecord.id).label("cnt")
            )
            .group_by(BorrowRecord.book_id)
            .subquery()
        )
        rank_stmt = (
            select(func.count())
            .select_from(subq)
            .where(subq.c.cnt > total_borrows)
        )
        rank = (self.session.execute(rank_stmt).scalar() or 0) + 1

        # 5. Availability Status
        if book.available_copies == 0:
            status = "OUT_OF_STOCK"
        elif book.available_copies <= 1:
            status = "LOW_STOCK"
        else:
            status = "AVAILABLE"

        # Insights
        if self.session.bind and self.session.bind.dialect.name == "sqlite":
            bounds_stmt = (
                select(
                    func.min(func.julianday(BorrowRecord.returned_at) - func.julianday(BorrowRecord.borrowed_at)),
                    func.max(func.julianday(BorrowRecord.returned_at) - func.julianday(BorrowRecord.borrowed_at)),
                )
                .where(
                    BorrowRecord.book_id == book_id, BorrowRecord.returned_at.is_not(None)
                )
            )
            bounds = self.session.execute(bounds_stmt).first()
            min_dur = int(bounds[0]) if bounds and bounds[0] is not None else 0
            max_dur = int(bounds[1]) if bounds and bounds[1] is not None else 0
        else:
            bounds_stmt = (
                select(
                    func.min(BorrowRecord.returned_at - BorrowRecord.borrowed_at),
                    func.max(BorrowRecord.returned_at - BorrowRecord.borrowed_at),
                )
                .where(
                    BorrowRecord.book_id == book_id, BorrowRecord.returned_at.is_not(None)
                )
            )
            bounds = self.session.execute(bounds_stmt).first()
            min_dur = bounds[0].days if bounds and bounds[0] is not None else 0
            max_dur = bounds[1].days if bounds and bounds[1] is not None else 0

        # Return delays (returned > due_date)
        delays_stmt = (
            select(func.count(BorrowRecord.id))
            .where(
                BorrowRecord.book_id == book_id,
                BorrowRecord.returned_at > BorrowRecord.due_date,
            )
        )
        delays = self.session.execute(delays_stmt).scalar() or 0

        return BookAnalytics(
            total_times_borrowed=total_borrows,
            average_borrow_duration=round(avg_days, 1),
            last_borrowed_at=last_borrowed,
            popularity_rank=rank,
            availability_status=status,
            longest_borrow_duration=max_dur,
            shortest_borrow_duration=min_dur,
            return_delay_count=delays,
        )
