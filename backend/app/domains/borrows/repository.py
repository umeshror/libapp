from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_, func
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.member import Member
from app.models.book import Book
from app.domains.borrows.schemas import BorrowRecordCreate, BorrowRecordResponse


class BorrowRepository:
    """Data access layer for BorrowRecord entities with eager-loaded relationships."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, obj_in: BorrowRecordCreate) -> BorrowRecordResponse:
        db_obj = BorrowRecord(
            book_id=obj_in.book_id,
            member_id=obj_in.member_id,
            status=BorrowStatus.BORROWED,
        )
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        # Eager load for response
        return self.get_by_id(db_obj.id)  # type: ignore

    def get_by_id(self, id: UUID) -> Optional[BorrowRecordResponse]:
        statement = (
            select(BorrowRecord)
            .options(joinedload(BorrowRecord.book), joinedload(BorrowRecord.member))
            .where(BorrowRecord.id == id)
        )
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return BorrowRecordResponse.model_validate(result)
        return None

    def get_active_borrow(
        self, book_id: UUID, member_id: UUID
    ) -> Optional[BorrowRecordResponse]:
        """Find an active (not returned) borrow for a specific book-member pair."""
        statement = select(BorrowRecord).where(
            and_(
                BorrowRecord.book_id == book_id,
                BorrowRecord.member_id == member_id,
                BorrowRecord.status == BorrowStatus.BORROWED,
            )
        )
        result = self.session.execute(statement).scalar_one_or_none()
        if result:
            return BorrowRecordResponse.model_validate(result)
        return None

    def get_by_id_with_lock(self, id: UUID) -> Optional[BorrowRecord]:
        """
        Fetches a borrow record by ID with a row lock.
        Returns the ORM object for transactional updates.
        """
        statement = select(BorrowRecord).where(BorrowRecord.id == id).with_for_update()
        result = self.session.execute(statement).scalar_one_or_none()
        return result

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        member_id: Optional[UUID] = None,
        overdue: bool = False,
        status: Optional[BorrowStatus] = None,
        query: Optional[str] = None,
        sort_field: str = "borrowed_at",
        sort_order: str = "desc",
        cursor: Optional[str] = None,
    ) -> dict:
        """List borrow records with filtering by member, status, overdue, and search."""
        stmt = select(BorrowRecord).options(
            joinedload(BorrowRecord.book), joinedload(BorrowRecord.member)
        )

        if query:
            stmt = stmt.join(BorrowRecord.member).join(BorrowRecord.book)

        if member_id:
            stmt = stmt.where(BorrowRecord.member_id == member_id)

        if status:
            stmt = stmt.where(BorrowRecord.status == status)

        if overdue:
            stmt = stmt.where(
                and_(
                    BorrowRecord.status == BorrowStatus.BORROWED,
                    BorrowRecord.due_date < datetime.now(timezone.utc),
                )
            )

        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                (Member.name.ilike(search_term)) | (Book.title.ilike(search_term))
            )


        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0


        sort_column = getattr(BorrowRecord, sort_field, BorrowRecord.borrowed_at)

        # Keyset Pagination
        if cursor:
            try:
                cursor_val_str, cursor_id = cursor.split(":")
                if sort_field in ["borrowed_at", "returned_at", "due_date"]:
                    cursor_val = datetime.fromisoformat(cursor_val_str)
                else:
                    cursor_val = cursor_val_str

                if sort_order == "desc":
                    stmt = stmt.where(
                        (sort_column < cursor_val) | 
                        ((sort_column == cursor_val) & (BorrowRecord.id < UUID(cursor_id)))
                    )
                else:
                    stmt = stmt.where(
                        (sort_column > cursor_val) | 
                        ((sort_column == cursor_val) & (BorrowRecord.id > UUID(cursor_id)))
                    )
            except:
                pass

        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Deterministic secondary sort
        if sort_order == "desc":
            stmt = stmt.order_by(BorrowRecord.id.desc())
        else:
            stmt = stmt.order_by(BorrowRecord.id.asc())

        if not cursor:
            stmt = stmt.offset(skip)
            
        stmt = stmt.limit(limit)
        results = self.session.execute(stmt).scalars().all()

        next_cursor = None
        if len(results) >= limit:
            last_item = results[-1]
            last_val = getattr(last_item, sort_field)
            if last_val:
                last_val_str = last_val.isoformat() if isinstance(last_val, datetime) else str(last_val)
                next_cursor = f"{last_val_str}:{last_item.id}"

        return {
            "items": results,
            "total": total,
            "next_cursor": next_cursor
        }
