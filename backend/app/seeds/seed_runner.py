import argparse
import logging
import sys
import os
from faker import Faker

# Ensure app is in path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.seeds.scenarios import SCENARIOS
from app.seeds.seed_books import seed_books
from app.seeds.seed_members import seed_members
from app.seeds.seed_borrows import seed_borrows
from app.seeds.high_scale_seeder import seed_high_scale

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_seed(scenario_name: str):
    logger.info(f"Starting seeding for scenario: {scenario_name}")

    if scenario_name not in SCENARIOS:
        logger.error(
            f"Scenario '{scenario_name}' not found. Available: {list(SCENARIOS.keys())}"
        )
        sys.exit(1)

    config = SCENARIOS[scenario_name]

    # Initialize Faker with deterministic seed
    faker = Faker()
    Faker.seed(42)

    db = SessionLocal()

    try:
        # 1. Check if high_scale
        if scenario_name == "high_scale":
            seed_high_scale(db, config, faker)
            return

        # 1. Seed Books
        seed_books(db, config["books"], faker)

        # 2. Seed Members
        seed_members(db, config["members"], faker)

        # 3. Seed Borrows (depends on books and members)
        # We assume if books/members exist, we can try to seed borrows.
        # Idempotency for borrows is harder (checking exact counts),
        # so we rely on the seeder to just add more if needed or skipping if saturated.
        # But for 'borrows', our seeder is currently just 'create N new ones'.
        # To be idempotent, we should check current counts.
        seed_borrows(
            db,
            active_count=config["active_borrows"],
            returned_count=config["returned_borrows"],
            overdue_count=config["overdue_borrows"],
            faker=faker,
        )

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()
        logger.info("Seeding completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the database.")
    parser.add_argument(
        "--scenario", type=str, default="minimal", help="Seeding scenario to run"
    )
    args = parser.parse_args()

    # Environment Check
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        logger.error("Cannot run seeding in production environment!")
        sys.exit(1)

    run_seed(args.scenario)
