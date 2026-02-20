from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.member_detail_repository import MemberDetailRepository
from app.repositories.member_repository import MemberRepository
from app.schemas.member_details import (
    MemberCoreDetails,
    MembershipAnalyticsSummary,
    MemberBorrowHistoryResponse,
    MemberBorrowHistoryItem,
    MemberAnalyticsResponse,
)


class MemberDetailService:
    def __init__(self, db: Session):
        self.repository = MemberDetailRepository(db)
        self.member_repo = MemberRepository(db)

    def _calculate_risk_level(self, overdue_rate: float) -> str:
        if overdue_rate < 5.0:
            return "LOW"
        elif overdue_rate <= 15.0:
            return "MEDIUM"
        return "HIGH"

    def get_member_details(self, member_id: UUID) -> MemberCoreDetails:
        member = self.member_repo.get(member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        stats = self.repository.get_member_core_stats(member_id)

        # Calculate membership duration
        duration = datetime.now(timezone.utc).date() - member.created_at.date()

        risk_level = self._calculate_risk_level(stats["overdue_rate_percent"])

        return MemberCoreDetails(
            member=member,
            membership_duration_days=max(0, duration.days),
            active_borrows_count=stats["active_borrows_count"],
            analytics_summary=MembershipAnalyticsSummary(
                total_books_borrowed=stats["total_books_borrowed"],
                overdue_rate_percent=stats["overdue_rate_percent"],
                risk_level=risk_level,
            ),
        )

    def get_member_borrow_history(
        self,
        member_id: UUID,
        limit: int,
        offset: int,
        status: str,
        sort: str,
        order: str,
    ) -> MemberBorrowHistoryResponse:
        results, total = self.repository.get_member_borrow_history(
            member_id, limit, offset, status, sort, order
        )

        # Check if overdue
        data = []
        now = datetime.now(timezone.utc)
        for r in results:
            # Ensure due_date and returned_at are aware for comparison
            due_dt = r.due_date
            if due_dt and due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)

            ret_at = r.returned_at
            if ret_at and ret_at.tzinfo is None:
                ret_at = ret_at.replace(tzinfo=timezone.utc)

            was_overdue = False
            if ret_at:
                was_overdue = ret_at > due_dt
            else:
                was_overdue = now > due_dt

            data.append(
                MemberBorrowHistoryItem(
                    book_id=r.book_id,
                    book_title=r.book_title,
                    borrowed_at=r.borrowed_at,
                    due_date=r.due_date,
                    returned_at=r.returned_at,
                    duration_days=int(r.duration_days)
                    if r.duration_days is not None
                    else None,
                    was_overdue=was_overdue,
                )
            )

        return MemberBorrowHistoryResponse(
            data=data,
            meta={
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            },
        )

    def get_member_analytics(self, member_id: UUID) -> MemberAnalyticsResponse:
        analytics = self.repository.get_member_detailed_analytics(member_id)

        # Add risk level
        analytics["risk_level"] = self._calculate_risk_level(
            analytics["overdue_rate_percent"]
        )

        return MemberAnalyticsResponse(**analytics)
