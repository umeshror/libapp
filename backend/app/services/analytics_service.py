from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    BorrowForecast,
    DailyBorrowCount,
)


class AnalyticsService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = AnalyticsRepository(session)

    def get_summary(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> AnalyticsSummaryResponse:
        # 1. Defaults
        if not end_date:
            end_date = datetime.now(timezone.utc).date()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # 3. Fetch Data
        overview = self.repo.get_overview_stats(start_date, end_date)
        overdue_breakdown = self.repo.get_overdue_breakdown()  # Snapshot
        inventory_health = self.repo.get_inventory_health()  # Snapshot

        top_members = self.repo.get_most_active_members(start_date, end_date, limit=5)

        dam = self.repo.get_daily_active_members(start_date, end_date)

        # Get daily borrows for the main chart
        daily_borrows_dict = self.repo.get_daily_borrow_counts(start_date, end_date)
        daily_borrows = [
            DailyBorrowCount(date=d, count=c)
            for d, c in sorted(daily_borrows_dict.items())
        ]

        # 4. Forecast Logic (Simple Moving Average)
        # Get last 7 days from NOW (or via End Date?)
        # Usually forecast is about the future, so valid base is "recent past".
        forecast_start = end_date - timedelta(days=7)
        recent_activity = self.repo.get_daily_borrow_counts(forecast_start, end_date)

        total_recent = sum(recent_activity.values())
        days_count = (end_date - forecast_start).days
        if days_count == 0:
            days_count = 1  # avoid div zero

        daily_avg = total_recent / 7.0 if total_recent > 0 else 0
        projected_daily = int(round(daily_avg))
        projected_total = projected_daily * 7

        forecast = BorrowForecast(
            projected_next_7_days_total=projected_total,
            daily_projection=projected_daily,
        )

        # 5. response
        response = AnalyticsSummaryResponse(
            overview=overview,
            overdue_breakdown=overdue_breakdown,
            inventory_health=inventory_health,
            top_members=top_members,
            daily_active_members=dam,
            daily_borrows=daily_borrows,
            forecast=forecast,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        return response
