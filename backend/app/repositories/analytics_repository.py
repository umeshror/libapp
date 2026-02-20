from datetime import date, datetime, timezone
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, desc, cast, Date
from app.models.book import Book
from app.models.member import Member
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.schemas.analytics import (
    AnalyticsOverview,
    OverdueBreakdown,
    TopMember,
    InventoryHealth,
    DailyActiveMember,
)


class AnalyticsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_overview_stats(self, start_date: date, end_date: date) -> AnalyticsOverview:
        # 1. Total books
        total_books = self.session.query(func.count(Book.id)).scalar() or 0

        # 2. Active borrows (current snapshot)
        active_borrows = (
            self.session.query(func.count(BorrowRecord.id))
            .filter(BorrowRecord.status == BorrowStatus.BORROWED)
            .scalar()
            or 0
        )

        # 3. Overdue borrows (current snapshot)
        now = datetime.now(timezone.utc)
        overdue_borrows = (
            self.session.query(func.count(BorrowRecord.id))
            .filter(
                BorrowRecord.status == BorrowStatus.BORROWED,
                BorrowRecord.due_date < now,
            )
            .scalar()
            or 0
        )

        # 4. Utilization Rate
        # Capacity = Sum of total_copies of all books
        total_capacity = self.session.query(func.sum(Book.total_copies)).scalar() or 0

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
        # We need this in days.
        # In Postgres: EXTRACT(DAY FROM (now() - due_date))

        days_overdue = func.extract("day", now - BorrowRecord.due_date)

        # Bucket logic
        # 1-3 days
        # 4-7 days
        # 7+ days

        query = self.session.query(
            func.sum(
                case((and_(days_overdue >= 1, days_overdue <= 3), 1), else_=0)
            ).label("days_1_3"),
            func.sum(
                case((and_(days_overdue >= 4, days_overdue <= 7), 1), else_=0)
            ).label("days_4_7"),
            func.sum(case((days_overdue > 7, 1), else_=0)).label("days_7_plus"),
        ).filter(
            BorrowRecord.status == BorrowStatus.BORROWED, BorrowRecord.due_date < now
        )

        result = query.one()

        return OverdueBreakdown(
            days_1_3=result.days_1_3 or 0,
            days_4_7=result.days_4_7 or 0,
            days_7_plus=result.days_7_plus or 0,
        )

    def get_most_active_members(
        self, start_date: date, end_date: date, limit: int = 5
    ) -> List[TopMember]:
        # Top members by borrow count in range
        query = (
            self.session.query(
                Member.id,
                Member.name,
                func.count(BorrowRecord.id).label("borrow_count"),
            )
            .join(BorrowRecord)
            .filter(
                BorrowRecord.borrowed_at >= start_date,
                BorrowRecord.borrowed_at <= end_date,
            )
            .group_by(Member.id)
            .order_by(desc("borrow_count"))
            .limit(limit)
        )

        results = query.all()

        return [
            TopMember(member_id=str(r.id), name=r.name, borrow_count=r.borrow_count)
            for r in results
        ]

    def get_inventory_health(self) -> InventoryHealth:
        # Low stock: available <= 1
        low_stock = (
            self.session.query(func.count(Book.id))
            .filter(Book.available_copies <= 1)
            .scalar()
            or 0
        )

        # Fully unavailable: available == 0
        unavailable = (
            self.session.query(func.count(Book.id))
            .filter(Book.available_copies == 0)
            .scalar()
            or 0
        )

        # Never borrowed
        # Use NOT EXISTS for massive performance gain over OUTER JOIN
        never_borrowed = (
            self.session.query(func.count(Book.id))
            .filter(
                ~Book.borrow_records.any()  # type: ignore
            )
            .scalar()
            or 0
        )

        return InventoryHealth(
            low_stock_books=low_stock,
            never_borrowed_books=never_borrowed,
            fully_unavailable_books=unavailable,
        )

    def get_daily_active_members(
        self, start_date: date, end_date: date
    ) -> List[DailyActiveMember]:
        # Count distinct member_id per day from BorrowRecord.borrowed_at

        # Cast datetime to date
        borrow_date = cast(BorrowRecord.borrowed_at, Date)

        query = (
            self.session.query(
                borrow_date.label("date"),
                func.count(func.distinct(BorrowRecord.member_id)).label("count"),
            )
            .filter(borrow_date >= start_date, borrow_date <= end_date)
            .group_by(borrow_date)
            .order_by(borrow_date)
        )

        results = query.all()

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

        query = (
            self.session.query(borrow_date, func.count(BorrowRecord.id))
            .filter(borrow_date >= start_date, borrow_date <= end_date)
            .group_by(borrow_date)
        )

        results = query.all()
        return {r[0]: r[1] for r in results}
