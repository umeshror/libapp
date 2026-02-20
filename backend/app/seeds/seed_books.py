import logging
from datetime import timezone
from faker import Faker
from sqlalchemy.orm import Session
from app.services.book_service import BookService
from app.schemas import BookCreate

logger = logging.getLogger(__name__)


def seed_books(db: Session, count: int, faker: Faker) -> int:
    """
    Seeds books using the BookService.
    Idempotency: Checks if ISBN exists before creating.
    """
    service = BookService(db)
    created_count = 0

    logger.info(f"Seeding {count} books...")

    for _ in range(count):
        # Generate all random data upfront to keep RNG sequence identical across runs
        isbn = faker.isbn13()
        title = faker.sentence(nb_words=4).rstrip(".")
        author = faker.name()
        # Seed random with a deterministic value derived from faker to keep sync
        total_copies = faker.random_int(min=1, max=10)
        created_at = faker.date_time_between(
            start_date="-547d", end_date="now", tzinfo=timezone.utc
        )

        # Check if book exists
        if service.get_book_by_isbn(isbn):
            continue

        book_in = BookCreate(
            title=title,
            author=author,
            isbn=isbn,
            total_copies=total_copies,
            available_copies=total_copies,
        )

        try:
            book_response = service.create_book(book_in)

            # Backdate created_at to simulate history
            from app.models.book import Book

            book_orm = db.get(Book, book_response.id)

            if book_orm:
                book_orm.created_at = created_at
                db.add(book_orm)
                db.commit()

            created_count += 1
        except Exception as e:
            logger.warning(f"Failed to seed book {isbn}: {e}")
            continue

    logger.info(f"Successfully seeded {created_count} books.")
    return created_count
