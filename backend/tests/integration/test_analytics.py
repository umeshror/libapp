import pytest
from datetime import datetime, timedelta, date
from unittest.mock import MagicMock, patch
from app.domains.analytics.schemas import (
    AnalyticsOverview,
    OverdueBreakdown,
    TopMember,
    InventoryHealth,
    DailyActiveMember,
    BorrowForecast,
    PopularBook,
    RecentActivity,
)
from app.domains.analytics.service import AnalyticsService

# Mock Data
MOCK_OVERVIEW = AnalyticsOverview(
    total_books=100, active_borrows=20, overdue_borrows=5, utilization_rate=20.0
)
MOCK_OVERDUE = OverdueBreakdown(days_1_3=2, days_4_7=1, days_7_plus=2)
MOCK_TOP_MEMBERS = [TopMember(member_id="1", name="Alice", borrow_count=10)]
MOCK_INVENTORY = InventoryHealth(
    low_stock_books=5, never_borrowed_books=10, fully_unavailable_books=2
)
MOCK_DAM = [DailyActiveMember(date=date.today(), count=15)]
MOCK_FORECAST = {
    "projected_next_7_days_total": 42,
    "daily_projection": 6,
}  # Dict from Repo


@pytest.fixture
def mock_repo():
    with patch("app.domains.analytics.service.AnalyticsRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.get_overview_stats.return_value = MOCK_OVERVIEW
        instance.get_overdue_breakdown.return_value = MOCK_OVERDUE
        instance.get_most_active_members.return_value = MOCK_TOP_MEMBERS
        instance.get_inventory_health.return_value = MOCK_INVENTORY
        instance.get_daily_active_members.return_value = MOCK_DAM
        instance.get_daily_borrow_counts.return_value = {date.today(): 6}
        instance.get_popular_books.return_value = [
            PopularBook(book_id="b1", title="Book 1", author="A1", borrow_count=5)
        ]
        instance.get_recent_activity.return_value = [
            RecentActivity(id="1", type="borrow", book_title="Book 1", member_name="Alice", timestamp="2024-01-01T12:00:00")
        ]
        yield instance


def test_analytics_summary_structure(client, mock_repo):
    """Test API structure using mocked repository."""
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["overview"]["total_books"] == 100
    assert data["overdue_breakdown"]["days_1_3"] == 2
    assert data["top_members"][0]["name"] == "Alice"
    assert (
        data["forecast"]["projected_next_7_days_total"] == 7
    )  # 6 / 7 days = ~1 * 7 = 7
    assert data["popular_books"][0]["title"] == "Book 1"
    assert data["recent_activity"][0]["type"] == "borrow"


def test_date_filter_validation(client, mock_repo):
    """Test valid and invalid date ranges."""
    # Invalid: Start > End
    response = client.get("/api/v1/analytics/summary?from=2025-01-10&to=2025-01-01")
    assert response.status_code == 400
    assert "Start date cannot be after end date" in response.json()["detail"]

    # Valid (Mock will be called)
    response = client.get("/api/v1/analytics/summary?from=2025-01-01&to=2025-01-10")
    assert response.status_code == 200
