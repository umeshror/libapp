from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID

from app.models.book import Book
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.member import Member
from app.schemas.book_details import BorrowerInfo, BorrowHistoryItem, BookAnalytics


class BookDetailRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_book(self, book_id: UUID) -> Optional[Book]:
        return self.session.query(Book).filter(Book.id == book_id).first()

    def get_current_borrowers(self, book_id: UUID) -> List[BorrowerInfo]:
        """
        Get active borrowers (returned_at IS NULL).
        """
        query = (
            self.session.query(
                Member.id,
                Member.name,
                BorrowRecord.borrowed_at,
                BorrowRecord.due_date,
                BorrowRecord.id.label("borrow_id"),
            )
            .join(BorrowRecord, Member.id == BorrowRecord.member_id)
            .filter(
                BorrowRecord.book_id == book_id,
                BorrowRecord.status == BorrowStatus.BORROWED,
            )
            .order_by(BorrowRecord.due_date.asc())
        )

        results = query.all()

        borrower_infos = []
        # Ideally handle timezone. Assuming naive UTC in DB for simplicity or consistent usage.

        for r in results:
            # Consistent aware datetime usage
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
        Get past borrowers (returned_at IS NOT NULL), paginated.
        Returns (items, total_count).
        """
        base_query = (
            self.session.query(
                Member.id,
                Member.name,
                BorrowRecord.borrowed_at,
                BorrowRecord.returned_at,
            )
            .join(Member, BorrowRecord.member_id == Member.id)
            .filter(
                BorrowRecord.book_id == book_id,
                BorrowRecord.status == BorrowStatus.RETURNED,
                BorrowRecord.returned_at.isnot(None),
            )
        )

        total_count = base_query.count()

        results = (
            base_query.order_by(BorrowRecord.returned_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

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
        total_borrows = (
            self.session.query(func.count(BorrowRecord.id))
            .filter(BorrowRecord.book_id == book_id)
            .scalar()
            or 0
        )

        # 2. Avg duration (only for returned)
        avg_duration = (
            self.session.query(
                func.avg(
                    func.extract(
                        "epoch", BorrowRecord.returned_at - BorrowRecord.borrowed_at
                    )
                )
            )
            .filter(
                BorrowRecord.book_id == book_id, BorrowRecord.returned_at.isnot(None)
            )
            .scalar()
        )

        # Convert seconds to days (handle Decimal from extract)
        avg_days = (float(avg_duration) / 86400.0) if avg_duration is not None else 0.0

        # 3. Last borrowed
        last_borrowed = (
            self.session.query(func.max(BorrowRecord.borrowed_at))
            .filter(BorrowRecord.book_id == book_id)
            .scalar()
        )

        # 4. Popularity Rank
        # Rank based on total borrows compared to all books
        # Optimized: Count borrows per book, then rank current book.
        # This can be heavy. A simpler approach for MVP:
        # Count how many books have MORE borrows than this one + 1.

        # Subquery for borrow counts
        # This is strictly per requirements but beware of performance on million rows.
        # Ideally materialized view.
        # For now, let's just use a count comparison? Or maybe just get top 100?
        # The prompt asks for "Popularity rank".
        # Let's try a window function query (filtered) or just a simple count > logic.

        subq = (
            self.session.query(
                BorrowRecord.book_id, func.count(BorrowRecord.id).label("cnt")
            )
            .group_by(BorrowRecord.book_id)
            .subquery()
        )

        # My count
        my_count = total_borrows

        # Rank = count of books with cnt > my_count + 1
        rank = (
            self.session.query(func.count())
            .select_from(subq)
            .filter(subq.c.cnt > my_count)
            .scalar()
            + 1
        )

        # 5. Availability Status
        if book.available_copies == 0:
            status = "OUT_OF_STOCK"
        elif book.available_copies <= 1:
            status = "LOW_STOCK"  # Requirements say <= 1 is LOW_STOCK, but if 0 is out... let's match logic.
            # "LOW_STOCK (available_copies <= 1)" - implies 0 or 1.
            # But "OUT_OF_STOCK" implies 0.
            # So: 0 -> Out, 1 -> Low, >1 -> Available.
        else:
            status = "AVAILABLE"

        # Insights
        # Min/Max duration
        bounds = (
            self.session.query(
                func.min(BorrowRecord.returned_at - BorrowRecord.borrowed_at),
                func.max(BorrowRecord.returned_at - BorrowRecord.borrowed_at),
            )
            .filter(
                BorrowRecord.book_id == book_id, BorrowRecord.returned_at.isnot(None)
            )
            .first()
        )

        min_dur = bounds[0].days if bounds and bounds[0] is not None else 0
        max_dur = bounds[1].days if bounds and bounds[1] is not None else 0

        # Return delays (returned > due_date)
        delays = (
            self.session.query(func.count(BorrowRecord.id))
            .filter(
                BorrowRecord.book_id == book_id,
                BorrowRecord.returned_at > BorrowRecord.due_date,
            )
            .scalar()
            or 0
        )

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
