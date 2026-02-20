from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.member_detail_service import MemberDetailService
from app.schemas.member_details import (
    MemberCoreDetails,
    MemberBorrowHistoryResponse,
    MemberAnalyticsResponse,
)

router = APIRouter(prefix="/members", tags=["member-details"])


@router.get("/{member_id}", response_model=MemberCoreDetails)
def get_member_details(member_id: UUID, db: Session = Depends(get_db)):
    """
    Get lightweight member profile and behavioral summary.
    """
    service = MemberDetailService(db)
    return service.get_member_details(member_id)


@router.get("/{member_id}/borrows", response_model=MemberBorrowHistoryResponse)
def get_member_borrow_history(
    member_id: UUID,
    limit: int = 10,
    offset: int = 0,
    status: str = "all",
    sort: str = "borrowed_at",
    order: str = "desc",
    db: Session = Depends(get_db),
):
    """
    Get paginated borrow history for a member with book details.
    """
    service = MemberDetailService(db)
    return service.get_member_borrow_history(
        member_id, limit, offset, status, sort, order
    )


@router.get("/{member_id}/analytics", response_model=MemberAnalyticsResponse)
def get_member_analytics(member_id: UUID, db: Session = Depends(get_db)):
    """
    Get deep behavioral analytics for a member.
    """
    service = MemberDetailService(db)
    return service.get_member_analytics(member_id)
