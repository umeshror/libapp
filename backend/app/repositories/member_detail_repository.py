from datetime import datetime, timezone
from typing import Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, case, and_, text
from uuid import UUID

from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.book import Book


class MemberDetailRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_member_core_stats(self, member_id: UUID) -> dict:
        """
        Fetch active borrow count and basic summary stats.
        """
        # Active borrows count
        active_count = (
            self.db.execute(
                select(func.count())
                .select_from(BorrowRecord)
                .where(
                    and_(
                        BorrowRecord.member_id == member_id,
                        BorrowRecord.status == BorrowStatus.BORROWED,
                    )
                )
            ).scalar()
            or 0
        )

        # Summary analytics
        stats = self.db.execute(
            select(
                func.count(BorrowRecord.id).label("total_borrowed"),
                func.count()
                .filter(
                    and_(
                        BorrowRecord.returned_at > BorrowRecord.due_date,
                        BorrowRecord.returned_at.is_not(None),
                    )
                )
                .label("returned_overdue_count"),
                func.count()
                .filter(
                    and_(
                        BorrowRecord.status == BorrowStatus.BORROWED,
                        BorrowRecord.due_date < datetime.now(timezone.utc),
                    )
                )
                .label("active_overdue_count"),
            ).where(BorrowRecord.member_id == member_id)
        ).first()

        total = stats.total_borrowed if stats is not None else 0
        overdue_total = (
            (stats.returned_overdue_count or 0) + (stats.active_overdue_count or 0)
            if stats is not None
            else 0
        )
        overdue_rate = (overdue_total / total * 100) if total > 0 else 0.0

        return {
            "active_borrows_count": active_count,
            "total_books_borrowed": total,
            "overdue_rate_percent": round(overdue_rate, 2),
        }

    def get_member_borrow_history(
        self,
        member_id: UUID,
        limit: int = 10,
        offset: int = 0,
        status: Optional[str] = "all",
        sort: str = "borrowed_at",
        order: str = "desc",
    ) -> Tuple[Any, int]:
        """
        Fetch paginated borrow history with book details.
        """
        query = (
            select(
                BorrowRecord.book_id,
                Book.title.label("book_title"),
                BorrowRecord.borrowed_at,
                BorrowRecord.returned_at,
                BorrowRecord.due_date,
                func.extract(
                    "day",
                    func.coalesce(BorrowRecord.returned_at, datetime.now(timezone.utc))
                    - BorrowRecord.borrowed_at,
                ).label("duration_days"),
            )
            .join(Book, BorrowRecord.book_id == Book.id)
            .where(BorrowRecord.member_id == member_id)
        )

        if status == "active":
            query = query.where(BorrowRecord.status == BorrowStatus.BORROWED)
        elif status == "returned":
            query = query.where(BorrowRecord.status == BorrowStatus.RETURNED)

        # Total count for pagination
        total_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(total_query).scalar() or 0

        # Sorting
        sort_col = (
            getattr(BorrowRecord, sort)
            if hasattr(BorrowRecord, sort)
            else BorrowRecord.borrowed_at
        )
        if order == "desc":
            query = query.order_by(desc(sort_col))
        else:
            query = query.order_by(sort_col)

        # Pagination
        query = query.limit(limit).offset(offset)
        results = self.db.execute(query).all()

        return results, total

    def get_member_detailed_analytics(self, member_id: UUID) -> dict:
        """
        Fetch deep analytics for a member.
        """
        # Duration and count stats
        stats = self.db.execute(
            select(
                func.count(BorrowRecord.id).label("total_count"),
                func.count()
                .filter(BorrowRecord.status == BorrowStatus.BORROWED)
                .label("active_count"),
                func.avg(
                    func.extract(
                        "day",
                        func.coalesce(
                            BorrowRecord.returned_at, datetime.now(timezone.utc)
                        )
                        - BorrowRecord.borrowed_at,
                    )
                ).label("avg_duration"),
                func.max(
                    func.extract(
                        "day",
                        func.coalesce(
                            BorrowRecord.returned_at, datetime.now(timezone.utc)
                        )
                        - BorrowRecord.borrowed_at,
                    )
                ).label("max_duration"),
                func.min(
                    func.extract(
                        "day",
                        func.coalesce(
                            BorrowRecord.returned_at, datetime.now(timezone.utc)
                        )
                        - BorrowRecord.borrowed_at,
                    )
                ).label("min_duration"),
                func.count()
                .filter(
                    case(
                        (
                            BorrowRecord.returned_at.is_not(None),
                            BorrowRecord.returned_at > BorrowRecord.due_date,
                        ),
                        (
                            BorrowRecord.returned_at.is_(None),
                            BorrowRecord.due_date < datetime.now(timezone.utc),
                        ),
                        else_=False,
                    )
                )
                .label("overdue_count"),
            ).where(BorrowRecord.member_id == member_id)
        ).first()

        # Favorite Author
        fav_author = self.db.execute(
            select(Book.author)
            .join(BorrowRecord, BorrowRecord.book_id == Book.id)
            .where(BorrowRecord.member_id == member_id)
            .group_by(Book.author)
            .order_by(desc(func.count(BorrowRecord.id)))
            .limit(1)
        ).scalar()

        # Activity Trend (last 6 months)
        # We'll use a monthly grouping
        if self.db.bind and self.db.bind.dialect.name == "sqlite":
            month_fmt = func.strftime("%Y-%m", BorrowRecord.borrowed_at).label("month")
        else:
            month_fmt = func.to_char(BorrowRecord.borrowed_at, "YYYY-MM").label("month")

        trend_query = (
            select(month_fmt, func.count(BorrowRecord.id).label("count"))
            .where(BorrowRecord.member_id == member_id)
            .group_by(text("month"))
            .order_by(text("month"))
            .limit(6)
        )

        trends = self.db.execute(trend_query).all()

        # Borrow frequency per month (based on first borrow date)
        first_borrow = self.db.execute(
            select(func.min(BorrowRecord.borrowed_at)).where(
                BorrowRecord.member_id == member_id
            )
        ).scalar()

        freq = 0.0
        if first_borrow:
            if first_borrow.tzinfo is None:
                first_borrow = first_borrow.replace(tzinfo=timezone.utc)
            duration = datetime.now(timezone.utc) - first_borrow
            months = max(1, duration.days / 30)
            freq = stats.total_count / months if stats and stats.total_count else 0.0

        return {
            "total_books_borrowed": stats.total_count if stats is not None else 0,
            "active_books": stats.active_count if stats is not None else 0,
            "average_borrow_duration": round(float(stats.avg_duration or 0), 1)
            if stats is not None
            else 0.0,
            "longest_borrow_duration": int(stats.max_duration or 0)
            if stats is not None and stats.max_duration
            else None,
            "shortest_borrow_duration": int(stats.min_duration or 0)
            if stats is not None and stats.min_duration
            else None,
            "overdue_count": stats.overdue_count if stats is not None else 0,
            "overdue_rate_percent": round(
                (stats.overdue_count / stats.total_count * 100), 1
            )
            if stats is not None and stats.total_count > 0
            else 0.0,
            "favorite_author": fav_author,
            "borrow_frequency_per_month": round(freq, 1),
            "activity_trend": [{"month": t.month, "count": t.count} for t in trends],
        }
