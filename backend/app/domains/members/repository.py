from datetime import datetime, timezone
from typing import Optional, Tuple, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, case, and_, text
from app.models.member import Member
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.book import Book
from app.domains.members.schemas import MemberCreate, MemberResponse
from app.shared.pagination import encode_cursor, decode_cursor
from app.shared.audit import log_audit_event


class MemberRepository:
    """Data access layer for Member entities, stats, and borrow history."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, obj_in: MemberCreate) -> MemberResponse:
        db_obj = Member(name=obj_in.name, email=obj_in.email, phone=obj_in.phone)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        
        log_audit_event(
            self.session,
            entity_type="member",
            entity_id=db_obj.id,
            action="create",
            new_state=MemberResponse.model_validate(db_obj).model_dump(mode="json")
        )
        self.session.commit()
        
        return MemberResponse.model_validate(db_obj)

    def get(self, id: UUID, include_deleted: bool = False) -> Optional[MemberResponse]:
        statement = select(Member).where(Member.id == id)
        if not include_deleted:
            statement = statement.where(Member.deleted_at.is_(None))
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return MemberResponse.model_validate(result)
        return None

    def get_by_email(self, email: str, include_deleted: bool = False) -> Optional[MemberResponse]:
        statement = select(Member).where(Member.email == email)
        if not include_deleted:
            statement = statement.where(Member.deleted_at.is_(None))
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return MemberResponse.model_validate(result)
        return None
    def update(self, member_id: UUID, data: dict) -> Optional[MemberResponse]:
        db_obj = self.session.get(Member, member_id)
        if not db_obj:
            return None
        
        old_state = MemberResponse.model_validate(db_obj).model_dump(mode="json")
        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(db_obj)
        
        log_audit_event(
            self.session,
            entity_type="member",
            entity_id=db_obj.id,
            action="update",
            old_state=old_state,
            new_state=MemberResponse.model_validate(db_obj).model_dump(mode="json")
        )
        self.session.commit()
        
        return MemberResponse.model_validate(db_obj)

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
        cursor: Optional[str] = None,
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

        # Keyset Pagination
        if cursor:
            decoded = decode_cursor(cursor)
            if decoded:
                cursor_val_str, cursor_id = decoded
                if sort_field == "created_at":
                    cursor_val = datetime.fromisoformat(cursor_val_str)
                else:
                    cursor_val = cursor_val_str

                if sort_order == "desc":
                    stmt = stmt.where(
                        (sort_column < cursor_val) | 
                        ((sort_column == cursor_val) & (Member.id < UUID(cursor_id)))
                    )
                else:
                    stmt = stmt.where(
                        (sort_column > cursor_val) | 
                        ((sort_column == cursor_val) & (Member.id > UUID(cursor_id)))
                    )

        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        if sort_order == "desc":
            stmt = stmt.order_by(Member.id.desc())
        else:
            stmt = stmt.order_by(Member.id.asc())

        if not cursor:
            stmt = stmt.offset(skip)
            
        stmt = stmt.limit(limit)
        results = self.session.execute(stmt).scalars().all()

        next_cursor = None
        if len(results) >= limit:
            last_item = results[-1]
            last_val = getattr(last_item, sort_field)
            last_val_str = last_val.isoformat() if isinstance(last_val, datetime) else str(last_val)
            next_cursor = encode_cursor(last_val_str, str(last_item.id))

        return {
            "items": results,
            "total": total,
            "next_cursor": next_cursor
        }

    def list_all(self, include_deleted: bool = False) -> List[Member]:
        """Fetch all members for export."""
        stmt = select(Member)
        if not include_deleted:
            stmt = stmt.where(Member.deleted_at.is_(None))
        return list(self.session.execute(stmt).scalars().all())

    def bulk_create(self, members_in: List[MemberCreate]) -> Tuple[int, int, List[dict]]:
        """Perform batch inserts with individual audit logging."""
        successful = 0
        failed = 0
        errors = []

        for i, m_in in enumerate(members_in):
            try:
                db_obj = Member(
                    name=m_in.name,
                    email=m_in.email,
                    phone=m_in.phone
                )
                self.session.add(db_obj)
                self.session.flush()
                
                log_audit_event(
                    self.session,
                    entity_type="member",
                    entity_id=db_obj.id,
                    action="bulk_import",
                    new_state=MemberResponse.model_validate(db_obj).model_dump(mode="json")
                )
                successful += 1
            except Exception as e:
                self.session.rollback()
                failed += 1
                errors.append({"row": i, "error": str(e)})
        
        self.session.commit()
        return successful, failed, errors

    def delete(self, id: UUID) -> bool:
        db_obj = self.session.get(Member, id)
        if not db_obj or db_obj.deleted_at:
            return False

        old_state = MemberResponse.model_validate(db_obj).model_dump(mode="json")
        db_obj.deleted_at = datetime.now(timezone.utc)
        self.session.commit()

        log_audit_event(
            self.session,
            entity_type="member",
            entity_id=db_obj.id,
            action="delete",
            old_state=old_state,
            new_state=MemberResponse.model_validate(db_obj).model_dump(mode="json")
        )
        self.session.commit()
        return True

    def restore(self, id: UUID) -> Optional[MemberResponse]:
        db_obj = self.session.get(Member, id)
        if not db_obj or not db_obj.deleted_at:
            return None

        old_state = MemberResponse.model_validate(db_obj).model_dump(mode="json")
        db_obj.deleted_at = None
        self.session.commit()

        log_audit_event(
            self.session,
            entity_type="member",
            entity_id=db_obj.id,
            action="restore",
            old_state=old_state,
            new_state=MemberResponse.model_validate(db_obj).model_dump(mode="json")
        )
        self.session.commit()
        return MemberResponse.model_validate(db_obj)

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

