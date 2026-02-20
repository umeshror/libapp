from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from app.api.deps import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import AnalyticsSummaryResponse

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    from_date: Optional[date] = Query(
        None, alias="from", description="Start date (YYYY-MM-DD)"
    ),
    to_date: Optional[date] = Query(
        None, alias="to", description="End date (YYYY-MM-DD)"
    ),
    db: Session = Depends(get_db),
):
    """
    Get advanced analytics summary for the dashboard.
    - Overview metrics (Total books, active borrows, utilization)
    - Overdue risk breakdown
    - Top active members
    - Inventory health
    - Daily active members trend
    - 7-day borrow forecast

    If dates are not provided, defaults to the last 30 days.
    """
    service = AnalyticsService(db)

    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=400, detail="Start date cannot be after end date."
        )

    try:
        return service.get_summary(from_date, to_date)
    except Exception as e:
        from app.core.logging import logger

        logger.error(f"Analytics failure: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while generating analytics.",
        )
