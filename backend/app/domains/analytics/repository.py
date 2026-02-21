from datetime import date, datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, desc, cast, Date, select, text
from app.models.book import Book
from app.models.member import Member
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.domains.analytics.schemas import (
    AnalyticsOverview,
    OverdueBreakdown,
    TopMember,
    InventoryHealth,
    DailyActiveMember,
    PopularBook,
    RecentActivity,
)
from app.domains.books.schemas import BookAnalytics
from app.domains.members.schemas import MemberAnalyticsResponse, ActivityTrendItem


class AnalyticsRepository:
    """Aggregation layer for dashboard, book, and member analytics using PostgreSQL."""

    def __init__(self, session: Session):
        self.session = session

    def get_overview_stats(self, start_date: date, end_date: date) -> AnalyticsOverview:
        now = datetime.now(timezone.utc)

        # Consolidate stats from both tables in 2 round-trips
        book_stats = self.session.execute(
            select(
                func.count(Book.id).label("total_books"),
                func.sum(Book.total_copies).label("total_capacity")
            )
        ).first()

        borrow_stats = self.session.execute(
            select(
                func.count(BorrowRecord.id).filter(BorrowRecord.status == BorrowStatus.BORROWED).label("active"),
                func.count(BorrowRecord.id).filter(
                    and_(BorrowRecord.status == BorrowStatus.BORROWED, BorrowRecord.due_date < now)
                ).label("overdue")
            )
        ).first()

        total_books = book_stats.total_books or 0
        total_capacity = book_stats.total_capacity or 0
        active_borrows = borrow_stats.active or 0
        overdue_borrows = borrow_stats.overdue or 0

        utilization_rate = 0.0
        if total_capacity > 0:
            utilization_rate = (active_borrows / total_capacity) * 100.0

        return AnalyticsOverview(
            total_books=total_books,
            active_borrows=active_borrows,
            overdue_borrows=overdue_borrows,
            utilization_rate=round(utilization_rate, 2),
        )

    def get_overdue_breakdown(self) -> OverdueBreakdown:
        now = datetime.now(timezone.utc)

        # Calculate days overdue: NOW - due_date
        days_overdue = func.extract("day", now - BorrowRecord.due_date)

        stmt = select(
            func.sum(
                case((and_(days_overdue >= 1, days_overdue <= 3), 1), else_=0)
            ).label("days_1_3"),
            func.sum(
                case((and_(days_overdue >= 4, days_overdue <= 7), 1), else_=0)
            ).label("days_4_7"),
            func.sum(case((days_overdue > 7, 1), else_=0)).label("days_7_plus"),
        ).where(
            BorrowRecord.status == BorrowStatus.BORROWED, BorrowRecord.due_date < now
        )

        result = self.session.execute(stmt).first()

        return OverdueBreakdown(
            days_1_3=result.days_1_3 or 0,
            days_4_7=result.days_4_7 or 0,
            days_7_plus=result.days_7_plus or 0,
        )

    def get_most_active_members(
        self, start_date: date, end_date: date, limit: int = 5
    ) -> List[TopMember]:
        # Top members by borrow count in range
        stmt = (
            select(
                Member.id,
                Member.name,
                func.count(BorrowRecord.id).label("borrow_count"),
            )
            .join(BorrowRecord)
            .where(
                BorrowRecord.borrowed_at >= start_date,
                BorrowRecord.borrowed_at <= end_date,
            )
            .group_by(Member.id)
            .order_by(desc("borrow_count"))
            .limit(limit)
        )

        results = self.session.execute(stmt).all()

        return [
            TopMember(member_id=str(r.id), name=r.name, borrow_count=r.borrow_count)
            for r in results
        ]

    def get_inventory_health(self) -> InventoryHealth:
        # Consolidate all book health metrics into a single query
        stmt = select(
            func.count(Book.id).filter(Book.available_copies <= 1).label("low_stock"),
            func.count(Book.id).filter(Book.available_copies == 0).label("unavailable"),
            # Optimized 'never borrowed' check using EXISTS subquery inside filter
            func.count(Book.id).filter(
                ~select(BorrowRecord.id).where(BorrowRecord.book_id == Book.id).exists()
            ).label("never_borrowed")
        )
        
        result = self.session.execute(stmt).first()

        return InventoryHealth(
            low_stock_books=result.low_stock or 0,
            never_borrowed_books=result.never_borrowed or 0,
            fully_unavailable_books=result.unavailable or 0,
        )

    def get_daily_active_members(
        self, start_date: date, end_date: date
    ) -> List[DailyActiveMember]:
        # Count distinct member_id per day from BorrowRecord.borrowed_at

        # Cast datetime to date
        borrow_date = cast(BorrowRecord.borrowed_at, Date)

        stmt = (
            select(
                borrow_date.label("date"),
                func.count(func.distinct(BorrowRecord.member_id)).label("count"),
            )
            .where(borrow_date >= start_date, borrow_date <= end_date)
            .group_by(borrow_date)
            .order_by(borrow_date)
        )

        results = self.session.execute(stmt).all()

        return [
            DailyActiveMember(date=r.date, count=r.count)  # type: ignore
            for r in results
        ]

    def get_daily_borrow_counts(
        self, start_date: date, end_date: date
    ) -> Dict[date, int]:
        """
        Helper for forecast. Returns query counts per day.
        """
        borrow_date = cast(BorrowRecord.borrowed_at, Date)

        stmt = (
            select(borrow_date, func.count(BorrowRecord.id))
            .where(borrow_date >= start_date, borrow_date <= end_date)
            .group_by(borrow_date)
        )

        results = self.session.execute(stmt).all()
        return {r[0]: r[1] for r in results}

    def get_popular_books(self, limit: int = 5) -> List[PopularBook]:
        stmt = (
            select(
                Book.id,
                Book.title,
                Book.author,
                func.count(BorrowRecord.id).label("borrow_count"),
            )
            .join(BorrowRecord)
            .group_by(Book.id)
            .order_by(desc("borrow_count"))
            .limit(limit)
        )
        results = self.session.execute(stmt).all()
        return [
            PopularBook(
                book_id=str(r.id),
                title=r.title,
                author=r.author,
                borrow_count=r.borrow_count,
            )
            for r in results
        ]

    def get_recent_activity(self, limit: int = 10) -> List[RecentActivity]:
        # Fetch recent borrows and returns
        stmt = (
            select(
                BorrowRecord.id,
                BorrowRecord.status,
                Book.title.label("book_title"),
                Member.name.label("member_name"),
                func.coalesce(BorrowRecord.returned_at, BorrowRecord.borrowed_at).label("timestamp"),
            )
            .join(Book, BorrowRecord.book_id == Book.id)
            .join(Member, BorrowRecord.member_id == Member.id)
            .order_by(desc("timestamp"))
            .limit(limit)
        )
        results = self.session.execute(stmt).all()
        return [
            RecentActivity(
                id=str(r.id),
                type="return" if r.status == BorrowStatus.RETURNED else "borrow",
                book_title=r.book_title,
                member_name=r.member_name,
                timestamp=r.timestamp.isoformat() if r.timestamp else "",
            )
            for r in results
        ]

    def get_book_analytics(self, book_id: UUID, book: Book) -> BookAnalytics:
        """
        Calculates analytics for a specific book.
        """
        # 1. Total times borrowed
        total_stmt = select(func.count(BorrowRecord.id)).where(BorrowRecord.book_id == book_id)
        total_borrows = self.session.execute(total_stmt).scalar() or 0

        # 2. Avg duration (only for returned)
        diff_expr = func.extract("epoch", BorrowRecord.returned_at - BorrowRecord.borrowed_at)

        avg_stmt = select(func.avg(diff_expr)).where(
            BorrowRecord.book_id == book_id, BorrowRecord.returned_at.is_not(None)
        )
        avg_duration = self.session.execute(avg_stmt).scalar()
        avg_days = (float(avg_duration) / 86400.0) if avg_duration is not None else 0.0

        # 3. Last borrowed
        last_stmt = select(func.max(BorrowRecord.borrowed_at)).where(BorrowRecord.book_id == book_id)
        last_borrowed = self.session.execute(last_stmt).scalar()

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

    def get_member_analytics(self, member_id: UUID) -> MemberAnalyticsResponse:
        """
        Calculates detailed analytics for a member.
        """
        now = datetime.now(timezone.utc)
        diff_expr = func.extract("day", func.coalesce(BorrowRecord.returned_at, now) - BorrowRecord.borrowed_at)
        
        stats_stmt = select(
            func.count(BorrowRecord.id).label("total_count"),
            func.count().filter(BorrowRecord.status == BorrowStatus.BORROWED).label("active_count"),
            func.avg(diff_expr).label("avg_duration"),
            func.max(diff_expr).label("max_duration"),
            func.min(diff_expr).label("min_duration"),
            func.count().filter(
                case(
                    (BorrowRecord.returned_at.is_not(None), BorrowRecord.returned_at > BorrowRecord.due_date),
                    (BorrowRecord.returned_at.is_(None), BorrowRecord.due_date < now),
                    else_=False
                )
            ).label("overdue_count"),
        ).where(BorrowRecord.member_id == member_id)

        stats = self.session.execute(stats_stmt).first()

        fav_author = self.session.execute(
            select(Book.author)
            .join(BorrowRecord, BorrowRecord.book_id == Book.id)
            .where(BorrowRecord.member_id == member_id)
            .group_by(Book.author)
            .order_by(desc(func.count(BorrowRecord.id)))
            .limit(1)
        ).scalar()

        month_fmt = func.to_char(BorrowRecord.borrowed_at, "YYYY-MM").label("month")

        trend_query = (
            select(month_fmt, func.count(BorrowRecord.id).label("count"))
            .where(BorrowRecord.member_id == member_id)
            .group_by(text("month"))
            .order_by(text("month"))
            .limit(6)
        )

        trends = self.session.execute(trend_query).all()

        first_borrow = self.session.execute(
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

        overdue_rate = 0.0
        if stats and stats.total_count > 0:
            overdue_rate = (stats.overdue_count / stats.total_count * 100)

        risk_level = self.calculate_risk_level(overdue_rate)

        return MemberAnalyticsResponse(
            total_books_borrowed=stats.total_count if stats is not None else 0,
            active_books=stats.active_count if stats is not None else 0,
            average_borrow_duration=round(float(stats.avg_duration or 0), 1) if stats is not None else 0.0,
            longest_borrow_duration=int(stats.max_duration or 0) if stats is not None and stats.max_duration else None,
            shortest_borrow_duration=int(stats.min_duration or 0) if stats is not None and stats.min_duration else None,
            overdue_count=stats.overdue_count if stats is not None else 0,
            overdue_rate_percent=round(overdue_rate, 1),
            favorite_author=fav_author,
            borrow_frequency_per_month=round(freq, 1),
            risk_level=risk_level,
            activity_trend=[ActivityTrendItem(month=t.month, count=t.count) for t in trends],
        )

    def calculate_risk_level(self, overdue_rate: float) -> str:
        if overdue_rate > 30:
            return "HIGH"
        if overdue_rate > 10:
            return "MEDIUM"
        return "LOW"
