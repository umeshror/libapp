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
def mock_uow():
    with patch("app.domains.analytics.router.AnalyticsService") as MockService:
        service_instance = MockService.return_value
        # Mock the summary response
        from app.domains.analytics.schemas import AnalyticsSummaryResponse
        summary = AnalyticsSummaryResponse(
            overview=MOCK_OVERVIEW,
            overdue_breakdown=MOCK_OVERDUE,
            inventory_health=MOCK_INVENTORY,
            top_members=MOCK_TOP_MEMBERS,
            daily_active_members=MOCK_DAM,
            daily_borrows=[],
            forecast=BorrowForecast(projected_next_7_days_total=7, daily_projection=1),
            popular_books=[PopularBook(book_id="b1", title="Book 1", author="A1", borrow_count=5)],
            recent_activity=[RecentActivity(id="1", type="borrow", book_title="Book 1", member_name="Alice", timestamp="2024-01-01T12:00:00")],
            generated_at=datetime.now().isoformat()
        )
        service_instance.get_summary.return_value = summary
        yield service_instance


def test_analytics_summary_structure(client, mock_uow):
    """Test API structure using mocked service."""
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["overview"]["total_books"] == 100
    assert data["overdue_breakdown"]["days_1_3"] == 2
    assert data["top_members"][0]["name"] == "Alice"
    assert data["popular_books"][0]["title"] == "Book 1"
    assert data["recent_activity"][0]["type"] == "borrow"


def test_date_filter_validation(client, mock_uow):
    """Test valid and invalid date ranges."""
    # Invalid: Start > End
    response = client.get("/api/v1/analytics/summary?from=2025-01-10&to=2025-01-01")
    assert response.status_code == 400
    assert "Start date cannot be after end date" in response.json()["detail"]

    # Valid (Mock will be called)
    response = client.get("/api/v1/analytics/summary?from=2025-01-01&to=2025-01-10")
    assert response.status_code == 200
