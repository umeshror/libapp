import logging
import random
from datetime import timezone
from faker import Faker
from sqlalchemy.orm import Session
from app.domains.borrows.service import BorrowService

logger = logging.getLogger(__name__)


def seed_borrows(
    db: Session,
    active_count: int,
    returned_count: int,
    overdue_count: int,
    faker: Faker,
) -> int:
    """
    Seeds borrow records using BorrowService.
    Supports active, returned, and overdue scenarios.
    """
    borrow_service = BorrowService(db)

    total_seeded = 0

    # helper to get random book/member
    # Use Repository directly to bypass Service limit of 100
    from app.domains.books.repository import BookRepository

    book_repo = BookRepository(db)
    books_result = book_repo.list(limit=50000)
    all_books = books_result["items"]

    # MemberService now enforces limit=100, so use Repo
    from app.domains.members.repository import MemberRepository

    member_repo = MemberRepository(db)
    members_result = member_repo.list(limit=50000)
    all_members = members_result["items"]

    if not all_books or not all_members:
        logger.warning("No books or members found. Skipping borrow seeding.")
        return 0

    # 1. Seed Active Borrows
    logger.info(f"Seeding {active_count} active borrows...")
    for _ in range(active_count):
        book = random.choice(all_books)
        member = random.choice(all_members)

        # Simple check to avoid instant failure if book has no copies
        if book.available_copies < 1:
            continue

        try:
            # Random date in last 1.5 years
            borrow_date = faker.date_time_between(
                start_date="-547d", end_date="now", tzinfo=timezone.utc
            )
            borrow_service.borrow_book(book.id, member.id, borrowed_at=borrow_date)
            total_seeded += 1
        except Exception:
            # Ignore conflicts (limit exceeded, etc) for seeding
            pass

    # 2. Seed Returned Borrows
    logger.info(f"Seeding {returned_count} returned borrows...")
    for _ in range(returned_count):
        book = random.choice(all_books)
        member = random.choice(all_members)

        if book.available_copies < 1:
            continue

        try:
            # Borrow in past (last 1.5 years)
            borrow_date = faker.date_time_between(
                start_date="-547d", end_date="-30d", tzinfo=timezone.utc
            )
            borrow = borrow_service.borrow_book(
                book.id, member.id, borrowed_at=borrow_date
            )

            # Return after borrow date
            # We ensure return date is after borrow date implicitly by logic or we can be precise
            # faker.date_time_between can take start_date as datetime object? Yes.
            return_date = faker.date_time_between(
                start_date=borrow_date, end_date="now", tzinfo=timezone.utc
            )
            borrow_service.return_book(borrow.id, returned_at=return_date)

            total_seeded += 1
        except Exception:
            pass

    # 3. Seed Overdue Borrows
    logger.info(f"Seeding {overdue_count} overdue borrows...")
    for _ in range(overdue_count):
        book = random.choice(all_books)
        member = random.choice(all_members)

        if book.available_copies < 1:
            continue

        try:
            # Borrow > 14 days ago (up to 1.5 years)
            borrow_date = faker.date_time_between(
                start_date="-547d", end_date="-20d", tzinfo=timezone.utc
            )
            # Due date will be +14 days from borrow_date, so it will be in the past
            borrow_service.borrow_book(book.id, member.id, borrowed_at=borrow_date)
            total_seeded += 1
        except Exception:
            pass

    logger.info(f"Successfully seeded {total_seeded} borrow events.")
    return total_seeded
