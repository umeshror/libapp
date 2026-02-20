from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.schemas import BorrowRecordCreate, BorrowRecordResponse


class BorrowRepository:
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
    ) -> dict:
        from app.models.member import Member
        from app.models.book import Book

        stmt = select(BorrowRecord).options(
            joinedload(BorrowRecord.book), joinedload(BorrowRecord.member)
        )

        # Joins for search if needed
        if query:
            stmt = stmt.join(BorrowRecord.member).join(BorrowRecord.book)

        # Filtering
        if member_id:
            stmt = stmt.where(BorrowRecord.member_id == member_id)

        if status:
            stmt = stmt.where(BorrowRecord.status == status)

        if overdue:
            from datetime import datetime, timezone

            stmt = stmt.where(
                and_(
                    BorrowRecord.status == BorrowStatus.BORROWED,
                    BorrowRecord.due_date < datetime.now(timezone.utc),
                )
            )

        if query:
            search_term = f"%{query}%"
            # Search by member name or book title
            stmt = stmt.where(
                (Member.name.ilike(search_term)) | (Book.title.ilike(search_term))
            )

        # Count
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar() or 0

        # Sorting
        sort_column = getattr(BorrowRecord, sort_field, BorrowRecord.borrowed_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        stmt = stmt.order_by(BorrowRecord.id)  # Deterministic

        stmt = stmt.offset(skip).limit(limit)
        results = self.session.execute(stmt).scalars().all()

        return {"items": results, "total": total}
