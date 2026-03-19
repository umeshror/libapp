import logging
import random
import uuid
from datetime import timezone
from faker import Faker
from app.shared.uow import AbstractUnitOfWork
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.book import Book

logger = logging.getLogger(__name__)


def seed_borrows(
    uow: AbstractUnitOfWork,
    active_count: int,
    returned_count: int,
    overdue_count: int,
    faker: Faker,
) -> int:
    """Seeds borrow records using bulk addition."""
    total_seeded = 0

    with uow:
        all_books = uow.books.list(limit=50000)["items"]
        all_members = uow.members.list(limit=50000)["items"]

    if not all_books or not all_members:
        logger.warning("No books or members found. Skipping borrow seeding.")
        return 0

    def get_borrow_dates(scenario: str):
        if scenario == "active":
            return faker.date_time_between(start_date="-547d", end_date="now", tzinfo=timezone.utc), None, BorrowStatus.BORROWED
        elif scenario == "returned":
            start = faker.date_time_between(start_date="-547d", end_date="-30d", tzinfo=timezone.utc)
            end = faker.date_time_between(start_date=start, end_date="now", tzinfo=timezone.utc)
            return start, end, BorrowStatus.RETURNED
        elif scenario == "overdue":
            start = faker.date_time_between(start_date="-547d", end_date="-20d", tzinfo=timezone.utc)
            return start, None, BorrowStatus.BORROWED

    with uow:
        for scenario, count in [("active", active_count), ("returned", returned_count), ("overdue", overdue_count)]:
            logger.info(f"Seeding {count} {scenario} borrows...")
            for _ in range(count):
                book = random.choice(all_books)
                member = random.choice(all_members)
                
                if scenario != "returned" and book.available_copies < 1:
                    continue

                borrow_date, return_date, status = get_borrow_dates(scenario)
                
                due_date = borrow_date + __import__('datetime').timedelta(days=14)

                record = BorrowRecord(
                    id=uuid.uuid4(),
                    book_id=book.id,
                    member_id=member.id,
                    borrowed_at=borrow_date,
                    due_date=due_date,
                    returned_at=return_date,
                    status=status
                )
                
                # Adjust availability
                if status == BorrowStatus.BORROWED:
                    book_orm = uow.session.get(Book, book.id)
                    if book_orm and book_orm.available_copies > 0:
                        book_orm.available_copies -= 1
                    else:
                        continue
                
                uow.session.add(record)
                total_seeded += 1
                
                if total_seeded % 500 == 0:
                    uow.flush()

        uow.commit()

    logger.info(f"Successfully seeded {total_seeded} borrow events.")
    return total_seeded
