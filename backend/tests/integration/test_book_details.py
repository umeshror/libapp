import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime
from app.schemas.book_details import BorrowerInfo, BorrowHistoryItem, BookAnalytics


def test_get_book_details_full_lifecycle(client):
    book_id = uuid4()

    # Mock Data
    mock_book = MagicMock()
    mock_book.id = book_id
    mock_book.title = "Mocked Book"
    mock_book.author = "Tester"
    mock_book.isbn = "111-222-333"
    mock_book.total_copies = 5
    mock_book.available_copies = 3
    mock_book.created_at = datetime.utcnow()
    mock_book.updated_at = datetime.utcnow()

    mock_borrower = BorrowerInfo(
        borrow_id=uuid4(),
        member_id=uuid4(),
        name="Alice",
        borrowed_at=datetime.utcnow(),
        due_date=datetime.utcnow(),
        days_until_due=5,
    )

    mock_history_item = BorrowHistoryItem(
        member_id=uuid4(),
        member_name="Bob",
        borrowed_at=datetime.utcnow(),
        returned_at=datetime.utcnow(),
        duration_days=10,
    )

    mock_analytics = BookAnalytics(
        total_times_borrowed=10,
        average_borrow_duration=5.5,
        last_borrowed_at=datetime.utcnow(),
        popularity_rank=1,
        availability_status="AVAILABLE",
        longest_borrow_duration=12,
        shortest_borrow_duration=2,
        return_delay_count=0,
    )

    with patch("app.services.book_service.BookRepository") as MockRepo:
        repo_instance = MockRepo.return_value
        repo_instance.get_with_lock.return_value = mock_book
        repo_instance.get_current_borrowers.return_value = [mock_borrower]
        repo_instance.get_borrow_history.return_value = ([mock_history_item], 50)
        repo_instance.get_analytics.return_value = mock_analytics

        # Call API
        response = client.get(f"/books/{book_id}/details")
        assert response.status_code == 200
        data = response.json()

        # Verify
        assert data["book"]["title"] == "Mocked Book"
        assert len(data["current_borrowers"]) == 1
        assert data["current_borrowers"][0]["name"] == "Alice"
        assert data["borrow_history"]["meta"]["total"] == 50
        assert data["analytics"]["popularity_rank"] == 1


def test_get_book_details_not_found(client):
    with patch("app.services.book_service.BookRepository") as MockRepo:
        repo_instance = MockRepo.return_value
        repo_instance.get_with_lock.return_value = None

        uuid = uuid4()
        response = client.get(f"/books/{uuid}/details")
        assert response.status_code == 404
