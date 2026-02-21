import pytest
import uuid
from app.domains.books.repository import BookRepository
from app.domains.members.repository import MemberRepository
from app.domains.borrows.repository import BorrowRepository
from app.domains.books.schemas import BookCreate, BookUpdate
from app.domains.members.schemas import MemberCreate
from app.domains.borrows.schemas import BorrowRecordCreate
from app.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL.rsplit("/", 1)[0] + "/library_test")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_book_repository(db_session):
    repo = BookRepository(db_session)
    book_in = BookCreate(title="Repo Book", author="Repo Author", isbn="9988776655")
    created_book = repo.create(book_in)

    assert created_book.id is not None
    assert created_book.title == "Repo Book"

    fetched_book = repo.get(created_book.id)
    assert fetched_book is not None
    assert fetched_book.id == created_book.id

    isbn_book = repo.get_by_isbn("9988776655")
    assert isbn_book is not None

    update_data = BookUpdate(title="Updated Repo Book")
    updated_book = repo.update(created_book.id, update_data)
    assert updated_book.title == "Updated Repo Book"


def test_member_repository(db_session):
    repo = MemberRepository(db_session)
    member_in = MemberCreate(name="Repo Member", email="repo@example.com")
    created_member = repo.create(member_in)

    assert created_member.id is not None

    fetched_member = repo.get(created_member.id)
    assert fetched_member is not None

    email_member = repo.get_by_email("repo@example.com")
    assert email_member is not None


def test_borrow_repository(db_session):
    book_repo = BookRepository(db_session)
    member_repo = MemberRepository(db_session)
    borrow_repo = BorrowRepository(db_session)

    book = book_repo.create(BookCreate(title="B1", author="A1", isbn="111"))
    member = member_repo.create(MemberCreate(name="M1", email="m1@e.com"))

    borrow_in = BorrowRecordCreate(book_id=book.id, member_id=member.id)
    borrow_record = borrow_repo.create(borrow_in)

    assert borrow_record.id is not None
    assert borrow_record.status == "borrowed"

    active_borrow = borrow_repo.get_active_borrow(book.id, member.id)
    assert active_borrow is not None
    assert active_borrow.id == borrow_record.id

    from app.models.borrow_record import BorrowStatus

    active_list_result = borrow_repo.list(
        member_id=member.id, status=BorrowStatus.BORROWED
    )
    active_list = active_list_result["items"]
    assert len(active_list) == 1
    assert active_list[0].id == borrow_record.id


def test_book_locking(db_session):
    repo = BookRepository(db_session)
    book_in = BookCreate(title="Lock Book", author="Lock Author", isbn="locked123")
    created_book = repo.create(book_in)

    # Verify get_with_lock returns the expected book
    locked_book = repo.get_with_lock(created_book.id)
    assert locked_book is not None
    assert locked_book.id == created_book.id
    # Ensure it's an ORM object, not a Pydantic model, as required for updates
    from app.models.book import Book

    assert isinstance(locked_book, Book)
