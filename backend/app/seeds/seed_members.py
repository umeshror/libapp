import logging
from faker import Faker
from sqlalchemy.orm import Session
from app.services.member_service import MemberService
from app.schemas import MemberCreate

logger = logging.getLogger(__name__)


def seed_members(db: Session, count: int, faker: Faker) -> int:
    """
    Seeds members using the MemberService.
    Idempotency: Checks if email exists before creating.
    """
    service = MemberService(db)
    created_count = 0

    logger.info(f"Seeding {count} members...")

    for _ in range(count):
        # Generate all faker data upfront to keep RNG sequence identical
        email = faker.unique.email()
        name = faker.name()
        phone = faker.phone_number()

        # Check if member exists
        if service.get_member_by_email(email):
            continue

        member_in = MemberCreate(name=name, email=email, phone=phone)

        try:
            service.create_member(member_in)
            created_count += 1
        except Exception as e:
            logger.warning(f"Failed to seed member {email}: {e}")
            continue

    logger.info(f"Successfully seeded {created_count} members.")
    return created_count
