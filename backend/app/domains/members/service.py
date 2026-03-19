"""Member domain service — orchestrates member operations and analytics."""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from fastapi import BackgroundTasks
from app.shared.uow import AbstractUnitOfWork
from app.shared.csv_utils import parse_csv_stream, generate_csv_response
from app.shared.schemas import PaginatedResponse, PaginationMeta, BulkOperationResponse
from app.domains.members.schemas import (
    MemberCreate,
    MemberUpdate,
    MemberResponse,
    MemberCoreDetails,
    MembershipAnalyticsSummary,
    MemberBorrowHistoryResponse,
    MemberBorrowHistoryItem,
    MemberAnalyticsResponse,
)
from app.core.exceptions import MemberNotFoundError
from app.shared.audit import log_audit_event


class MemberService:
    """Orchestrates member operations, profile details, and analytics with explicit Unit of Work."""

    def __init__(self, uow: AbstractUnitOfWork, background_tasks: Optional[BackgroundTasks] = None):
        self.uow = uow
        self.background_tasks = background_tasks

    def create_member(self, member_in: MemberCreate) -> MemberResponse:
        with self.uow:
            member = self.uow.members.create(member_in)
            self.uow.commit()
            self.uow.refresh(member)
            
            if self.background_tasks:
                self.background_tasks.add_task(
                    log_audit_event,
                    self.uow.session,
                    "MEMBER_CREATE",
                    str(member.id),
                    f"Created member: {member.name}"
                )
            return MemberResponse.model_validate(member)

    def update_member(self, member_id: UUID, member_in: MemberUpdate) -> Optional[MemberResponse]:
        with self.uow:
            data = member_in.model_dump(exclude_unset=True)
            member = self.uow.members.update(member_id, data)
            if not member:
                return None
            self.uow.commit()
            self.uow.refresh(member)
            
            if self.background_tasks:
                self.background_tasks.add_task(
                    log_audit_event,
                    self.uow.session,
                    "MEMBER_UPDATE",
                    str(member.id),
                    f"Updated member: {member.name}"
                )
            return MemberResponse.model_validate(member)

    def delete_member(self, member_id: UUID) -> bool:
        with self.uow:
            success = self.uow.members.delete(member_id)
            if success:
                self.uow.commit()
                if self.background_tasks:
                    self.background_tasks.add_task(
                        log_audit_event,
                        self.uow.session,
                        "MEMBER_DELETE",
                        str(member_id),
                        f"Deleted member {member_id}"
                    )
            return success

    def restore_member(self, member_id: UUID) -> Optional[MemberResponse]:
        with self.uow:
            member = self.uow.members.restore(member_id)
            if not member:
                return None
            self.uow.commit()
            self.uow.refresh(member)
            if self.background_tasks:
                self.background_tasks.add_task(
                    log_audit_event,
                    self.uow.session,
                    "MEMBER_RESTORE",
                    str(member.id),
                    f"Restored member {member.name}"
                )
            return MemberResponse.model_validate(member)

    def list_members(
        self,
        offset: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort: str = "-created_at",
        cursor: Optional[str] = None,
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

        with self.uow:
            result = self.uow.members.list(
                skip=offset,
                limit=limit,
                query=query,
                sort_field=sort_field,
                sort_order=sort_order,
                cursor=cursor,
            )

        items = result["items"]
        total = result["total"]
        next_cursor = result.get("next_cursor")

        return PaginatedResponse(
            data=[MemberResponse.model_validate(m) for m in items],
            meta=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=next_cursor is not None if cursor else (offset + limit) < total,
                next_cursor=next_cursor,
            ),
        )

    def get_member(self, member_id: UUID) -> Optional[MemberResponse]:
        with self.uow:
            member = self.uow.members.get(member_id)
            return MemberResponse.model_validate(member) if member else None

    def get_member_by_email(self, email: str) -> Optional[MemberResponse]:
        with self.uow:
            member = self.uow.members.get_by_email(email)
            return MemberResponse.model_validate(member) if member else None

    def get_member_details(self, member_id: UUID) -> MemberCoreDetails:
        """Build a member profile with membership duration, active borrows, and risk level."""
        with self.uow:
            member = self.uow.members.get(member_id)
            if not member:
                raise MemberNotFoundError("Member not found.")

            stats = self.uow.members.get_core_stats(member_id)
            duration = datetime.now(timezone.utc).date() - member.created_at.date()
            risk_level = self.uow.analytics.calculate_risk_level(stats["overdue_rate_percent"])

        return MemberCoreDetails(
            member=MemberResponse.model_validate(member),
            membership_duration_days=max(0, duration.days),
            active_borrows_count=stats["active_borrows_count"],
            analytics_summary=MembershipAnalyticsSummary(
                total_books_borrowed=stats["total_books_borrowed"],
                overdue_rate_percent=stats["overdue_rate_percent"],
                risk_level=risk_level,
                total_fines_accrued=stats["total_fines_accrued"],
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
        with self.uow:
            results, total = self.uow.members.get_borrow_history(
                member_id, limit, offset, status, sort, order
            )

        data = []
        now = datetime.now(timezone.utc)
        for r in results:
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
        with self.uow:
            return self.uow.analytics.get_member_analytics(member_id)

    def export_members_csv(self) -> str:
        with self.uow:
            members = self.uow.members.list_all()
        data = [MemberResponse.model_validate(m).model_dump(mode="json") for m in members]
        fieldnames = ["id", "name", "email", "phone", "created_at", "updated_at"]
        return generate_csv_response(data, fieldnames)

    def import_members_csv(self, file_content: bytes) -> BulkOperationResponse:
        rows = parse_csv_stream(file_content)
        members_in = []
        for row in rows:
            try:
                members_in.append(MemberCreate(
                    name=row["name"],
                    email=row["email"],
                    phone=row.get("phone")
                ))
            except Exception:
                continue

        with self.uow:
            success, failed, errors = self.uow.members.bulk_create(members_in)
            self.uow.commit()
            
        return BulkOperationResponse(
            total_records=len(rows),
            successful=success,
            failed=failed + (len(rows) - len(members_in) - success),
            errors=errors
        )
