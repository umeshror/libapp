import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.models.borrow_record import BorrowStatus
from app.models.member import Member
from app.models.book import Book


@pytest.fixture
def test_member(db_session):
    member = Member(id=uuid4(), name="Test Member", email=f"test_{uuid4()}@example.com")
    db_session.add(member)
    db_session.commit()
    return member


@pytest.fixture
def test_book(db_session):
    book = Book(id=uuid4(), title="Test Book", author="Test Author", isbn=str(uuid4()))
    db_session.add(book)
    db_session.commit()
    return book


def test_get_member_core_details(client, db_session, test_member):
    response = client.get(f"/members/{test_member.id}")
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert "member" in data, f"Key 'member' not in {data}"
    assert data["member"]["id"] == str(test_member.id)
    assert "membership_duration_days" in data
    assert "active_borrows_count" in data
    assert "analytics_summary" in data


def test_get_member_borrow_history_pagination(
    client, db_session, test_member, test_book
):
    from app.models.borrow_record import BorrowRecord

    # Seed 15 records
    for i in range(15):
        record = BorrowRecord(
            id=uuid4(),
            book_id=test_book.id,
            member_id=test_member.id,
            borrowed_at=datetime.now(timezone.utc) - timedelta(days=i),
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            status=BorrowStatus.RETURNED,
            returned_at=datetime.now(timezone.utc),
        )
        db_session.add(record)
    db_session.commit()

    # Test Page 1
    response = client.get(f"/members/{test_member.id}/borrows?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 10
    assert data["meta"]["total"] >= 15
    assert data["meta"]["has_more"] is True

    # Test Page 2
    response = client.get(f"/members/{test_member.id}/borrows?limit=10&offset=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 5
    assert data["meta"]["has_more"] is False


def test_get_member_analytics(client, db_session, test_member, test_book):
    from app.models.borrow_record import BorrowRecord

    # One returned (on time)
    record1 = BorrowRecord(
        id=uuid4(),
        book_id=test_book.id,
        member_id=test_member.id,
        borrowed_at=datetime.now(timezone.utc) - timedelta(days=10),
        due_date=datetime.now(timezone.utc) + timedelta(days=4),
        status=BorrowStatus.RETURNED,
        returned_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    # One overdue
    record2 = BorrowRecord(
        id=uuid4(),
        book_id=test_book.id,
        member_id=test_member.id,
        borrowed_at=datetime.now(timezone.utc) - timedelta(days=20),
        due_date=datetime.now(timezone.utc) - timedelta(days=5),
        status=BorrowStatus.BORROWED,
    )
    db_session.add(record1)
    db_session.add(record2)
    db_session.commit()

    response = client.get(f"/members/{test_member.id}/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_books_borrowed"] >= 2
    assert data["active_books"] >= 1
    assert data["overdue_count"] >= 1
    assert data["overdue_rate_percent"] > 0
    assert "risk_level" in data
