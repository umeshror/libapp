import pytest
from uuid import uuid4
from app.services.borrow_service import BorrowService
from app.services.book_service import BookService
from app.services.member_service import MemberService
from app.repositories.book_repository import BookRepository
from app.schemas import BookCreate, MemberCreate, BookUpdate
from app.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.exceptions import (
    MemberNotFoundError,
    BookNotFoundError,
    BorrowRecordNotFoundError,
    AlreadyReturnedError,
)

engine = create_engine(settings.DATABASE_URL.rsplit("/", 1)[0] + "/library_test")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_borrow_service_edge_cases(db_session):
    borrow_service = BorrowService(db_session)
    book_service = BookService(db_session)
    member_service = MemberService(db_session)

    # Setup
    book = book_service.create_book(
        BookCreate(
            title="Edge Book",
            author="A",
            isbn="Edge1",
            total_copies=5,
            available_copies=5,
        )
    )
    member = member_service.create_member(
        MemberCreate(name="Edge Member", email="edge@e.com")
    )

    # 1. Borrow with invalid member
    with pytest.raises(MemberNotFoundError):
        borrow_service.borrow_book(book.id, uuid4())

    # 2. Borrow with invalid book
    with pytest.raises(BookNotFoundError):
        borrow_service.borrow_book(uuid4(), member.id)

    # 3. Double borrow (same book)
    borrow_service.borrow_book(book.id, member.id)
    from app.core.exceptions import ActiveBorrowExistsError

    with pytest.raises(ActiveBorrowExistsError):
        borrow_service.borrow_book(book.id, member.id)

    # 4. Return invalid borrow/record
    with pytest.raises(BorrowRecordNotFoundError):
        borrow_service.return_book(uuid4())

    # 5. Return already returned
    borrow = borrow_service.borrow_repo.get_active_borrow(book.id, member.id)
    # Return once
    borrow_service.return_book(borrow.id)
    # Return again
    with pytest.raises(AlreadyReturnedError):
        borrow_service.return_book(borrow.id)

    # 6. Missing book during return cannot be tested via DB due to FK CASCADE constraints.
    # This branch requires a mock-based unit test for full coverage.


def test_book_repository_edge_cases(db_session):
    repo = BookRepository(db_session)

    # 1. Get invalid ID
    assert repo.get(uuid4()) is None

    # 2. Get invalid ISBN
    assert repo.get_by_isbn("nonexistent") is None

    # 3. Update invalid ID
    assert repo.update(uuid4(), BookUpdate(title="New")) is None

    # 4. List books
    result = repo.list()
    assert isinstance(result, dict)
    assert "items" in result
    assert isinstance(result["items"], list)


def test_service_wrappers(db_session):
    book_svc = BookService(db_session)
    member_svc = MemberService(db_session)

    # Book Service Coverage
    b = book_svc.create_book(BookCreate(title="SVC List", author="A", isbn="LST1"))
    assert len(book_svc.list_books().data) > 0
    assert book_svc.get_book_by_isbn("LST1") is not None
    assert book_svc.update_book(b.id, BookUpdate(title="Upd")) is not None

    # Member Service Coverage
    m = member_svc.create_member(MemberCreate(name="Mem List", email="lst@e.com"))
    assert len(member_svc.list_members().data) > 0
    assert member_svc.get_member(m.id) is not None
    assert member_svc.get_member_by_email("lst@e.com") is not None
    assert member_svc.repo.get_by_email("nonexistent") is None


def test_member_repository_coverage(db_session):
    from app.repositories.member_repository import MemberRepository

    repo = MemberRepository(db_session)
    result = repo.list()
    assert isinstance(result, dict)
    assert isinstance(result["items"], list)
