from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.member_repository import MemberRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas import MemberCreate, MemberResponse, PaginatedResponse, PaginationMeta
from app.schemas.member_details import (
    MemberCoreDetails,
    MembershipAnalyticsSummary,
    MemberBorrowHistoryResponse,
    MemberBorrowHistoryItem,
    MemberAnalyticsResponse,
)


class MemberService:
    """Orchestrates member operations, profile details, and analytics."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = MemberRepository(session)
        self.analytics_repo = AnalyticsRepository(session)

    def create_member(self, member_in: MemberCreate) -> MemberResponse:
        return self.repo.create(member_in)

    def get_member(self, member_id: UUID) -> Optional[MemberResponse]:
        return self.repo.get(member_id)

    def get_member_by_email(self, email: str) -> Optional[MemberResponse]:
        return self.repo.get_by_email(email)

    def list_members(
        self,
        offset: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort: str = "-created_at",
    ) -> PaginatedResponse[MemberResponse]:
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        sort_field = sort
        sort_order = "asc"
        if sort.startswith("-"):
            sort_field = sort[1:]
            sort_order = "desc"

        allowed = ["name", "created_at", "email"]
        if sort_field not in allowed:
            raise ValueError(f"Invalid sort field: {sort_field}. Allowed: {allowed}")

        result = self.repo.list(
            skip=offset,
            limit=limit,
            query=query,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        items = result["items"]
        total = result["total"]

        return PaginatedResponse(
            data=[MemberResponse.model_validate(m) for m in items],
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + limit) < total,
            ),
        )

    def get_member_details(self, member_id: UUID) -> MemberCoreDetails:
        """Build a member profile with membership duration, active borrows, and risk level."""
        member = self.repo.get(member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        stats = self.repo.get_core_stats(member_id)

        # Calculate membership duration
        duration = datetime.now(timezone.utc).date() - member.created_at.date()

        risk_level = self.analytics_repo.calculate_risk_level(stats["overdue_rate_percent"])

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
        """Fetch paginated borrow history with overdue detection per record."""
        results, total = self.repo.get_borrow_history(
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
            if due_dt:
                if ret_at:
                    was_overdue = ret_at > due_dt
                else:
                    was_overdue = now > due_dt

            data.append(
                MemberBorrowHistoryItem(
                    id=r.id,
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
        return self.analytics_repo.get_member_analytics(member_id)
