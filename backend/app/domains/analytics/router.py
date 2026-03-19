"""Analytics domain API endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date
from typing import Optional
from app.shared.deps import get_uow
from app.shared.uow import UnitOfWork
from app.domains.analytics.service import AnalyticsService
from app.domains.analytics.schemas import AnalyticsSummaryResponse
from app.core.logging import logger

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    from_date: Optional[date] = Query(
        None, alias="from", description="Start date (YYYY-MM-DD)"
    ),
    to_date: Optional[date] = Query(
        None, alias="to", description="End date (YYYY-MM-DD)"
    ),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Get advanced analytics summary for the dashboard.
    Defaults to the last 30 days if dates are not provided.
    """
    service = AnalyticsService(uow)

    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=400, detail="Start date cannot be after end date."
        )

    try:
        return service.get_summary(from_date, to_date)
    except Exception as e:
        logger.error(f"Analytics failure: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while generating analytics.",
        )
