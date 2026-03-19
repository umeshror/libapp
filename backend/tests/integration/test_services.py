import pytest
import uuid
from app.domains.borrows.service import BorrowService
from app.domains.books.service import BookService
from app.domains.members.service import MemberService
from app.domains.books.schemas import BookCreate
from app.domains.members.schemas import MemberCreate


def test_borrow_service_flow(uow):
    borrow_service = BorrowService(uow)
    book_service = BookService(uow)
    member_service = MemberService(uow)

    # Setup data
    book = book_service.create_book(
        BookCreate(
            title="Svc Book",
            author="Auth",
            isbn="S1",
            total_copies=2,
            available_copies=2,
        )
    )
    member = member_service.create_member(
        MemberCreate(name="Svc Member", email="svc@e.com")
    )

    # 1. Successful Borrow
    borrow_record = borrow_service.borrow_book(book.id, member.id)
    assert borrow_record.id is not None
    assert borrow_record.status == "borrowed"

    # Verify inventory decremented
    book_refreshed = book_service.get_book(book.id)
    assert book_refreshed.available_copies == 1

    # 2. Return Service
    returned_record = borrow_service.return_book(borrow_record.id)
    assert returned_record.status == "returned"
    assert returned_record.returned_at is not None

    # Verify inventory incremented
    book_refreshed = book_service.get_book(book.id)
    assert book_refreshed.available_copies == 2


def test_borrow_limits(uow):
    borrow_service = BorrowService(uow)
    book_service = BookService(uow)
    member_service = MemberService(uow)

    member = member_service.create_member(
        MemberCreate(name="Limit Mem", email="limit@e.com")
    )

    # Borrow 5 books
    for i in range(5):
        book = book_service.create_book(
            BookCreate(
                title=f"B{i}",
                author="A",
                isbn=f"L{i}",
                total_copies=1,
                available_copies=1,
            )
        )
        borrow_service.borrow_book(book.id, member.id)

    # Try 6th borrow
    book6 = book_service.create_book(
        BookCreate(
            title="B6", author="A", isbn="L6", total_copies=1, available_copies=1
        )
    )

    from app.core.exceptions import BorrowLimitExceededError

    with pytest.raises(BorrowLimitExceededError):
        borrow_service.borrow_book(book6.id, member.id)


def test_no_inventory(uow):
    borrow_service = BorrowService(uow)
    book_service = BookService(uow)
    member_service = MemberService(uow)

    book = book_service.create_book(
        BookCreate(
            title="Empty", author="A", isbn="E1", total_copies=1, available_copies=0
        )
    )
    member = member_service.create_member(MemberCreate(name="Mem", email="e@e.com"))

    from app.core.exceptions import InventoryUnavailableError

    with pytest.raises(InventoryUnavailableError):
        borrow_service.borrow_book(book.id, member.id)


def test_book_service_details_consolidation(uow):
    book_service = BookService(uow)
    borrow_service = BorrowService(uow)
    member_service = MemberService(uow)
    
    # Setup data
    book = book_service.create_book(
        BookCreate(title="Consolidated Book", author="Author", isbn="C1", total_copies=5, available_copies=5)
    )
    member = member_service.create_member(
        MemberCreate(name="Tester", email="test@e.com")
    )

    # 1. Active borrow (Member 1)
    b1 = borrow_service.borrow_book(book.id, member.id)
    
    # 2. Returned borrow (Member 2)
    member2 = member_service.create_member(MemberCreate(name="Tester 2", email="test2@e.com"))
    b2 = borrow_service.borrow_book(book.id, member2.id)
    borrow_service.return_book(b2.id)
    
    # Test Service Method
    details = book_service.get_book_details(book.id)
    
    assert details.book.id == book.id
    assert len(details.current_borrowers) == 1
    assert details.current_borrowers[0].name == "Tester"
    assert details.borrow_history.meta["total"] == 1
    assert details.analytics.total_times_borrowed == 2


def test_member_service_details_consolidation(uow):
    member_service = MemberService(uow)
    book_service = BookService(uow)
    
    # Setup data
    member = member_service.create_member(MemberCreate(name="Member Detail Test", email="detail@test.com"))
    book = book_service.create_book(BookCreate(title="B1", author="A1", isbn="ISBN1"))
    
    # Borrow and return for history
    from app.domains.borrows.service import BorrowService
    borrow_service = BorrowService(uow)
    b1 = borrow_service.borrow_book(book.id, member.id)
    borrow_service.return_book(b1.id)
    
    # Test Details
    core = member_service.get_member_details(member.id)
    assert core.member.id == member.id
    assert core.analytics_summary.total_books_borrowed == 1
    
    # Test History
    history_res = member_service.get_member_borrow_history(member.id, limit=10, offset=0, status="all", sort="borrowed_at", order="desc")
    assert history_res.meta["total"] == 1
    assert history_res.data[0].book_title == "B1"
    
    # Test Analytics
    analytics = member_service.get_member_analytics(member.id)
    assert analytics.total_books_borrowed == 1
    assert analytics.risk_level in ["LOW", "MEDIUM", "HIGH"]
