import logging
import random
import os
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
        from concurrent.futures import ThreadPoolExecutor
        from app.db.session import SessionLocal

        logger.info(f"Generating {book_count} books and {member_count} members using parallel workers...")
        num_workers = min(os.cpu_count() or 4, 8)

        # 1. Books
        def _book_worker(count):
            worker_db = SessionLocal()
            books = []
            local_book_ids = []
            local_inventory = {}
            local_tiers = {}
            
            for _ in range(count):
                book_id = uuid4()
                total_copies = random.randint(1, 10)
                books.append(Book(
                    id=book_id,
                    title=self.faker.sentence(nb_words=3),
                    author=self.faker.name(),
                    isbn=f"{self.faker.isbn13()}-{uuid4().hex[:4]}",
                    total_copies=total_copies,
                    available_copies=total_copies,
                ))
                local_book_ids.append(book_id)
                local_inventory[book_id] = {"total": total_copies, "active": 0}
                
                rand = random.random()
                if rand < 0.05: local_tiers[book_id] = "A"
                elif rand < 0.30: local_tiers[book_id] = "B"
                elif rand < 0.80: local_tiers[book_id] = "C"
                else: local_tiers[book_id] = "D"

            worker_db.bulk_save_objects(books)
            worker_db.commit()
            worker_db.close()
            return local_book_ids, local_inventory, local_tiers

        book_chunk = book_count // num_workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_book_worker, book_chunk if i < num_workers - 1 else book_count - (book_chunk * i)) for i in range(num_workers)]
            for f in futures:
                ids, inv, tiers = f.result()
                self.book_ids.extend(ids)
                self.inventory.update(inv)
                self.book_tiers.update(tiers)

        logger.info(f"Inserted {book_count} books.")

        # 2. Members
        def _member_worker(count):
            worker_db = SessionLocal()
            members_data = []
            local_member_ids = []
            local_segments = {}
            
            for _ in range(count):
                member_id = uuid4()
                days_ago = random.randint(0, total_months * 30)
                joined_date = datetime.now(timezone.utc) - timedelta(days=days_ago)

                members_data.append({
                    "id": member_id,
                    "name": self.faker.name(),
                    "email": f"{uuid4().hex[:8]}@{self.faker.domain_name()}",
                    "phone": self.faker.phone_number(),
                    "created_at": joined_date,
                    "updated_at": joined_date,
                })
                local_member_ids.append(member_id)
                
                rand = random.random()
                if rand < 0.05: local_segments[member_id] = "heavy"
                elif rand < 0.55: local_segments[member_id] = "regular"
                elif rand < 0.80: local_segments[member_id] = "casual"
                else: local_segments[member_id] = "inactive"

                if len(members_data) >= 5000:
                    worker_db.execute(insert(Member), members_data)
                    worker_db.commit()
                    members_data = []

            if members_data:
                worker_db.execute(insert(Member), members_data)
                worker_db.commit()
            worker_db.close()
            return local_member_ids, local_segments

        member_chunk = member_count // num_workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            members_futures = [executor.submit(_member_worker, member_chunk if i < num_workers - 1 else member_count - (member_chunk * i)) for i in range(num_workers)]
            for f in members_futures:
                ids, segs = f.result()
                self.member_ids.extend(ids)
                self.member_segments.update(segs)

        logger.info(f"Inserted {member_count} members.")

    def simulate_borrows(self, total_months: int, target_records: int):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from app.db.session import SessionLocal

        start_date = datetime.now(timezone.utc) - timedelta(days=total_months * 30)
        end_date = datetime.now(timezone.utc)
        
        logger.info(
            f"Simulating activity from {start_date.date()} to {end_date.date()} using parallel workers..."
        )

        # Pre-filter and prepare data for threads
        active_members = [
            m_id for m_id, seg in self.member_segments.items() if seg != "inactive"
        ]
        borrowable_books = [
            b_id for b_id, tier in self.book_tiers.items() if tier != "D"
        ]
        tier_weights = {"A": 50, "B": 10, "C": 1}
        weighted_books = []
        for b_id in borrowable_books:
            weighted_books.extend([b_id] * tier_weights[self.book_tiers[b_id]])

        # Divide work into chunks of days (e.g., 30 days per chunk)
        num_workers = min(os.cpu_count() or 4, 8)
        days_per_worker = max(1, (total_months * 30) // num_workers)
        
        chunks = []
        chunk_start = start_date
        while chunk_start < end_date:
            chunk_end = min(chunk_start + timedelta(days=days_per_worker), end_date)
            chunks.append((chunk_start, chunk_end))
            chunk_start = chunk_end

        total_created = 0
        logger.info(f"Launching {len(chunks)} workers for parallel simulation...")

        def _worker(date_range):
            worker_start, worker_end = date_range
            worker_db = SessionLocal()
            worker_created = 0
            records_to_insert = []
            current_date = worker_start
            batch_size = 10000

            try:
                while current_date < worker_end:
                    seasonal_factor = 1.0
                    if current_date.month in [11, 12]:
                        seasonal_factor = 1.3
                    if current_date.month in [6, 7]:
                        seasonal_factor = 0.8

                    daily_target = (target_records / (total_months * 30)) * seasonal_factor
                    daily_count = int(random.gauss(daily_target, daily_target * 0.1))

                    for _ in range(max(0, daily_count)):
                        m_id = random.choice(active_members)
                        b_id = random.choice(weighted_books)
                        
                        # Simplified inventory check for parallel seeder:
                        # At this scale, we'll allow slight over-borrowing during simulation
                        # and sync available_copies at the end via SQL.
                        # Tracking global 'active' accurately across threads needs locks.
                        # For seeder, speed > perfect inventory consistency during generation.
                        
                        due_date = current_date + timedelta(days=14)
                        is_overdue = random.random() < 0.12
                        returned_at = None
                        status = BorrowStatus.BORROWED

                        if is_overdue:
                            delay = random.choice([random.randint(1, 3), random.randint(4, 7), random.randint(8, 30)])
                            ret_date = due_date + timedelta(days=delay)
                        else:
                            ret_date = current_date + timedelta(days=random.randint(1, 13))

                        if ret_date < end_date:
                            returned_at = ret_date
                            status = BorrowStatus.RETURNED

                        records_to_insert.append({
                            "id": uuid4(),
                            "book_id": b_id,
                            "member_id": m_id,
                            "borrowed_at": current_date,
                            "due_date": due_date,
                            "returned_at": returned_at,
                            "status": status,
                        })
                        worker_created += 1

                        if len(records_to_insert) >= batch_size:
                            worker_db.execute(insert(BorrowRecord), records_to_insert)
                            worker_db.commit()
                            records_to_insert = []

                    current_date += timedelta(days=1)

                if records_to_insert:
                    worker_db.execute(insert(BorrowRecord), records_to_insert)
                    worker_db.commit()
            except Exception as e:
                logger.error(f"Worker failed: {e}")
                worker_db.rollback()
            finally:
                worker_db.close()
            return worker_created

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_worker, chunk) for chunk in chunks]
            for future in as_completed(futures):
                total_created += future.result()
                logger.info(f"Worker finished. Total so far: {total_created}")

        logger.info(f"Simulation finished. Total records: {total_created}")

    def _flush_borrows(self, records):
        self.db.execute(insert(BorrowRecord), records)
        self.db.commit()

    def update_inventory_status(self):
        logger.info("Syncing final inventory available_copies...")
        self.db.execute(
            text("""
            UPDATE book 
            SET available_copies = GREATEST(0, total_copies - COALESCE(stats.active_count, 0))
            FROM (
                SELECT book_id, COUNT(*) as active_count 
                FROM borrow_record 
                WHERE status = 'borrowed'
                GROUP BY book_id
            ) as stats
            WHERE book.id = stats.book_id
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
