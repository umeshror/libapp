import pytest
from uuid import uuid4
from app.domains.books.schemas import BookCreate
from app.domains.borrows.schemas import BorrowRequest
from app.domains.borrows.service import BorrowService
from app.domains.members.schemas import MemberCreate
from app.domains.members.service import MemberService
from app.domains.books.service import BookService

def test_get_book_details_full_lifecycle(client, uow):
    # Setup real data using uow
    book_service = BookService(uow)
    member_service = MemberService(uow)
    borrow_service = BorrowService(uow)

    book = book_service.create_book(
        BookCreate(title="Integration Book", author="Author", isbn="I1", total_copies=5, available_copies=5)
    )
    member = member_service.create_member(MemberCreate(name="Alice", email="alice@test.com"))
    
    # 1. Active borrow
    b1 = borrow_service.borrow_book(book.id, member.id)
    borrow_service.return_book(b1.id)
    
    # 2. Another borrow
    b2 = borrow_service.borrow_book(book.id, member.id)

    # Call API
    response = client.get(f"/api/v1/books/{book.id}/details")
    assert response.status_code == 200
    data = response.json()

    # Verify
    assert data["book"]["title"] == "Integration Book"
    assert len(data["current_borrowers"]) == 1
    assert data["current_borrowers"][0]["name"] == "Alice"
    assert data["borrow_history"]["meta"]["total"] == 1
    assert data["analytics"]["total_times_borrowed"] == 2


def test_get_book_details_not_found(client):
    uuid = uuid4()
    response = client.get(f"/api/v1/books/{uuid}/details")
    assert response.status_code == 404
