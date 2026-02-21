import uuid
from sqlalchemy import Column, Integer, String, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin


class Book(Base, TimestampMixin):
    """
    Core inventory model enforcing business rules for book availability.
    Maintains total physical copies and tracks available copies for borrowing.
    Uses version_id for optimistic locking during concurrent borrow operations.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String, index=True, nullable=False)
    author = Column(String, index=True, nullable=False)
    isbn = Column(String, unique=True, index=True, nullable=False)
    total_copies = Column(Integer, default=1, nullable=False)
    available_copies = Column(Integer, default=1, nullable=False)

    # Optimistic Locking
    version_id = Column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version_id}

    # Constraints
    __table_args__ = (
        CheckConstraint("total_copies >= 0", name="check_total_copies_non_negative"),
        CheckConstraint(
            "available_copies >= 0", name="check_available_copies_non_negative"
        ),
        Index("ix_book_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
        Index("ix_book_author_trgm", "author", postgresql_using="gin", postgresql_ops={"author": "gin_trgm_ops"}),
        Index("ix_book_isbn_trgm", "isbn", postgresql_using="gin", postgresql_ops={"isbn": "gin_trgm_ops"}),
    )
