from datetime import datetime, timezone
from typing import Optional, Tuple, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, case, and_, text
from app.models.member import Member
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.book import Book
from app.domains.members.schemas import MemberCreate, MemberResponse


class MemberRepository:
    """Data access layer for Member entities, stats, and borrow history."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, obj_in: MemberCreate) -> MemberResponse:
        db_obj = Member(name=obj_in.name, email=obj_in.email, phone=obj_in.phone)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return MemberResponse.model_validate(db_obj)

    def get(self, id: UUID) -> Optional[MemberResponse]:
        statement = select(Member).where(Member.id == id)
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return MemberResponse.model_validate(result)
        return None

    def get_by_email(self, email: str) -> Optional[MemberResponse]:
        statement = select(Member).where(Member.email == email)
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return MemberResponse.model_validate(result)
        return None

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        stmt = select(Member)

        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                (Member.name.ilike(search_term)) | (Member.email.ilike(search_term))
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        sort_column = getattr(Member, sort_field, Member.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        stmt = stmt.order_by(Member.id)  # Deterministic

        stmt = stmt.offset(skip).limit(limit)
        results = self.session.execute(stmt).scalars().all()

        return {"items": results, "total": total}

    def get_core_stats(self, member_id: UUID) -> dict:
        """
        Fetch active borrow count and basic summary stats.
        """
        active_count = (
            self.session.execute(
                select(func.count())
                .select_from(BorrowRecord)
                .where(
                    and_(
                        BorrowRecord.member_id == member_id,
                        BorrowRecord.status == BorrowStatus.BORROWED,
                    )
                )
            ).scalar()
            or 0
        )

        total_borrowed = func.count(BorrowRecord.id)
        returned_overdue = func.count().filter(
            and_(
                BorrowRecord.returned_at > BorrowRecord.due_date,
                BorrowRecord.returned_at.is_not(None),
            )
        )
        active_overdue = func.count().filter(
            and_(
                BorrowRecord.status == BorrowStatus.BORROWED,
                BorrowRecord.due_date < datetime.now(timezone.utc),
            )
        )

        stats = self.session.execute(
            select(
                total_borrowed.label("total_borrowed"),
                returned_overdue.label("returned_overdue_count"),
                active_overdue.label("active_overdue_count"),
            ).where(BorrowRecord.member_id == member_id)
        ).first()

        total = stats.total_borrowed if stats is not None else 0
        overdue_total = (
            (stats.returned_overdue_count or 0) + (stats.active_overdue_count or 0)
            if stats is not None
            else 0
        )
        overdue_rate = (overdue_total / total * 100) if total > 0 else 0.0

        return {
            "active_borrows_count": active_count,
            "total_books_borrowed": total,
            "overdue_rate_percent": round(overdue_rate, 2),
        }

    def get_borrow_history(
        self,
        member_id: UUID,
        limit: int = 10,
        offset: int = 0,
        status: Optional[str] = "all",
        order_by: str = "borrowed_at",
        order: str = "desc",
    ) -> Tuple[Any, int]:
        """
        Fetch paginated borrow history with book details.
        """
        duration_expr = func.extract(
            "day",
            func.coalesce(BorrowRecord.returned_at, datetime.now(timezone.utc))
            - BorrowRecord.borrowed_at,
        )

        query = (
            select(
                BorrowRecord.id,
                BorrowRecord.book_id,
                Book.title.label("book_title"),
                BorrowRecord.borrowed_at,
                BorrowRecord.returned_at,
                BorrowRecord.due_date,
                duration_expr.label("duration_days"),
            )
            .join(Book, BorrowRecord.book_id == Book.id)
            .where(BorrowRecord.member_id == member_id)
        )

        if status == "active":
            query = query.where(BorrowRecord.status == BorrowStatus.BORROWED)
        elif status == "returned":
            query = query.where(BorrowRecord.status == BorrowStatus.RETURNED)

        total_query = select(func.count()).select_from(query.subquery())
        total = self.session.execute(total_query).scalar() or 0

        sort_col = (
            getattr(BorrowRecord, order_by)
            if hasattr(BorrowRecord, order_by)
            else BorrowRecord.borrowed_at
        )
        if order == "desc":
            query = query.order_by(desc(sort_col))
        else:
            query = query.order_by(sort_col)

        query = query.limit(limit).offset(offset)
        results = self.session.execute(query).all()

        return results, total

