import pytest
import uuid
from app.domains.borrows.service import BorrowService
from app.domains.books.service import BookService
from app.domains.members.service import MemberService
from app.domains.books.schemas import BookCreate
from app.domains.members.schemas import MemberCreate
from app.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Setup PostgreSQL test DB
_test_uri = settings.DATABASE_URL.rsplit("/", 1)[0] + "/library_test"
engine = create_engine(_test_uri)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_borrow_service_flow(db_session):
    borrow_service = BorrowService(db_session)
    book_service = BookService(db_session)
    member_service = MemberService(db_session)

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
    # Need to refresh or fetch fresh
    book_refreshed = book_service.get_book(book.id)
    assert book_refreshed.available_copies == 1

    # 2. Return Service
    returned_record = borrow_service.return_book(borrow_record.id)
    assert returned_record.status == "returned"
    assert returned_record.returned_at is not None

    # Verify inventory incremented
    book_refreshed = book_service.get_book(book.id)
    assert book_refreshed.available_copies == 2


def test_borrow_limits(db_session):
    borrow_service = BorrowService(db_session)
    book_service = BookService(db_session)
    member_service = MemberService(db_session)

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


def test_no_inventory(db_session):
    borrow_service = BorrowService(db_session)
    book_service = BookService(db_session)
    member_service = MemberService(db_session)

    book = book_service.create_book(
        BookCreate(
            title="Empty", author="A", isbn="E1", total_copies=1, available_copies=0
        )
    )
    member = member_service.create_member(MemberCreate(name="Mem", email="e@e.com"))

    from app.core.exceptions import InventoryUnavailableError

    with pytest.raises(InventoryUnavailableError):
        borrow_service.borrow_book(book.id, member.id)

def test_book_service_details_consolidation(db_session):
    book_service = BookService(db_session)
    from app.domains.borrows.repository import BorrowRepository
    from app.domains.members.repository import MemberRepository
    from app.domains.borrows.schemas import BorrowRecordCreate
    
    borrow_repo = BorrowRepository(db_session)
    
    # Setup data
    book = book_service.create_book(
        BookCreate(title="Consolidated Book", author="Author", isbn="C1", total_copies=5, available_copies=5)
    )
    member = MemberRepository(db_session).create(
        MemberCreate(name="Tester", email="test@e.com")
    )
    
    # 1. Active borrow
    borrow_repo.create(BorrowRecordCreate(book_id=book.id, member_id=member.id))
    
    # 2. Returned borrow (history)
    b2 = borrow_repo.create(BorrowRecordCreate(book_id=book.id, member_id=member.id))
    from app.models.borrow_record import BorrowRecord, BorrowStatus
    from datetime import datetime, timezone
    
    db_borrow = db_session.get(BorrowRecord, b2.id)
    db_borrow.status = BorrowStatus.RETURNED
    db_borrow.returned_at = datetime.now(timezone.utc)
    db_session.add(db_borrow)
    db_session.commit()
    
    # Test Service Method
    details = book_service.get_book_details(book.id)
    
    assert details.book.id == book.id
    assert len(details.current_borrowers) == 1
    assert details.current_borrowers[0].name == "Tester"
    assert details.borrow_history.meta["total"] == 1
    assert details.analytics.total_times_borrowed == 2

def test_member_service_details_consolidation(db_session):
    member_service = MemberService(db_session)
    from app.domains.books.repository import BookRepository
    from app.domains.borrows.repository import BorrowRepository
    from app.domains.borrows.schemas import BorrowRecordCreate
    
    book_repo = BookRepository(db_session)
    borrow_repo = BorrowRepository(db_session)
    
    # Setup data
    member = member_service.create_member(MemberCreate(name="Member Detail Test", email="detail@test.com"))
    book = book_repo.create(BookCreate(title="B1", author="A1", isbn="ISBN1"))
    
    # Borrow and return for history
    b1 = borrow_repo.create(BorrowRecordCreate(book_id=book.id, member_id=member.id))
    from app.models.borrow_record import BorrowRecord, BorrowStatus
    from datetime import datetime, timezone
    
    db_b = db_session.get(BorrowRecord, b1.id)
    db_b.status = BorrowStatus.RETURNED
    db_b.returned_at = datetime.now(timezone.utc)
    db_session.add(db_b)
    db_session.commit()
    
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
