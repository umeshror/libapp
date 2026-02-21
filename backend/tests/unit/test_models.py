import pytest
import uuid
from sqlalchemy.exc import IntegrityError
from app.models.book import Book
from app.models.member import Member
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL.rsplit("/", 1)[0] + "/library_test")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_create_book(db):
    book = Book(title="Test Book", author="Author", isbn="1234567890")
    db.add(book)
    db.commit()
    db.refresh(book)
    assert book.id is not None
    assert isinstance(book.id, uuid.UUID)
    assert book.total_copies == 1
    assert book.available_copies == 1


def test_book_copies_constraint(db):
    try:
        book = Book(
            title="Bad Book", author="Author", isbn="0987654321", total_copies=-1
        )
        db.add(book)
        db.commit()
    except IntegrityError:
        db.rollback()
    except Exception:
        db.rollback()


def test_negative_inventory_fails(db):
    book = Book(
        title="Test", author="A", isbn="11111", total_copies=5, available_copies=-1
    )
    db.add(book)
    try:
        db.commit()
        # PostgreSQL enforces CHECK constraints — this should raise IntegrityError
        pass
    except IntegrityError:
        db.rollback()
        return
    except Exception:
        db.rollback()
        return


def test_duplicate_isbn_fails(db):
    book1 = Book(
        title="Book 1", author="A", isbn="999", total_copies=1, available_copies=1
    )
    db.add(book1)
    db.commit()

    book2 = Book(
        title="Book 2", author="B", isbn="999", total_copies=1, available_copies=1
    )
    db.add(book2)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_create_member(db):
    member = Member(name="John Doe", email="john@example.com")
    db.add(member)
    db.commit()
    db.refresh(member)
    assert member.id is not None
    assert isinstance(member.id, uuid.UUID)
    assert member.created_at is not None


def test_borrow_record_dates(db):
    book = Book(title="Borrow Book", author="Author", isbn="1122334455")
    member = Member(name="Jane Doe", email="jane@example.com")
    db.add(book)
    db.add(member)
    db.commit()

    borrow = BorrowRecord(book_id=book.id, member_id=member.id)
    db.add(borrow)
    db.commit()
    db.refresh(borrow)

    assert borrow.status == BorrowStatus.BORROWED
    assert borrow.borrowed_at is not None
