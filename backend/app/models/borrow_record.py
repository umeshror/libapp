import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, DateTime, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class BorrowStatus(str, enum.Enum):
    """Enumeration of possible borrow statuses."""

    BORROWED = "borrowed"
    RETURNED = "returned"


class BorrowRecord(Base):
    """
    Transactional record linking Members to Books.
    Acts as the source of truth for active and historical borrows, due dates, and return timestamps.
    Includes a partial index on (book_id, member_id) to efficiently enforce business rules
    preventing members from concurrently borrowing the same book multiple times.
    """

    __tablename__: str = "borrow_record"  # type: ignore

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    book_id = Column(
        UUID(as_uuid=True), ForeignKey("book.id", ondelete="CASCADE"), nullable=False
    )
    member_id = Column(
        UUID(as_uuid=True), ForeignKey("member.id", ondelete="CASCADE"), nullable=False
    )
    borrowed_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    due_date = Column(DateTime, nullable=True, index=True)
    returned_at = Column(DateTime, nullable=True)
    status = Column(
        Enum(BorrowStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=BorrowStatus.BORROWED,
        nullable=False,
    )  # type: ignore

    book = relationship("Book", backref="borrow_records")
    member = relationship("Member", backref="borrow_records")

    __table_args__ = (
        Index(
            "ix_active_borrows",
            "book_id",
            "member_id",
            postgresql_where=(status == BorrowStatus.BORROWED),
        ),
    )
