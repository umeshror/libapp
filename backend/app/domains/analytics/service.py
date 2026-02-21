"""Analytics domain service — dashboard summary aggregation with forecasting."""

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.domains.analytics.repository import AnalyticsRepository
from app.domains.analytics.schemas import (
    AnalyticsSummaryResponse,
    BorrowForecast,
    DailyBorrowCount,
)


class AnalyticsService:
    """Aggregates dashboard analytics with configurable date ranges and forecasting."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = AnalyticsRepository(session)

    def get_summary(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> AnalyticsSummaryResponse:
        """Build the full analytics summary with trend data and 7-day forecast."""
        if not end_date:
            end_date = datetime.now(timezone.utc).date()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        overview = self.repo.get_overview_stats(start_date, end_date)
        overdue_breakdown = self.repo.get_overdue_breakdown()
        inventory_health = self.repo.get_inventory_health()

        top_members = self.repo.get_most_active_members(start_date, end_date, limit=5)
        dam = self.repo.get_daily_active_members(start_date, end_date)

        popular_books = self.repo.get_popular_books(limit=5)
        recent_activity_list = self.repo.get_recent_activity(limit=10)

        daily_borrows_dict = self.repo.get_daily_borrow_counts(start_date, end_date)
        daily_borrows = [
            DailyBorrowCount(date=d, count=c)
            for d, c in sorted(daily_borrows_dict.items())
        ]

        # 7-day forecast via simple moving average
        forecast_start = end_date - timedelta(days=7)
        recent_counts = self.repo.get_daily_borrow_counts(forecast_start, end_date)

        total_recent = sum(recent_counts.values())
        daily_avg = total_recent / 7.0 if total_recent > 0 else 0
        projected_daily = int(round(daily_avg))
        projected_total = projected_daily * 7

        forecast = BorrowForecast(
            projected_next_7_days_total=projected_total,
            daily_projection=projected_daily,
        )

        return AnalyticsSummaryResponse(
            overview=overview,
            overdue_breakdown=overdue_breakdown,
            inventory_health=inventory_health,
            top_members=top_members,
            daily_active_members=dam,
            daily_borrows=daily_borrows,
            forecast=forecast,
            popular_books=popular_books,
            recent_activity=recent_activity_list,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
