import pytest
import subprocess
from app.db.session import SessionLocal
from app.models.book import Book
from app.models.member import Member
from app.models.borrow_record import BorrowRecord, BorrowStatus


def test_seeder_minimal_scenario_idempotency(uow):
    """
    Test that the seeder runs successfully and is idempotent.
    """
    from app.seeds.scenarios import SCENARIOS
    from app.seeds.seed_books import seed_books
    from app.seeds.seed_members import seed_members
    from app.seeds.seed_borrows import seed_borrows
    from faker import Faker

    config = SCENARIOS["minimal"]
    faker = Faker()
    Faker.seed(42)

    # 1. Run seeder first time (minimal scenario)
    seed_books(uow, config["books"], faker)
    seed_members(uow, config["members"], faker)
    seed_borrows(
        uow,
        config["active_borrows"],
        config["returned_borrows"],
        config["overdue_borrows"],
        faker,
    )

    # Verify counts
    with uow:
        book_count = uow.session.query(Book).count()
        member_count = uow.session.query(Member).count()
        borrow_count = uow.session.query(BorrowRecord).count()

    # Minimal scenario targets: 2000 books, 300 members, 1315 borrows
    # Due to randomized member selection and the 5-book limit constraint,
    # the actual generated count may be slightly lower than 1315.
    assert book_count >= 2000
    assert member_count >= 300
    assert borrow_count > 1000

    # 2. Run seeder second time
    Faker.seed(42)
    faker.unique.clear()
    seed_books(uow, config["books"], faker)
    seed_members(uow, config["members"], faker)

    with uow:
        book_count_2 = uow.session.query(Book).count()
        member_count_2 = uow.session.query(Member).count()

    assert book_count_2 == book_count, (
        "Book count changed after 2nd seed run (should be idempotent)"
    )
    assert member_count_2 == member_count, (
        "Member count changed after 2nd seed run (should be idempotent)"
    )

    # Constraints verification
    with uow:
        invalid_books = uow.session.query(Book).filter(Book.available_copies < 0).all()
        assert len(invalid_books) == 0, "Found books with negative availability"

        inconsistent_borrows = (
            uow.session.query(BorrowRecord)
            .filter(
                BorrowRecord.status == BorrowStatus.RETURNED,
                BorrowRecord.returned_at == None,
            )
            .all()
        )
    assert len(inconsistent_borrows) == 0, (
        "Found returned borrows without returned_at date"
    )
