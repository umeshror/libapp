import pytest
import uuid
from app.services.borrow_service import BorrowService
from app.services.book_service import BookService
from app.services.member_service import MemberService
from app.schemas import BookCreate, MemberCreate
from app.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup in-memory DB for service testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
