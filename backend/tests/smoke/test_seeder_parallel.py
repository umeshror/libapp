import logging
import sys
import os
from faker import Faker

# Ensure app is in path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.seeds.high_scale_seeder import HighScaleSeeder
from app.seeds.scenarios import SCENARIOS
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)

def clear_data(db):
    print("Clearing existing data...")
    db.execute(text("TRUNCATE TABLE borrow_record RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE member RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE book RESTART IDENTITY CASCADE"))
    db.commit()

def test_parallel_seeder():
    db = SessionLocal()
    faker = Faker()
    
    clear_data(db)
    
    # Use a tiny version of high_scale for testing
    config = {
        "books": 100,
        "members": 50,
        "months": 1,
        "target_borrows": 1000
    }
    
    seeder = HighScaleSeeder(db, faker)
    print("Testing metadata seeding...")
    seeder.seed_metadata(config["books"], config["members"], config["months"])
    
    print("Testing parallel simulation...")
    seeder.simulate_borrows(config["months"], config["target_borrows"])
    
    print("Testing inventory sync...")
    seeder.update_inventory_status()
    
    print("Validation...")
    # Manual validation instead of the full seeder.validate() which has hardcoded high checks
    from sqlalchemy import select, func
    from app.models.borrow_record import BorrowRecord
    total = db.execute(select(func.count(BorrowRecord.id))).scalar()
    print(f"Total borrows created: {total}")
    assert total > 0, "No borrows created!"
    
    print("Smoke test PASSED.")
    db.close()

if __name__ == "__main__":
    test_parallel_seeder()
