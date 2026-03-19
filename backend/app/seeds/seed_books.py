import logging
import uuid
from datetime import timezone
from faker import Faker
from app.shared.uow import AbstractUnitOfWork
from app.models.book import Book

logger = logging.getLogger(__name__)


def seed_books(uow: AbstractUnitOfWork, count: int, faker: Faker) -> int:
    """
    Seeds books using bulk insertion.
    Idempotency: Checks if ISBN exists before creating.
    """
    created_count = 0
    logger.info(f"Seeding {count} books...")

    with uow:
        existing_isbns = {b.isbn for b in uow.books.list_all()}

    with uow:
        for _ in range(count):
            isbn = faker.isbn13()
            title = faker.sentence(nb_words=4).rstrip(".")
            author = faker.name()
            total_copies = faker.random_int(min=1, max=10)
            created_at = faker.date_time_between(
                start_date="-547d", end_date="now", tzinfo=timezone.utc
            )

            if isbn in existing_isbns:
                continue

            book_orm = Book(
                id=uuid.uuid4(),
                title=title,
                author=author,
                isbn=isbn,
                total_copies=total_copies,
                available_copies=total_copies,
                created_at=created_at
            )
            uow.session.add(book_orm)
            existing_isbns.add(isbn)
            created_count += 1

            if created_count % 500 == 0:
                uow.flush()

        uow.commit()

    logger.info(f"Successfully seeded {created_count} books.")
    return created_count
