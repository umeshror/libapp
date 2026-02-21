import os
import logging
from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy import text
from app.db.session import SessionLocal
from app.seeds.seed_runner import run_seed
from app.core.config import settings
from alembic.config import Config
from alembic import command

logger = logging.getLogger(__name__)
router = APIRouter()

def verify_seeding_secret(x_seeding_secret: str = Header(...)):
    if x_seeding_secret != settings.SEEDING_SECRET:
        raise HTTPException(status_code=403, detail="Invalid seeding secret")

@router.post("/run", dependencies=[Depends(verify_seeding_secret)])
def trigger_seed(scenario: str = "minimal", clear: bool = False, if_empty: bool = False):
    """Trigger the database seeder."""
    try:
        run_seed(scenario, clear=clear, if_empty=if_empty, force=True)
        return {"status": "success", "message": f"Seeding completed for scenario: {scenario}"}
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/migrate", dependencies=[Depends(verify_seeding_secret)])
def trigger_migrate():
    """Run Alembic migrations."""
    try:
        # Get the path to alembic.ini (it's in the backend root)
        # Assuming current working directory is the backend root as it is in Vercel
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        return {"status": "success", "message": "Migrations completed successfully"}
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
