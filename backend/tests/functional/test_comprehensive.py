import pytest
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.domains.borrows.service import BorrowService
from app.domains.books.service import BookService
from app.domains.members.service import MemberService
from app.domains.books.schemas import BookCreate
from app.domains.members.schemas import MemberCreate
from app.core.config import settings
from app.core.exceptions import (
    InventoryUnavailableError,
    BorrowLimitExceededError,
    AlreadyReturnedError,
    ActiveBorrowExistsError,
)

_test_uri = settings.DATABASE_URL.rsplit("/", 1)[0] + "/library_test"
engine = create_engine(_test_uri)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Creates a new database session for a test.
    Drops all tables after test to ensure isolation.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# -----------------------------------------------------------------------------
# 1. Unit Tests for Service Layer (Business Logic & Invariants)
# -----------------------------------------------------------------------------


def test_borrow_invariants(db_session):
    """
    Verifies that borrowing maintains inventory invariants:
    - Available copies decrement by 1.
    - Borrow record is created with 'borrowed' status.
    """
    borrow_svc = BorrowService(db_session)
    book_svc = BookService(db_session)
    member_svc = MemberService(db_session)

    # Setup
    book = book_svc.create_book(
        BookCreate(
            title="Invariant Book",
            author="A",
            isbn="INV1",
            total_copies=5,
            available_copies=5,
        )
    )
    member = member_svc.create_member(
        MemberCreate(name="Inv Member", email="inv@e.com")
    )

    # Action
    borrow_svc.borrow_book(book.id, member.id)

    # Assert Invariants
    book_fresh = book_svc.get_book(book.id)
    assert book_fresh.available_copies == 4, (
        "Invariant Violated: Available copies did not decrement."
    )

    borrows_result = borrow_svc.borrow_repo.list(member_id=member.id)
    borrows = borrows_result["items"]
    assert len(borrows) == 1
    assert borrows[0].status == "borrowed"


# -----------------------------------------------------------------------------
# 2. Integration Test for Borrow Flow
# -----------------------------------------------------------------------------


def test_full_borrow_return_cycle(db_session):
    """
    Tests the complete lifecycle: Borrow -> Return -> Inventory Restoration.
    """
    borrow_svc = BorrowService(db_session)
    book_svc = BookService(db_session)
    member_svc = MemberService(db_session)

    book = book_svc.create_book(
        BookCreate(
            title="Flow Book",
            author="A",
            isbn="FL1",
            total_copies=1,
            available_copies=1,
        )
    )
    member = member_svc.create_member(
        MemberCreate(name="Flow Member", email="flow@e.com")
    )

    # Borrow
    record = borrow_svc.borrow_book(book.id, member.id)
    assert record.status == "borrowed"
    assert book_svc.get_book(book.id).available_copies == 0

    # Return
    returned = borrow_svc.return_book(record.id)
    assert returned.status == "returned"
    assert book_svc.get_book(book.id).available_copies == 1


# -----------------------------------------------------------------------------
# 3. Concurrency Simulation Test (Race Condition)
# -----------------------------------------------------------------------------


def test_concurrent_borrow_race_condition():
    """
    Simulates a race condition where two threads attempt to borrow
    the LAST available copy of a book.
    Expected: Exactly one thread succeeds, the other fails.
    """
    # Use separate sessions for concurrency simulation
    concurrent_engine = create_engine(_test_uri)
    ConcurrentSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=concurrent_engine
    )

    # Setup Data (Outside threads)
    Base.metadata.create_all(bind=concurrent_engine)
    setup_session = ConcurrentSessionLocal()
    book_svc = BookService(setup_session)
    member_svc = MemberService(setup_session)

    book = book_svc.create_book(
        BookCreate(
            title="Race Book",
            author="A",
            isbn="RACE1",
            total_copies=1,
            available_copies=1,
        )
    )
    member1 = member_svc.create_member(MemberCreate(name="Racer 1", email="r1@e.com"))
    member2 = member_svc.create_member(MemberCreate(name="Racer 2", email="r2@e.com"))

    book_id = book.id
    m1_id = member1.id
    m2_id = member2.id
    setup_session.close()

    results = []

    def attempt_borrow(member_id):
        session = ConcurrentSessionLocal()
        svc = BorrowService(session)
        try:
            svc.borrow_book(book_id, member_id)
            results.append("success")
        except InventoryUnavailableError:
            results.append("inventory_error")
        except Exception as e:
            results.append(f"error: {e}")
        finally:
            session.close()

    t1 = threading.Thread(target=attempt_borrow, args=(m1_id,))
    t2 = threading.Thread(target=attempt_borrow, args=(m2_id,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Cleanup
    Base.metadata.drop_all(bind=concurrent_engine)

    assert results.count("success") == 1, (
        f"Expected 1 success, got {results.count('success')} | Full: {results}"
    )
    assert results.count("inventory_error") == 1, (
        f"Expected 1 inventory error, got {results.count('inventory_error')} | Full: {results}"
    )


# -----------------------------------------------------------------------------
# 4. Double Return Test
# -----------------------------------------------------------------------------


def test_double_return_prevention(db_session):
    """
    Ensures a book cannot be returned twice (idempotency/error handling).
    """
    borrow_svc = BorrowService(db_session)
    book_svc = BookService(db_session)
    member_svc = MemberService(db_session)

    book = book_svc.create_book(
        BookCreate(
            title="Ret Book", author="A", isbn="RT1", total_copies=1, available_copies=1
        )
    )
    member = member_svc.create_member(
        MemberCreate(name="Ret Member", email="ret@e.com")
    )

    record = borrow_svc.borrow_book(book.id, member.id)

    # First Return - Success
    borrow_svc.return_book(record.id)

    # Second Return - Failure
    with pytest.raises(AlreadyReturnedError):
        borrow_svc.return_book(record.id)

    # Invariant: Inventory stays at 1 (not 2)
    assert book_svc.get_book(book.id).available_copies == 1


# -----------------------------------------------------------------------------
# 5. Borrow Limit Enforcement Test
# -----------------------------------------------------------------------------


def test_borrow_limit_enforcement(db_session):
    """
    Ensures a member cannot borrow more than 5 books.
    """
    borrow_svc = BorrowService(db_session)
    book_svc = BookService(db_session)
    member_svc = MemberService(db_session)

    member = member_svc.create_member(MemberCreate(name="Max Mem", email="max@e.com"))

    # Fill quota (5 books)
    for i in range(5):
        book = book_svc.create_book(
            BookCreate(
                title=f"B{i}",
                author="A",
                isbn=f"MAX{i}",
                total_copies=1,
                available_copies=1,
            )
        )
        borrow_svc.borrow_book(book.id, member.id)

    # Attempt 6th
    book6 = book_svc.create_book(
        BookCreate(
            title="B6", author="A", isbn="MAX6", total_copies=1, available_copies=1
        )
    )

    with pytest.raises(BorrowLimitExceededError):
        borrow_svc.borrow_book(book6.id, member.id)
