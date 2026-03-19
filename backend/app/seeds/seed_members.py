import logging
import uuid
from faker import Faker
from app.shared.uow import AbstractUnitOfWork
from app.models.member import Member

logger = logging.getLogger(__name__)


def seed_members(uow: AbstractUnitOfWork, count: int, faker: Faker) -> int:
    """
    Seeds members using bulk insertion.
    Idempotency: Checks if email exists before creating.
    """
    created_count = 0
    logger.info(f"Seeding {count} members...")

    with uow:
        existing_emails = {m.email for m in uow.members.list_all()}

    with uow:
        for _ in range(count):
            email = faker.unique.email()
            name = faker.name()
            phone = faker.phone_number()

            if email in existing_emails:
                continue

            member_orm = Member(
                id=uuid.uuid4(),
                name=name,
                email=email,
                phone=phone
            )
            uow.session.add(member_orm)
            existing_emails.add(email)
            created_count += 1

        uow.commit()

    logger.info(f"Successfully seeded {created_count} members.")
    return created_count
