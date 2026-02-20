import logging
import random
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text, insert
from app.models.book import Book
from app.models.member import Member
from app.models.borrow_record import BorrowRecord, BorrowStatus
from faker import Faker

logger = logging.getLogger(__name__)


class HighScaleSeeder:
    def __init__(self, db: Session, faker: Faker):
        self.db = db
        self.faker = faker
        self.book_ids: List[UUID] = []
        self.member_ids: List[UUID] = []
        self.inventory: Dict[UUID, Dict[str, int]] = {}  # book_id -> {total, active}
        self.member_segments: Dict[UUID, str] = {}  # member_id -> segment
        self.book_tiers: Dict[UUID, str] = {}  # book_id -> tier

    def seed_metadata(self, book_count: int, member_count: int, total_months: int):
        logger.info(f"Generating {book_count} books and {member_count} members...")

        # 1. Books
        books = []
        for i in range(book_count):
            book_id = uuid4()
            total_copies = random.randint(1, 10)
            books.append(
                Book(
                    id=book_id,
                    title=self.faker.sentence(nb_words=3),
                    author=self.faker.name(),
                    isbn=f"{self.faker.isbn13()}-{uuid4().hex[:4]}",
                    total_copies=total_copies,
                    available_copies=total_copies,
                )
            )
            self.book_ids.append(book_id)
            self.inventory[book_id] = {"total": total_copies, "active": 0}

            # Assign Tiers: A(5%), B(25%), C(50%), D(20%)
            rand = random.random()
            if rand < 0.05:
                self.book_tiers[book_id] = "A"
            elif rand < 0.30:
                self.book_tiers[book_id] = "B"
            elif rand < 0.80:
                self.book_tiers[book_id] = "C"
            else:
                self.book_tiers[book_id] = "D"

        self.db.bulk_save_objects(books)
        logger.info(f"Inserted {book_count} books.")

        # 2. Members
        members_data = []
        for i in range(member_count):
            member_id = uuid4()
            # Distribute created_at over total_months
            days_ago = random.randint(0, total_months * 30)
            joined_date = datetime.now(timezone.utc) - timedelta(days=days_ago)

            members_data.append(
                {
                    "id": member_id,
                    "name": self.faker.name(),
                    "email": f"{uuid4().hex[:8]}@{self.faker.domain_name()}",
                    "phone": self.faker.phone_number(),
                    "created_at": joined_date,
                    "updated_at": joined_date,
                }
            )
            self.member_ids.append(member_id)

            # Assign Segments: Heavy(5%), Regular(50%), Casual(25%), Inactive(20%)
            rand = random.random()
            if rand < 0.05:
                self.member_segments[member_id] = "heavy"
            elif rand < 0.55:
                self.member_segments[member_id] = "regular"
            elif rand < 0.80:
                self.member_segments[member_id] = "casual"
            else:
                self.member_segments[member_id] = "inactive"

        self.db.execute(insert(Member), members_data)
        self.db.commit()
        logger.info(f"Inserted {member_count} members.")

    def simulate_borrows(self, total_months: int, target_records: int):
        start_date = datetime.now(timezone.utc) - timedelta(days=total_months * 30)
        end_date = datetime.now(timezone.utc)
        current_date = start_date

        logger.info(
            f"Simulating activity from {start_date.date()} to {end_date.date()}..."
        )

        records_to_insert = []
        batch_size = 20000
        total_created = 0

        # Pre-filter active members
        active_members = [
            m_id for m_id, seg in self.member_segments.items() if seg != "inactive"
        ]
        # Pre-filter borrowable books (Tiers A, B, C)
        borrowable_books = [
            b_id for b_id, tier in self.book_tiers.items() if tier != "D"
        ]

        # Weight books by tier for selection
        tier_weights = {"A": 50, "B": 10, "C": 1}
        weighted_books = []
        for b_id in borrowable_books:
            weighted_books.extend([b_id] * tier_weights[self.book_tiers[b_id]])

        # Simulation Loop
        day_inc = 0
        while current_date < end_date:
            day_inc += 1
            # Seasonal factor: Nov-Dec spike (+30%), Summer dip (-20%)
            seasonal_factor = 1.0
            if current_date.month in [11, 12]:
                seasonal_factor = 1.3
            if current_date.month in [6, 7]:
                seasonal_factor = 0.8

            # Base daily borrows
            daily_target = (target_records / (total_months * 30)) * seasonal_factor
            daily_count = int(random.gauss(daily_target, daily_target * 0.1))

            for _ in range(max(0, daily_count)):
                m_id = random.choice(active_members)

                # Member capacity check
                # Heavy: max 5, Regular: max 2, Casual: max 1
                # cap = {'heavy': 5, 'regular': 2, 'casual': 1}[self.member_segments[m_id]]
                # For high scale simulation, we don't track active per member in memory to save RAM,
                # we just sample.

                b_id = random.choice(weighted_books)
                inv = self.inventory[b_id]

                if inv["active"] < inv["total"]:
                    inv["active"] += 1

                    # Duration: 7-14 days usually
                    # duration = random.randint(7, 21)
                    due_date = current_date + timedelta(days=14)

                    # Overdue probability (12% base)
                    is_overdue = random.random() < 0.12
                    returned_at = None
                    status = BorrowStatus.BORROWED

                    if is_overdue:
                        delay = random.choice(
                            [
                                random.randint(1, 3),
                                random.randint(4, 7),
                                random.randint(8, 30),
                            ]
                        )
                        ret_date = due_date + timedelta(days=delay)
                    else:
                        ret_date = current_date + timedelta(days=random.randint(1, 13))

                    # If return date is in the past, mark as returned
                    if ret_date < end_date:
                        returned_at = ret_date
                        status = BorrowStatus.RETURNED
                        inv["active"] -= 1

                    records_to_insert.append(
                        {
                            "id": uuid4(),
                            "book_id": b_id,
                            "member_id": m_id,
                            "borrowed_at": current_date,
                            "due_date": due_date,
                            "returned_at": returned_at,
                            "status": status,
                        }
                    )
                    total_created += 1

                if len(records_to_insert) >= batch_size:
                    self._flush_borrows(records_to_insert)
                    records_to_insert = []
                    logger.info(f"Progress: {total_created} records created...")

            current_date += timedelta(days=1)
            # Occasional inventory replenishment simulation not needed for this scale

        if records_to_insert:
            self._flush_borrows(records_to_insert)

        logger.info(f"Simulation finished. Total records: {total_created}")

    def _flush_borrows(self, records):
        self.db.execute(insert(BorrowRecord), records)
        self.db.commit()

    def update_inventory_status(self):
        logger.info("Syncing final inventory available_copies...")
        self.db.execute(
            text("""
            UPDATE book 
            SET available_copies = total_copies - (
                SELECT COUNT(*) FROM borrow_record 
                WHERE borrow_record.book_id = book.id AND status = 'borrowed'
            )
        """)
        )
        self.db.commit()

    def validate(self):
        logger.info("Running post-seed validation...")
        total_borrows = self.db.execute(select(func.count(BorrowRecord.id))).scalar()
        overdue_count = self.db.execute(
            select(func.count(BorrowRecord.id)).where(
                text(
                    "returned_at > due_date OR (returned_at IS NULL AND due_date < NOW())"
                )
            )
        ).scalar()

        logger.info("--- SEED SUMMARY ---")
        logger.info(f"Total Borrows: {total_borrows}")
        logger.info(f"Overdue Rate: {(overdue_count / total_borrows) * 100:.2f}%")

        # Basic assertions
        assert total_borrows > 400000, "Too few borrows generated"
        assert 8 <= (overdue_count / total_borrows) * 100 <= 18, (
            "Overdue rate out of realistic bounds"
        )
        logger.info("Validation PASSED.")


def seed_high_scale(db: Session, config: dict, faker: Faker):
    seeder = HighScaleSeeder(db, faker)
    seeder.seed_metadata(config["books"], config["members"], config["months"])
    seeder.simulate_borrows(config["months"], config["target_borrows"])
    seeder.update_inventory_status()
    seeder.validate()
