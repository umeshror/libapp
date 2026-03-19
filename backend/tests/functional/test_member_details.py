import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.domains.members.schemas import MemberCreate
from app.domains.members.service import MemberService
from app.domains.books.schemas import BookCreate
from app.domains.books.service import BookService
from app.domains.borrows.service import BorrowService
from app.models.borrow_record import BorrowStatus

def test_get_member_core_details(client, uow):
    member_service = MemberService(uow)
    member = member_service.create_member(MemberCreate(name="Test Member", email=f"test_{uuid4()}@example.com"))
    
    response = client.get(f"/api/v1/members/{member.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["member"]["id"] == str(member.id)
    assert "membership_duration_days" in data
    assert "active_borrows_count" in data


def test_get_member_borrow_history_pagination(client, uow):
    member_service = MemberService(uow)
    book_service = BookService(uow)
    borrow_service = BorrowService(uow)

    member = member_service.create_member(MemberCreate(name="History Member", email=f"hist_{uuid4()}@test.com"))
    book = book_service.create_book(BookCreate(title="History Book", author="Auth", isbn=str(uuid4())))

    # Seed 15 records
    for i in range(15):
        b = borrow_service.borrow_book(book.id, member.id)
        borrow_service.return_book(b.id)

    # Test Page 1
    response = client.get(f"/api/v1/members/{member.id}/borrows/?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 10
    assert data["meta"]["total"] >= 15

    # Test Page 2
    response = client.get(f"/api/v1/members/{member.id}/borrows/?limit=10&offset=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 5


def test_get_member_analytics(client, uow):
    member_service = MemberService(uow)
    book_service = BookService(uow)
    borrow_service = BorrowService(uow)

    member = member_service.create_member(MemberCreate(name="Analytics Member", email=f"ana_{uuid4()}@test.com"))
    book = book_service.create_book(BookCreate(title="Analytics Book", author="Auth", isbn=str(uuid4()), total_copies=10, available_copies=10))

    # One returned
    b1 = borrow_service.borrow_book(book.id, member.id)
    borrow_service.return_book(b1.id)
    
    # One active
    borrow_service.borrow_book(book.id, member.id)

    response = client.get(f"/api/v1/members/{member.id}/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_books_borrowed"] >= 2
    assert data["active_books"] >= 1
    assert "risk_level" in data
